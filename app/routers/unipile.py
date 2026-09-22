"""Unipile-related API routes"""
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from uuid import UUID

from app.schemas import WebhookResponse, UnipileWebhookPayload
from app.clients.openai_client import openai_client
from app.services.prompt_manager import prompt_manager
from app.services.queue_persistent import persistent_queue_manager
from app.db.postgres import db
from app.database import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/unipile", tags=["unipile"])


@router.post("/webhook/message-received", response_model=WebhookResponse)
async def handle_webhook(request: Request):
    """
    Handle incoming Unipile webhook for new messages
    
    This endpoint receives webhooks from Unipile when messages are received or sent.
    It processes the message, determines direction (inbound/outbound), and takes
    appropriate action.
    """
    try:
        # Get raw JSON payload
        raw_payload = await request.json()
        logger.info(f"Raw webhook payload: {raw_payload}")
        
        # Try to parse with our schema
        try:
            payload = UnipileWebhookPayload.model_validate(raw_payload)
        except Exception as validation_error:
            logger.error(f"Payload validation failed: {validation_error}")
            logger.error(f"Raw payload that failed: {raw_payload}")
            return WebhookResponse(
                status="error",
                message=f"Invalid payload format: {str(validation_error)}"
            )
        
        logger.info(f"Received webhook event: {payload.event} for chat: {payload.chat_id}")
        logger.info(f"Webhook name: {payload.webhook_name}")
        logger.debug(f"Full payload: {payload.model_dump_json()}")
        
        # Filter: Only process message_received events
        if payload.event != "message_received":
            logger.info(f"Ignoring event type: {payload.event}")
            return WebhookResponse(
                status="success",
                message=f"Event {payload.event} ignored (not message_received)"
            )
        
        # Extract LinkedIn IDs for conversation identification
        # Determine message direction first
        is_account_owner_sender = (
            payload.sender.attendee_provider_id == payload.account_info.user_id
        )
        
        # Set sender and recipient based on direction
        if is_account_owner_sender:
            # OUTBOUND: Account owner sent the message
            # Sender = account owner, Recipient = first attendee (the candidate)
            if not payload.attendees or len(payload.attendees) == 0:
                logger.error("No attendees found in webhook payload")
                raise HTTPException(status_code=400, detail="No attendees in payload")
            
            sender_linkedin_id = payload.account_info.user_id
            recipient_linkedin_id = payload.attendees[0].attendee_provider_id
            direction = "outbound"
        else:
            # INBOUND: Candidate sent the message
            # Sender = candidate (from payload.sender), Recipient = account owner
            sender_linkedin_id = payload.sender.attendee_provider_id
            recipient_linkedin_id = payload.account_info.user_id
            direction = "inbound"
        
        logger.info("=" * 80)
        logger.info("DIRECTION DETECTION:")
        logger.info(f"  Sender LinkedIn ID:       {payload.sender.attendee_provider_id}")
        logger.info(f"  Account Owner LinkedIn ID: {payload.account_info.user_id}")
        logger.info(f"  Are they the same?:        {is_account_owner_sender}")
        logger.info(f"  ➜ DIRECTION:              {direction.upper()}")
        logger.info("=" * 80)
        logger.info(f"Conversation: {sender_linkedin_id} <-> {recipient_linkedin_id}")
        logger.info(f"Message from: {payload.sender.attendee_name}")
        logger.info(f"Message preview: {payload.message[:50]}...")
        
        # Log inbound messages to conversation history (outbound messages are already tracked in queue)
        # This ensures we capture messages from candidates that aren't in our queue system
        if direction == "inbound":
            conversation = await db.find_conversation(sender_linkedin_id, recipient_linkedin_id)
            
            if conversation:
                chat_id = conversation['chat_id']
                logger.info(f"📝 Logging inbound message to conversation history")
                
                # Check for attachments
                has_attachment = bool(payload.attachments and len(payload.attachments) > 0)
                attachment_info = ""
                
                if has_attachment:
                    attachment_details = []
                    for att in payload.attachments:
                        if isinstance(att, dict):
                            att_type = att.get("type", "file")
                            att_mimetype = att.get("mimetype", "unknown")
                            if att_mimetype == "application/pdf":
                                file_desc = "PDF document"
                            elif att_mimetype and att_mimetype.startswith("image/"):
                                file_desc = "image file"
                            elif att_mimetype and "word" in att_mimetype.lower():
                                file_desc = "Word document"
                            else:
                                file_desc = f"{att_type} file"
                            attachment_details.append(f"{file_desc} ({att_mimetype})")
                    if attachment_details:
                        attachment_info = ", ".join(attachment_details)
                
                # Log inbound message to conversation history
                await persistent_queue_manager.add_to_conversation_history(
                    chat_id=chat_id,
                    message=payload.message,
                    direction=direction,
                    has_attachment=has_attachment,
                    attachment_info=attachment_info
                )
                
                logger.info(f"✅ INBOUND message logged to conversation history")
            else:
                logger.warning(f"⚠️  No conversation found for inbound message - cannot log to history")
        else:
            logger.info(f"📤 OUTBOUND message detected - already tracked in queue system")
        
        # Handle inbound messages (from candidates) for AI responses
        if direction == "inbound":
            # Check if this conversation exists (was created via initial outreach)
            conversation = await db.find_conversation(sender_linkedin_id, recipient_linkedin_id)
            
            if conversation:
                logger.info(f"📨 Inbound message from existing conversation - generating AI response")
                
                try:
                    chat_id = conversation['chat_id']
                    job_id = conversation['job_id']
                    
                    # Check AI settings - job level overrides conversation level
                    ai_enabled = True  # Default to enabled
                    
                    # First check job-level setting (overrides everything)
                    try:
                        job_result = db._get_client().table('job_settings').select('ai_enabled').eq('job_id', job_id).execute()
                        if job_result.data:
                            ai_enabled = job_result.data[0]['ai_enabled']
                    except Exception as e:
                        logger.warning(f"Could not fetch job AI setting: {e}")
                    
                    logger.info(f"📍 Job-level AI setting: {'enabled' if ai_enabled else 'disabled'}")
                    
                    # If job-level AI is disabled, don't check conversation level
                    if not ai_enabled:
                        logger.info(f"⚠️  AI disabled at job level for job {job_id} - skipping response generation")
                        return WebhookResponse(
                            status="success",
                            message="Inbound message logged (AI disabled for this job)"
                        )
                    
                    # If job-level AI is enabled, check conversation-level setting
                    if not conversation.get('ai_enabled', True):
                        logger.info(f"⚠️  AI disabled for conversation {chat_id} - skipping response generation")
                        return WebhookResponse(
                            status="success",
                            message="Inbound message logged (AI disabled for this conversation)"
                        )
                    
                    # Auto AI requires a linked Outlook/Google calendar account on the conversation
                    if not conversation.get("calendar_account_id"):
                        logger.info(
                            "No calendar account linked for this conversation — "
                            "skipping auto AI (link Outlook/Google to enable)"
                        )
                        return WebhookResponse(
                            status="success",
                            message="Inbound message logged (no calendar linked; auto AI not triggered)",
                        )
                    
                    # Get account mapping for recruiter name
                    account_mapping = get_supabase_client().get_account_mapping(payload.account_id)
                    recruiter_name = "the recruiter"  # Default
                    if account_mapping:
                        recruiter_name = account_mapping.get("name", recruiter_name)
                    
                    # Get job info from Supabase
                    job_info = get_supabase_client().get_job_info(job_id)
                    if job_info:
                        job_title = job_info.get("job_title", "this position")
                        job_description = job_info.get("job_description", "a great opportunity")
                        client = job_info.get("client", "our client")
                        logger.info(f"📋 Job info loaded: {job_title} for {client}")
                    else:
                        job_title = "this position"
                        job_description = "a great opportunity"
                        client = "our client"
                        logger.warning(f"No job info found for job_id: {job_id}")
                    
                    # Get current conversation stage
                    current_stage = conversation['stage']
                    logger.info(f"📊 Current conversation stage: {current_stage}")
                    
                    # Get full conversation history from database
                    full_history = await persistent_queue_manager.get_conversation_history(str(chat_id))
                    logger.info(f"📜 Retrieved {len(full_history)} messages from conversation history")
                    
                    # Build conversation history for LLM (convert to role-based format)
                    conversation_history = []
                    for msg in full_history[:-1]:  # Exclude the current message (last one) as we'll add it with attachments
                        if msg["direction"] == "outbound":
                            conversation_history.append({
                                "role": "assistant",
                                "content": msg["message"]
                            })
                        else:  # inbound
                            content = msg["message"]
                            if msg.get("has_attachment") and msg.get("attachment_info"):
                                content += f"\n\n[ATTACHMENT: {msg['attachment_info']}]"
                            conversation_history.append({
                                "role": "user",
                                "content": content
                            })
                    
                    # Add current message with attachment info
                    current_message = payload.message
                    if attachment_info:
                        current_message += f"\n\n[ATTACHMENT: The candidate has shared {attachment_info}]"
                    
                    conversation_history.append({
                        "role": "user",
                        "content": current_message
                    })
                    
                    logger.info(f"📝 Prepared {len(conversation_history)} messages for LLM context")
                    
                    # Build prompt with context
                    prompt = prompt_manager.build_prompt(
                        recruiter_name=recruiter_name,
                        client=client,
                        job_title=job_title,
                        job_description=job_description,
                        conversation_stage=current_stage
                    )
                    
                    # Generate AI response
                    ai_full_response = await openai_client.generate_response(
                        prompt=prompt,
                        conversation_history=conversation_history
                    )
                    
                    logger.info(f"🤖 Raw AI response length: {len(ai_full_response)} chars")
                    logger.info(f"🤖 Raw AI response: {ai_full_response}")
                    
                    # Parse AI response (JSON or text format)
                    from app.services.scheduling_parser import parse_ai_response
                    
                    parsed_response = parse_ai_response(ai_full_response)
                    final_message = parsed_response.get("message", "")
                    new_stage = parsed_response.get("stage", current_stage)
                    booking_data = parsed_response.get("booking_data")
                    
                    logger.info(f"🎯 AI selected stage: {new_stage}")
                    logger.info(f"📝 AI message length: {len(final_message)} chars")
                    if booking_data:
                        logger.info(f"📅 AI wants to book: {booking_data.get('datetime')} for {booking_data.get('candidate_name')}")
                    
                    logger.info(f"🤖 Final message length: {len(final_message)} chars")
                    
                    # Validate message is not empty
                    if not final_message:
                        logger.error("❌ AI generated EMPTY response - aborting enqueue")
                        logger.error(f"Full AI response was: {ai_full_response}")
                        logger.error(f"Prompt used: {prompt[:200]}...")
                        # Don't enqueue empty message - stop here
                        return WebhookResponse(
                            status="success",
                            message="Webhook processed but AI response was empty"
                        )
                    
                    logger.info(f"✅ AI response generated (full): {final_message}")
                    
                    # Update conversation stage
                    await db.update_conversation_stage(chat_id, new_stage)
                    
                    # ============================================================
                    # CALENDAR BOOKING: Check if AI wants to schedule a meeting
                    # ============================================================
                    from app.services.calendar_service import calendar_service
                    from datetime import datetime
                    
                    if booking_data:
                        logger.info(f"📅 AI detected scheduling action!")
                        logger.info(f"   DateTime: {booking_data.get('datetime')}")
                        logger.info(f"   Duration: {booking_data.get('duration')} min")
                        logger.info(f"   Email: {booking_data.get('email')}")
                        logger.info(f"   Candidate: {booking_data.get('candidate_name')}")
                        
                        try:
                            # Get or discover calendar ID
                            calendar_id = await calendar_service.get_or_cache_calendar_id(conversation)
                            
                            if calendar_id:
                                # Parse ISO datetime (AI provides it in correct format)
                                datetime_str = booking_data['datetime']
                                proposed_dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
                                
                                logger.info(f"📅 Parsed datetime: {proposed_dt.isoformat()}")
                                
                                # CHECK AVAILABILITY BEFORE BOOKING
                                is_available, conflict = await calendar_service.check_availability(
                                    calendar_id,
                                    conversation.get('calendar_account_id'),
                                    proposed_dt,
                                    booking_data['duration']
                                )
                                
                                if is_available:
                                    # CREATE CALENDAR EVENT
                                    candidate_email = booking_data['email']
                                    candidate_name = booking_data.get('candidate_name', payload.sender.attendee_name)
                                    event_job_summary = booking_data.get('job_summary', job_title)
                                    
                                    event = await calendar_service.create_interview_event(
                                        conversation=conversation,
                                        candidate_name=candidate_name,
                                        job_title=event_job_summary,
                                        proposed_time=proposed_dt,
                                        duration_minutes=booking_data['duration'],
                                        timezone='UTC',
                                        candidate_email=candidate_email,
                                        linkedin_url=f"https://linkedin.com/in/{payload.sender.attendee_provider_id}"
                                    )
                                    
                                    if event:
                                        logger.info(f"✅ 📅 CALENDAR EVENT CREATED!")
                                        logger.info(f"   Event ID: {event.get('id', 'unknown')[:50]}...")
                                        logger.info(f"   Time: {proposed_dt.strftime('%A, %B %d at %I:%M %p UTC')}")
                                        logger.info(f"   Duration: {booking_data['duration']} minutes")
                                        logger.info(f"   Candidate: {candidate_name}")
                                        logger.info(f"   Email: {candidate_email}")
                                    else:
                                        logger.error(f"❌ Failed to create calendar event")
                                else:
                                    logger.warning(f"⚠️  TIME SLOT BUSY: {conflict}")
                                    logger.warning(f"   Booking skipped - candidate will need to choose alternative time")
                            else:
                                logger.info(f"ℹ️  No calendar_account_id in conversation - skipping booking")
                                
                        except ValueError as e:
                            logger.error(f"❌ Invalid datetime format: {booking_data.get('datetime')} - {e}")
                        except Exception as calendar_error:
                            logger.error(f"❌ Calendar booking error: {calendar_error}", exc_info=True)
                            # Don't fail the whole webhook - conversation continues
                    
                    # ============================================================
                    # END CALENDAR BOOKING
                    # ============================================================
                    
                    # Enqueue the AI response using stored conversation IDs (not webhook IDs)
                    # This ensures consistency with the original conversation setup
                    enqueue_result = await persistent_queue_manager.enqueue_message(
                        unipile_account_id=conversation['unipile_account_id'],  # Use stored account ID
                        calendar_account_id=conversation.get('calendar_account_id'),  # Use stored calendar account
                        recipient_linkedin_id=conversation['recipient_linkedin_id'],  # Use stored recipient
                        sender_linkedin_id=conversation['sender_linkedin_id'],  # Use stored sender
                        job_id=conversation['job_id'],  # Use stored job ID
                        message=final_message,
                        is_invite=False,
                        is_initial_reachout=False,
                        conversation_stage=new_stage
                    )
                    
                    if enqueue_result.get("status") == "error":
                        logger.error(f"Failed to enqueue AI response: {enqueue_result.get('error')}")
                    else:
                        logger.info(f"🚀 AI response queued: {enqueue_result.get('message_id')}")
                    
                except Exception as e:
                    logger.error(f"Error generating/enqueuing AI response: {e}", exc_info=True)
                    # Don't fail the webhook - just log the error
            else:
                logger.info(f"⚠️ Inbound message from unknown conversation - ignoring (no initial outreach)")
        
        else:  # outbound
            logger.info(f"📤 Outbound message logged (sent by account owner)")
        
        return WebhookResponse(
            status="success",
            message=f"Webhook processed successfully ({direction} message)"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return WebhookResponse(
            status="error",
            message=f"Error processing webhook: {str(e)}"
        )
