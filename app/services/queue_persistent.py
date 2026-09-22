"""
PostgreSQL-backed Queue Manager
Replaces in-memory storage with database persistence
"""

import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import uuid4, UUID
import httpx

from app.config import settings
from app.db.postgres import db
from app.clients.unipile import UnipileClient
from app.utils.http_errors import parse_http_error, serialize_error, enrich_message

logger = logging.getLogger(__name__)


class PersistentQueueManager:
    """
    Queue manager using PostgreSQL for all storage
    """
    
    def __init__(self):
        self.unipile_client = UnipileClient()
        self.min_delay_minutes = settings.DEFAULT_MIN_DELAY_MINUTES
        self.max_delay_minutes = settings.DEFAULT_MAX_DELAY_MINUTES
        logger.info(f"🗄️  PersistentQueueManager initialized (Delay: {self.min_delay_minutes}-{self.max_delay_minutes} mins)")
    
    def _calculate_scheduled_time(self) -> datetime:
        """Calculate random scheduled time within configured delay range"""
        delay_minutes = random.uniform(self.min_delay_minutes, self.max_delay_minutes)
        return datetime.now() + timedelta(minutes=delay_minutes)
    
    async def enqueue_message(
        self,
        unipile_account_id: str,
        calendar_account_id: Optional[str],
        sender_linkedin_id: str,
        recipient_linkedin_id: str,
        job_id: str,
        message: str,
        is_invite: bool = False,
        is_initial_reachout: bool = False,
        conversation_stage: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enqueue a new message to the database
        
        Args:
            unipile_account_id: LinkedIn Unipile account ID (for messaging)
            calendar_account_id: Outlook/Google Unipile account ID (for calendar) - optional
            sender_linkedin_id: LinkedIn ID of sender
            recipient_linkedin_id: LinkedIn ID of recipient
            job_id: Job identifier
            message: Message content
            is_invite: Whether this is a connection invite
            is_initial_reachout: Whether this is the first contact
            conversation_stage: Current conversation stage
        """
        try:
            # Check for duplicate initial outreach
            if is_initial_reachout:
                has_successful = await db.check_successful_initial_outreach(
                    sender_linkedin_id, recipient_linkedin_id
                )
                if has_successful:
                    logger.warning(f"⚠️  Initial outreach already sent to {recipient_linkedin_id}")
                    return {
                        "status": "duplicate",
                        "message": "Initial outreach already exists for this recipient"
                    }
            
            # Find or create conversation
            conversation = await db.find_conversation(sender_linkedin_id, recipient_linkedin_id)
            
            if not conversation:
                chat_id = uuid4()
                
                # Check job-level AI setting; auto AI stays off until a calendar is linked
                job_ai_enabled = True
                try:
                    job_result = db._get_client().table('job_settings').select('ai_enabled').eq('job_id', job_id).execute()
                    if job_result.data:
                        job_ai_enabled = job_result.data[0]['ai_enabled']
                except Exception as e:
                    logger.warning(f"Could not fetch job AI setting: {e}")
                
                ai_enabled = bool(calendar_account_id) and job_ai_enabled
                
                conversation = await db.create_conversation(
                    chat_id=chat_id,
                    sender_linkedin_id=sender_linkedin_id,
                    recipient_linkedin_id=recipient_linkedin_id,
                    unipile_account_id=unipile_account_id,
                    calendar_account_id=calendar_account_id,
                    job_id=job_id,
                    stage=conversation_stage or "initial_outreach",
                    ai_enabled=ai_enabled
                )
                calendar_status = f"Calendar: {calendar_account_id}" if calendar_account_id else "Calendar: None"
                logger.info(f"📝 Created new conversation: {chat_id} (AI: {ai_enabled}, {calendar_status})")
            else:
                chat_id = conversation['chat_id']
                logger.info(f"📝 Using existing conversation: {chat_id}")
            
            # Create message
            message_id = uuid4()
            scheduled_at = self._calculate_scheduled_time()
            message_type = "invite" if is_invite else "message"
            
            created_message = await db.create_message(
                message_id=message_id,
                chat_id=chat_id,
                sender_linkedin_id=sender_linkedin_id,
                recipient_linkedin_id=recipient_linkedin_id,
                unipile_account_id=unipile_account_id,
                job_id=job_id,
                message=message,
                direction="outbound",
                message_type=message_type,
                is_initial_reachout=is_initial_reachout,
                status="scheduled",
                scheduled_at=scheduled_at,
                conversation_stage=conversation_stage
            )
            
            logger.info(f"✅ Message enqueued: {message_id} (scheduled for {scheduled_at})")
            
            return {
                "status": "success",
                "message_id": str(message_id),
                "chat_id": str(chat_id),
                "scheduled_at": scheduled_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error enqueueing message: {e}", exc_info=True)
            raise
    
    async def cancel_message(self, message_id: str) -> Dict[str, Any]:
        """Cancel a scheduled message"""
        try:
            message_uuid = UUID(message_id)
            message = await db.get_message(message_uuid)
            
            if not message:
                return {"status": "error", "message": "Message not found"}
            
            if message['status'] not in ['scheduled', 'sending']:
                return {
                    "status": "error",
                    "message": f"Cannot cancel message with status: {message['status']}"
                }
            
            await db.update_message_status(message_uuid, "cancelled")
            logger.info(f"🚫 Cancelled message: {message_id}")
            
            return {"status": "success", "message": "Message cancelled"}
            
        except Exception as e:
            logger.error(f"Error cancelling message: {e}")
            raise
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """Get overall queue statistics"""
        try:
            stats = await db.get_queue_statistics()
            return {
                "status": "success",
                "statistics": {
                    "total_messages": stats['total_messages'],
                    "scheduled": stats['scheduled'],
                    "sent": stats['sent'],
                    "error": stats['error'],
                    "cancelled": stats['cancelled'],
                    "total_conversations": stats['total_conversations'],
                    "total_jobs": stats['total_jobs']
                }
            }
        except Exception as e:
            logger.error(f"Error getting queue status: {e}")
            raise
    
    async def get_all_messages(self) -> Dict[str, Any]:
        """Get all messages with details"""
        try:
            messages = await db.list_all_messages()
            
            formatted_messages = []
            for msg in messages:
                row = {
                    "message_id": str(msg['message_id']),
                    "chat_id": str(msg['chat_id']),
                    "sender_linkedin_id": msg['sender_linkedin_id'],
                    "recipient_linkedin_id": msg['recipient_linkedin_id'],
                    "unipile_account_id": msg['unipile_account_id'],
                    "job_id": msg['job_id'],
                    "message": msg['message'],
                    "direction": msg['direction'],
                    "message_type": msg['message_type'],
                    "is_initial_reachout": msg['is_initial_reachout'],
                    "status": msg['status'],
                    "scheduled_at": msg['scheduled_at'] if isinstance(msg['scheduled_at'], str) else (msg['scheduled_at'].isoformat() if msg['scheduled_at'] else None),
                    "retry_count": msg['retry_count'],
                    "error_message": msg['error_message'],
                    "conversation_stage": msg['conversation_stage'],
                    "has_attachment": msg['has_attachment'],
                    "attachment_info": msg['attachment_info'],
                    "created_at": msg['created_at'] if isinstance(msg['created_at'], str) else msg['created_at'].isoformat(),
                    "sent_at": msg['sent_at'] if isinstance(msg['sent_at'], str) else (msg['sent_at'].isoformat() if msg['sent_at'] else None)
                }
                formatted_messages.append(enrich_message(row))
            
            return {
                "status": "success",
                "count": len(formatted_messages),
                "messages": formatted_messages
            }
        except Exception as e:
            logger.error(f"Error getting all messages: {e}")
            raise
    
    async def process_queue(self):
        """
        Process scheduled messages (called by APScheduler)
        """
        try:
            # Get all scheduled messages ready to send
            messages = await db.list_scheduled_messages()
            
            if not messages:
                return
            
            logger.info(f"🔄 Processing {len(messages)} scheduled message(s)...")
            
            for msg in messages:
                message_id = msg['message_id']
                
                try:
                    # Mark as sending
                    await db.update_message_status(message_id, "sending")
                    
                    # Send via Unipile
                    if msg['message_type'] == 'invite':
                        await self.unipile_client.send_invitation(
                            account_id=msg['unipile_account_id'],
                            recipient_linkedin_id=msg['recipient_linkedin_id'],
                            message=msg['message']
                        )
                    else:
                        await self.unipile_client.send_message(
                            account_id=msg['unipile_account_id'],
                            recipient_linkedin_id=msg['recipient_linkedin_id'],
                            message=msg['message']
                        )
                    
                    # Mark as sent
                    await db.update_message_status(message_id, "sent", sent_at=datetime.now())
                    
                    # No need to add to conversation history - the message record already exists
                    # with status="sent" which is part of the conversation history
                    
                    logger.info(f"✅ Sent message: {message_id}")
                    
                except httpx.HTTPError as e:
                    retry_count = await db.increment_retry_count(message_id)
                    parsed = parse_http_error(e)
                    error_msg = serialize_error(parsed)
                    log_msg = parsed.get("display") or str(e)

                    if retry_count >= settings.MAX_RETRY_ATTEMPTS:
                        await db.update_message_status(message_id, "error", error_message=error_msg)
                        logger.error(
                            f"❌ Message {message_id} failed after {retry_count} attempts: "
                            f"{parsed.get('type') or log_msg}"
                        )
                    else:
                        new_scheduled_time = self._calculate_scheduled_time()
                        try:
                            db._get_client().table('messages').update({
                                'status': 'scheduled',
                                'scheduled_at': new_scheduled_time.isoformat(),
                                'error_message': error_msg
                            }).eq('message_id', str(message_id)).execute()
                            logger.warning(
                                f"⚠️  Retry {retry_count}/{settings.MAX_RETRY_ATTEMPTS} for {message_id}: {log_msg}"
                            )
                        except Exception as reschedule_err:
                            logger.error(f"Error rescheduling message {message_id}: {reschedule_err}")
                
                except Exception as e:
                    parsed = parse_http_error(e)
                    error_msg = serialize_error(parsed)
                    await db.update_message_status(message_id, "error", error_message=error_msg)
                    logger.error(f"❌ Error processing message {message_id}: {parsed.get('display') or str(e)}")
        
        except Exception as e:
            logger.error(f"Error in process_queue: {e}", exc_info=True)
    
    async def add_to_conversation_history(
        self,
        chat_id: UUID,
        message: str,
        direction: str,
        has_attachment: bool = False,
        attachment_info: Optional[str] = None,
        conversation_stage: Optional[str] = None
    ) -> None:
        """
        Add a message to conversation history (for inbound messages from webhook)
        """
        try:
            # Get conversation details
            conversation = await db.get_conversation(chat_id)
            
            if not conversation:
                logger.warning(f"Conversation {chat_id} not found for history entry")
                return
            
            # Create history message (status='history' for inbound)
            message_id = uuid4()
            await db.create_message(
                message_id=message_id,
                chat_id=chat_id,
                sender_linkedin_id=conversation['sender_linkedin_id'] if direction == 'outbound' else conversation['recipient_linkedin_id'],
                recipient_linkedin_id=conversation['recipient_linkedin_id'] if direction == 'outbound' else conversation['sender_linkedin_id'],
                unipile_account_id=conversation['unipile_account_id'],
                job_id=conversation['job_id'],
                message=message,
                direction=direction,
                status="history",
                scheduled_at=None,
                conversation_stage=conversation_stage,
                has_attachment=has_attachment,
                attachment_info=attachment_info
            )
            
            logger.info(f"📝 Added {direction} message to conversation {chat_id}")
            
        except Exception as e:
            logger.error(f"Error adding to conversation history: {e}", exc_info=True)
    
    async def get_conversation_history(self, chat_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for a specific chat"""
        try:
            chat_uuid = UUID(chat_id)
            messages = await db.list_messages_by_chat(chat_uuid)
            
            history = []
            for msg in messages:
                row = {
                    "message_id": str(msg['message_id']),
                    "message": msg['message'],
                    "direction": msg['direction'],
                    "status": msg.get("status"),
                    "timestamp": msg['created_at'] if isinstance(msg['created_at'], str) else msg['created_at'].isoformat(),
                    "has_attachment": msg['has_attachment'],
                    "attachment_info": msg['attachment_info'],
                    "conversation_stage": msg['conversation_stage'],
                    "error_message": msg.get("error_message"),
                }
                history.append(enrich_message(row))
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            raise
    
    async def get_all_conversations(self) -> List[Dict[str, Any]]:
        """Get summary of all conversations"""
        try:
            conversations = await db.list_all_conversations()
            
            formatted = []
            for conv in conversations:
                # Get message count
                messages = await db.list_messages_by_chat(conv['chat_id'])
                
                # Get job-level AI setting
                job_ai_enabled = None
                try:
                    job_result = db._get_client().table('job_settings').select('ai_enabled').eq('job_id', conv['job_id']).execute()
                    if job_result.data:
                        job_ai_enabled = job_result.data[0]['ai_enabled']
                except Exception as e:
                    logger.warning(f"Could not fetch job AI setting: {e}")
                
                formatted.append({
                    "chat_id": str(conv['chat_id']),
                    "sender_linkedin_id": conv['sender_linkedin_id'],
                    "recipient_linkedin_id": conv['recipient_linkedin_id'],
                    "stage": conv['stage'],
                    "job_id": conv['job_id'],
                    "conversation_ai_enabled": conv.get('ai_enabled', True),
                    "job_ai_enabled": job_ai_enabled,
                    "message_count": len(messages),
                    "created_at": conv['created_at'] if isinstance(conv['created_at'], str) else conv['created_at'].isoformat(),
                    "updated_at": conv['updated_at'] if isinstance(conv['updated_at'], str) else conv['updated_at'].isoformat()
                })
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error getting all conversations: {e}")
            raise
    
    async def get_conversations_by_job(self, job_id: str) -> Dict[str, Any]:
        """Get detailed conversation summary for a specific job"""
        try:
            summary = await db.get_conversation_summary_by_job(job_id)
            
            formatted = []
            for conv in summary:
                formatted.append({
                    "chat_id": str(conv['chat_id']),
                    "sender_linkedin_id": conv['sender_linkedin_id'],
                    "recipient_linkedin_id": conv['recipient_linkedin_id'],
                    "stage": conv['stage'],
                    "created_at": conv['created_at'].isoformat(),
                    "statistics": {
                        "total_messages": conv['total_messages'],
                        "inbound_messages": conv['inbound_messages'],
                        "outbound_messages": conv['outbound_messages'],
                        "sent_messages": conv['sent_messages'],
                        "scheduled_messages": conv['scheduled_messages'],
                        "error_messages": conv['error_messages']
                    },
                    "last_message_at": conv['last_message_at'].isoformat() if conv['last_message_at'] else None
                })
            
            return {
                "status": "success",
                "job_id": job_id,
                "count": len(formatted),
                "conversations": formatted
            }
            
        except Exception as e:
            logger.error(f"Error getting conversations by job: {e}")
            raise
    
    async def get_messages_by_job(self, job_id: str) -> Dict[str, Any]:
        """Get all messages for a specific job"""
        try:
            messages = await db.list_messages_by_job(job_id)
            
            formatted = []
            for msg in messages:
                formatted.append({
                    "message_id": str(msg['message_id']),
                    "chat_id": str(msg['chat_id']),
                    "sender_linkedin_id": msg['sender_linkedin_id'],
                    "recipient_linkedin_id": msg['recipient_linkedin_id'],
                    "message": msg['message'],
                    "direction": msg['direction'],
                    "status": msg['status'],
                    "created_at": msg['created_at'].isoformat(),
                    "sent_at": msg['sent_at'].isoformat() if msg['sent_at'] else None
                })
            
            return {
                "status": "success",
                "job_id": job_id,
                "count": len(formatted),
                "messages": formatted
            }
            
        except Exception as e:
            logger.error(f"Error getting messages by job: {e}")
            raise
    
    def get_conversation_stage(self, chat_id: str) -> str:
        """Get current conversation stage (sync wrapper for async)"""
        # This is a helper for compatibility - in production use async version
        import asyncio
        try:
            chat_uuid = UUID(chat_id)
            conv = asyncio.run(db.get_conversation(chat_uuid))
            return conv['stage'] if conv else "unknown"
        except:
            return "unknown"


# Global instance
persistent_queue_manager = PersistentQueueManager()

