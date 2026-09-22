"""Internal system routes (queue management, scheduling, etc.)"""
import logging
import os
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from app.schemas import (
    EnqueueMessageRequest,
    EnqueueMessageResponse,
    BatchEnqueueRequest,
    BatchEnqueueResponse
)
from app.services.queue_persistent import persistent_queue_manager
from app.services.prompt_manager import prompt_manager
from app.database import get_supabase_client
from app.config import settings
from app.utils.http_errors import enrich_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/internal", tags=["internal"])


@router.get("/jobs/{job_id}")
async def get_job_complete(job_id: str):
    """
    Get complete job data with all conversations and messages pre-grouped.
    Perfect for WhatsApp-like UI - one request, zero manual assembly.
    
    Returns:
    - All conversations for this job
    - Messages grouped by conversation
    - Real-time status and statistics
    - Last message preview for conversation list
    """
    try:
        from app.db.postgres import db
        
        # Get all conversations for this job
        conversations = await db.list_conversations_by_job(job_id)
        
        if not conversations:
            return {
                "status": "success",
                "job_id": job_id,
                "total_conversations": 0,
                "conversations": []
            }
        
        # Build complete response with messages grouped
        result = []
        
        for conv in conversations:
            chat_id = conv['chat_id']
            
            # Get all messages for this conversation
            messages = await db.list_messages_by_chat(chat_id)
            
            # Format messages for UI
            formatted_messages = []
            last_message = None
            last_message_time = None
            
            for msg in messages:
                formatted_msg = enrich_message({
                    "message_id": str(msg['message_id']),
                    "message": msg['message'],
                    "direction": msg['direction'],
                    "message_type": msg['message_type'],
                    "status": msg['status'],
                    "timestamp": msg['created_at'] if isinstance(msg['created_at'], str) else msg['created_at'].isoformat(),
                    "scheduled_at": msg['scheduled_at'] if isinstance(msg['scheduled_at'], str) else (msg['scheduled_at'].isoformat() if msg['scheduled_at'] else None),
                    "sent_at": msg['sent_at'] if isinstance(msg['sent_at'], str) else (msg['sent_at'].isoformat() if msg['sent_at'] else None),
                    "has_attachment": msg['has_attachment'],
                    "attachment_info": msg['attachment_info'],
                    "conversation_stage": msg['conversation_stage'],
                    "retry_count": msg['retry_count'],
                    "error_message": msg['error_message']
                })
                formatted_messages.append(formatted_msg)
                
                # Track last message for preview
                if not last_message_time or msg['created_at'] > last_message_time:
                    last_message = msg['message']
                    last_message_time = msg['created_at']
            
            # Calculate statistics
            stats = {
                "total_messages": len(messages),
                "scheduled": sum(1 for m in messages if m['status'] == 'scheduled'),
                "sending": sum(1 for m in messages if m['status'] == 'sending'),
                "sent": sum(1 for m in messages if m['status'] == 'sent'),
                "error": sum(1 for m in messages if m['status'] == 'error'),
                "cancelled": sum(1 for m in messages if m['status'] == 'cancelled'),
                "history": sum(1 for m in messages if m['status'] == 'history'),
                "inbound": sum(1 for m in messages if m['direction'] == 'inbound'),
                "outbound": sum(1 for m in messages if m['direction'] == 'outbound'),
                "has_errors": any(m['status'] == 'error' for m in messages),
                "has_scheduled": any(m['status'] == 'scheduled' for m in messages)
            }
            
            # Build conversation object
            result.append({
                "chat_id": str(chat_id),
                "sender_linkedin_id": conv['sender_linkedin_id'],
                "recipient_linkedin_id": conv['recipient_linkedin_id'],
                "unipile_account_id": conv['unipile_account_id'],
                "stage": conv['stage'],
                "ai_enabled": conv.get('ai_enabled', True),
                "created_at": conv['created_at'] if isinstance(conv['created_at'], str) else conv['created_at'].isoformat(),
                "updated_at": conv['updated_at'] if isinstance(conv['updated_at'], str) else conv['updated_at'].isoformat(),
                "last_message_preview": last_message[:100] if last_message else None,
                "last_message_at": last_message_time if isinstance(last_message_time, str) else (last_message_time.isoformat() if last_message_time else None),
                "statistics": stats,
                "messages": sorted(formatted_messages, key=lambda x: x['timestamp'])
            })
        
        # Sort by last activity (most recent first)
        result.sort(key=lambda x: x['last_message_at'] or x['created_at'], reverse=True)
        
        # Get job-level AI setting
        job_ai_enabled = True
        try:
            job_result = db._get_client().table('job_settings').select('ai_enabled').eq('job_id', job_id).execute()
            if job_result.data:
                job_ai_enabled = job_result.data[0]['ai_enabled']
        except Exception as e:
            logger.warning(f"Could not fetch job AI setting: {e}")
        
        return {
            "status": "success",
            "job_id": job_id,
            "job_ai_enabled": job_ai_enabled,
            "total_conversations": len(result),
            "conversations": result
        }
        
    except Exception as e:
        logger.error(f"Error fetching complete job data for {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/messages/enqueue", response_model=EnqueueMessageResponse)
async def enqueue_message(request: EnqueueMessageRequest):
    """
    Enqueue a single message for sending
    """
    try:
        # Get sender LinkedIn ID from Supabase
        account_mapping = get_supabase_client().get_account_mapping(request.unipile_account_id)
        if not account_mapping:
            raise HTTPException(
                status_code=404,
                detail=f"Account mapping not found for: {request.unipile_account_id}"
            )
        
        sender_linkedin_id = account_mapping["linkedin_provider_id"]
        
        # Enqueue the message
        result = await persistent_queue_manager.enqueue_message(
            unipile_account_id=request.unipile_account_id,
            calendar_account_id=request.calendar_account_id,
            recipient_linkedin_id=request.recipient_linkedin_id,
            sender_linkedin_id=sender_linkedin_id,
            job_id=request.job_id,
            message=request.message,
            is_invite=request.is_invite,
            is_initial_reachout=request.is_initial_reachout
        )
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return EnqueueMessageResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enqueuing message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/messages/enqueue/batch", response_model=BatchEnqueueResponse)
async def enqueue_batch(request: BatchEnqueueRequest):
    """
    Enqueue multiple messages in a batch (supports mix of invites and messages)
    """
    results = []
    errors = []
    queued_count = 0
    failed_count = 0
    
    for idx, job in enumerate(request.jobs):
        try:
            # Get sender LinkedIn ID from Supabase
            account_mapping = get_supabase_client().get_account_mapping(job.unipile_account_id)
            if not account_mapping:
                error_msg = f"Job {idx}: Account mapping not found for {job.unipile_account_id}"
                errors.append(error_msg)
                failed_count += 1
                results.append(EnqueueMessageResponse(
                    message_id="",
                    chat_id="",
                    status="error",
                    scheduled_at="",
                    error=error_msg
                ))
                continue
            
            sender_linkedin_id = account_mapping["linkedin_provider_id"]
            
            # Enqueue the message
            result = await persistent_queue_manager.enqueue_message(
                unipile_account_id=job.unipile_account_id,
                calendar_account_id=job.calendar_account_id,
                recipient_linkedin_id=job.recipient_linkedin_id,
                sender_linkedin_id=sender_linkedin_id,
                job_id=job.job_id,
                message=job.message,
                is_invite=job.is_invite,
                is_initial_reachout=job.is_initial_reachout
            )
            
            if result.get("status") == "error":
                errors.append(f"Job {idx}: {result.get('error')}")
                failed_count += 1
                results.append(EnqueueMessageResponse(
                    message_id="",
                    chat_id="",
                    status="error",
                    scheduled_at="",
                    error=result.get("error")
                ))
            else:
                queued_count += 1
                results.append(EnqueueMessageResponse(**result))
                
        except Exception as e:
            error_msg = f"Job {idx}: {str(e)}"
            logger.error(f"Error processing job {idx}: {e}")
            errors.append(error_msg)
            failed_count += 1
            results.append(EnqueueMessageResponse(
                message_id="",
                chat_id="",
                status="error",
                scheduled_at="",
                error=error_msg
            ))
    
    return BatchEnqueueResponse(
        status="success" if failed_count == 0 else "partial" if queued_count > 0 else "error",
        total_jobs=len(request.jobs),
        queued=queued_count,
        failed=failed_count,
        results=results,
        errors=errors
    )


@router.delete("/messages/{message_id}/cancel")
async def cancel_message(message_id: str):
    """
    Cancel a scheduled message
    
    Args:
        message_id: The ID of the message to cancel
    """
    result = await persistent_queue_manager.cancel_message(message_id)
    
    if result.get("status") != "success":
        raise HTTPException(
            status_code=404,
            detail=f"Message not found or cannot be cancelled: {message_id}"
        )
    
    return {
        "message_id": message_id,
        "status": "cancelled"
    }


@router.get("/status/queues")
async def get_queue_status():
    """
    Get status of all message queues
    """
    try:
        return await persistent_queue_manager.get_queue_status()
    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        return {
            "status": "error",
            "message": f"Failed to get queue status: {str(e)}",
            "statistics": {
                "total_messages": 0,
                "scheduled": 0,
                "sent": 0,
                "error": 0,
                "cancelled": 0,
                "total_conversations": 0,
                "total_jobs": 0
            }
        }


@router.get("/accounts")
async def get_all_accounts():
    """
    Get all connected accounts from Supabase
    """
    try:
        accounts = get_supabase_client().get_all_accounts()
        return {
            "status": "success",
            "count": len(accounts),
            "accounts": accounts
        }
    except Exception as e:
        logger.error(f"Error fetching accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test-env")
async def test_environment_variables():
    """
    Test environment variable loading
    """
    import os
    from app.config import settings
    
    return {
        "os_getenv": {
            "SUPABASE_URL": os.getenv("SUPABASE_URL"),
            "SUPABASE_KEY": os.getenv("SUPABASE_KEY"),
            "SUPABASE_SERVICE_ROLE_KEY": os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
            "UNIPILE_API_KEY": os.getenv("UNIPILE_API_KEY"),
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY")
        },
        "settings": {
            "SUPABASE_URL": settings.SUPABASE_URL,
            "SUPABASE_KEY": settings.SUPABASE_KEY,
            "SUPABASE_SERVICE_ROLE_KEY": settings.SUPABASE_SERVICE_ROLE_KEY,
            "UNIPILE_API_KEY": settings.UNIPILE_API_KEY,
            "OPENAI_API_KEY": settings.OPENAI_API_KEY
        },
        "all_env_vars": dict(os.environ)
    }


@router.get("/test-env")
async def test_environment_variables():
    """Test environment variable loading"""
    import os
    return {
        "os_getenv": {
            "SUPABASE_URL": os.getenv("SUPABASE_URL"),
            "SUPABASE_KEY": os.getenv("SUPABASE_KEY"),
            "SUPABASE_SERVICE_ROLE_KEY": os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
            "ENVIRONMENT": os.getenv("ENVIRONMENT")
        },
        "settings": {
            "SUPABASE_URL": settings.SUPABASE_URL,
            "SUPABASE_KEY": settings.SUPABASE_KEY,
            "SUPABASE_SERVICE_ROLE_KEY": settings.SUPABASE_SERVICE_ROLE_KEY,
            "ENVIRONMENT": os.getenv("ENVIRONMENT")
        }
    }


@router.get("/test-supabase")
async def test_supabase_connection():
    """
    Test Supabase connection and show configuration
    """
    try:
        # Debug environment variables
        env_debug = {
            "SUPABASE_URL": os.getenv("SUPABASE_URL"),
            "SUPABASE_KEY": os.getenv("SUPABASE_KEY"),
            "SUPABASE_SERVICE_ROLE_KEY": os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
            "settings_supabase_url": settings.SUPABASE_URL,
            "settings_supabase_key": settings.SUPABASE_KEY,
            "settings_service_role_key": settings.SUPABASE_SERVICE_ROLE_KEY
        }
        
        # Test basic connection
        result = get_supabase_client().client.table("unipile_accounts").select("*").limit(1).execute()
        
        return {
            "status": "success",
            "supabase_connected": True,
            "supabase_url": os.getenv("SUPABASE_URL", "Not set"),
            "supabase_key_set": bool(os.getenv("SUPABASE_KEY")),
            "service_role_key_set": bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
            "table_exists": True,
            "sample_data": result.data if result.data else [],
            "total_records": len(result.data) if result.data else 0,
            "env_debug": env_debug
        }
    except Exception as e:
        logger.error(f"Supabase connection test failed: {e}")
        return {
            "status": "error",
            "supabase_connected": False,
            "error": str(e),
            "supabase_url": os.getenv("SUPABASE_URL", "Not set"),
            "supabase_key_set": bool(os.getenv("SUPABASE_KEY")),
            "service_role_key_set": bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
            "env_debug": {
                "SUPABASE_URL": os.getenv("SUPABASE_URL"),
                "SUPABASE_KEY": os.getenv("SUPABASE_KEY"),
                "SUPABASE_SERVICE_ROLE_KEY": os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
                "settings_supabase_url": settings.SUPABASE_URL,
                "settings_supabase_key": settings.SUPABASE_KEY,
                "settings_service_role_key": settings.SUPABASE_SERVICE_ROLE_KEY
            }
        }


@router.get("/messages/all")
async def get_all_messages():
    """
    Get detailed information about all messages in the queue
    """
    return await persistent_queue_manager.get_all_messages()


@router.post("/messages/{message_id}/cancel")
async def cancel_message(message_id: str):
    """
    Cancel a scheduled message
    """
    try:
        result = await persistent_queue_manager.cancel_message(message_id)
        
        if result.get("status") == "success":
            return {"status": "success", "message": "Message cancelled"}
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to cancel message"))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/policies/scheduling")
async def update_scheduling_policy():
    """
    Update scheduling policy for message delays
    """
    # TODO: Implement scheduling policy management
    return {
        "status": "not_implemented",
        "message": "Scheduling policy management will be implemented in the next phase"
    }


@router.get("/policies/scheduling")
async def get_scheduling_policy():
    """
    Get current scheduling policy
    """
    # TODO: Implement scheduling policy retrieval
    return {
        "status": "not_implemented",
        "message": "Scheduling policy retrieval will be implemented in the next phase"
    }


@router.get("/ai/prompt")
async def get_prompt():
    """
    Get the current AI prompt template
    """
    return {
        "prompt": prompt_manager.get_prompt(),
        "variables": prompt_manager.get_template_variables()
    }


@router.put("/ai/prompt")
async def update_prompt(request: Dict[str, str]):
    """
    Update the AI prompt template
    
    Body:
        {
            "prompt": "New prompt template with {variables}"
        }
    """
    try:
        if "prompt" not in request:
            raise HTTPException(status_code=400, detail="Missing 'prompt' field")
        
        new_prompt = request["prompt"]
        
        if not new_prompt or len(new_prompt.strip()) == 0:
            raise HTTPException(status_code=400, detail="Prompt cannot be empty")
        
        success = prompt_manager.update_prompt(new_prompt)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update prompt")
        
        return {
            "status": "success",
            "message": "Prompt updated successfully",
            "prompt": prompt_manager.get_prompt()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating prompt: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations")
async def get_conversations():
    """Get all conversations with summary"""
    try:
        conversations = await persistent_queue_manager.get_all_conversations()
        return {
            "status": "success",
            "count": len(conversations),
            "conversations": conversations
        }
    except Exception as e:
        logger.error(f"Error fetching conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{chat_id}/history")
async def get_conversation_history(chat_id: str):
    """Get full message history for a conversation"""
    try:
        from uuid import UUID
        from app.db.postgres import db
        
        # Get conversation metadata from database
        chat_uuid = UUID(chat_id)
        conversation_data = await db.get_conversation(chat_uuid)
        
        if not conversation_data:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get message history
        history = await persistent_queue_manager.get_conversation_history(chat_id)
        
        conversation = {
            "chat_id": chat_id,
            "sender_linkedin_id": conversation_data['sender_linkedin_id'],
            "recipient_linkedin_id": conversation_data['recipient_linkedin_id'],
            "stage": conversation_data['stage'],
            "ai_enabled": conversation_data.get('ai_enabled', True),
            "message_count": len(history)
        }
        
        return {
            "status": "success",
            "conversation": conversation,
            "history": history
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching conversation history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversations/{chat_id}/ai/toggle")
async def toggle_conversation_ai(chat_id: str, enabled: bool):
    """
    Toggle AI responses for a specific conversation
    
    Args:
        chat_id: The conversation ID
        enabled: True to enable AI, False to disable
    """
    try:
        from uuid import UUID
        from app.db.postgres import db
        
        chat_uuid = UUID(chat_id)
        
        try:
            result = db._get_client().table('conversations').update({
                'ai_enabled': enabled,
                'updated_at': 'now()'
            }).eq('chat_id', str(chat_uuid)).execute()
            
            if result.data:
                return {"status": "success", "message": f"AI {'enabled' if enabled else 'disabled'} for conversation"}
            else:
                raise HTTPException(status_code=404, detail="Conversation not found")
        except Exception as e:
            logger.error(f"Error updating conversation AI setting: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to update AI setting: {str(e)}")
        
        logger.info(f"🤖 AI {'ENABLED' if enabled else 'DISABLED'} for conversation {chat_id}")
        
        return {
            "status": "success",
            "chat_id": chat_id,
            "ai_enabled": enabled
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling AI for chat {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/ai/toggle")
async def toggle_job_ai(job_id: str, enabled: bool):
    """
    Toggle AI responses for all conversations in a job
    
    Args:
        job_id: The job ID
        enabled: True to enable AI, False to disable
        
    Note: This affects all current and future conversations for this job
    """
    try:
        from app.db.postgres import db
        
        # Upsert job settings using Supabase
        job_result = db._get_client().table('job_settings').upsert({
            'job_id': job_id,
            'ai_enabled': enabled,
            'updated_at': 'now()'
        }).execute()
        
        # Also update existing conversations for this job
        conversations_result = db._get_client().table('conversations').update({
            'ai_enabled': enabled,
            'updated_at': 'now()'
        }).eq('job_id', job_id).execute()
        
        count = len(conversations_result.data) if conversations_result.data else 0
        
        logger.info(f"🤖 AI {'ENABLED' if enabled else 'DISABLED'} for job {job_id} ({count} conversations updated)")
        
        return {
            "status": "success",
            "job_id": job_id,
            "ai_enabled": enabled,
            "conversations_updated": count
        }
    except Exception as e:
        logger.error(f"Error toggling AI for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}/ai/status")
async def get_job_ai_status(job_id: str):
    """
    Get AI status for a job
    """
    try:
        from app.db.postgres import db
        
        result = db._get_client().table('job_settings').select('ai_enabled, updated_at').eq('job_id', job_id).execute()
        
        # Default to enabled if no setting exists
        ai_enabled = result.data[0]['ai_enabled'] if result.data else True
        updated_at = result.data[0]['updated_at'] if result.data and result.data[0]['updated_at'] else None
        
        return {
            "status": "success",
            "job_id": job_id,
            "ai_enabled": ai_enabled,
            "updated_at": updated_at
        }
    except Exception as e:
        logger.error(f"Error getting AI status for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversations/{chat_id}/send-message")
async def send_message_to_conversation(chat_id: str, request: Dict[str, str]):
    """
    Send a new message to an existing conversation from platform UI
    This is NOT an initial outreach - just continuing the conversation
    
    Request Body:
        {
            "message": "Your message content here",
            "message_type": "message"  # optional, defaults to "message"
        }
    """
    try:
        from uuid import UUID
        from app.db.postgres import db
        from app.services.queue_persistent import persistent_queue_manager
        
        chat_uuid = UUID(chat_id)
        
        # Get conversation details
        conversation = await db.get_conversation(chat_uuid)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Validate request
        if "message" not in request:
            raise HTTPException(status_code=400, detail="Missing 'message' field")
        
        message_content = request["message"]
        message_type = request.get("message_type", "message")
        
        if not message_content.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        # Enqueue the message (NOT initial outreach)
        result = await persistent_queue_manager.enqueue_message(
            unipile_account_id=conversation['unipile_account_id'],
            calendar_account_id=conversation.get('calendar_account_id'),
            sender_linkedin_id=conversation['sender_linkedin_id'],
            recipient_linkedin_id=conversation['recipient_linkedin_id'],
            job_id=conversation['job_id'],
            message=message_content,
            is_invite=False,  # Always false for UI messages
            is_initial_reachout=False,  # Always false for UI messages
            conversation_stage=conversation['stage']
        )
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return {
            "status": "success",
            "message_id": result.get("message_id"),
            "chat_id": chat_id,
            "scheduled_at": result.get("scheduled_at"),
            "message": "Message queued successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message to conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
