"""In-memory message queue manager"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import random
from app.config import settings
from app.clients.unipile import unipile_client

logger = logging.getLogger(__name__)


class QueuedMessage:
    """Represents a message in the queue"""
    
    def __init__(
        self,
        message_id: str,
        chat_id: str,
        unipile_account_id: str,
        recipient_linkedin_id: str,
        sender_linkedin_id: str,
        job_id: str,
        message: str,
        is_invite: bool,
        is_initial_reachout: bool,
        scheduled_at: datetime,
        conversation_stage: str = "initial_outreach"
    ):
        self.message_id = message_id
        self.chat_id = chat_id
        self.unipile_account_id = unipile_account_id
        self.recipient_linkedin_id = recipient_linkedin_id
        self.sender_linkedin_id = sender_linkedin_id
        self.job_id = job_id
        self.message = message
        self.is_invite = is_invite
        self.is_initial_reachout = is_initial_reachout
        self.scheduled_at = scheduled_at
        self.conversation_stage = conversation_stage
        self.status = "scheduled"
        self.retry_count = 0
        self.error_message: Optional[str] = None
        self.created_at = datetime.utcnow()
        self.sent_at: Optional[datetime] = None


class ConversationMessage:
    """Represents a message in conversation history (both inbound and outbound)"""
    
    def __init__(
        self,
        message_id: str,
        chat_id: str,
        direction: str,  # "outbound" or "inbound"
        sender_linkedin_id: str,
        recipient_linkedin_id: str,
        message: str,
        timestamp: datetime,
        has_attachment: bool = False,
        attachment_info: str = ""
    ):
        self.message_id = message_id
        self.chat_id = chat_id
        self.direction = direction
        self.sender_linkedin_id = sender_linkedin_id
        self.recipient_linkedin_id = recipient_linkedin_id
        self.message = message
        self.timestamp = timestamp
        self.has_attachment = has_attachment
        self.attachment_info = attachment_info


class QueueManager:
    """Manages the in-memory message queue"""
    
    def __init__(self):
        # message_id -> QueuedMessage
        self.messages: Dict[str, QueuedMessage] = {}
        
        # (sender_linkedin_id, recipient_linkedin_id) -> chat_id
        # Track conversations to prevent duplicate initial outreach
        self.conversations: Dict[tuple, str] = {}
        
        # chat_id -> current_conversation_stage
        # Track stage for each conversation
        self.conversation_stages: Dict[str, str] = {}
        
        # chat_id -> List[ConversationMessage]
        # Full conversation history (inbound + outbound)
        self.conversation_history: Dict[str, List[ConversationMessage]] = {}
        
        logger.info("Queue manager initialized (in-memory mode)")
    
    def calculate_scheduled_time(self) -> datetime:
        """Calculate scheduled time with random delay"""
        delay_minutes = random.randint(
            settings.DEFAULT_MIN_DELAY_MINUTES,
            settings.DEFAULT_MAX_DELAY_MINUTES
        )
        return datetime.utcnow() + timedelta(minutes=delay_minutes)
    
    def conversation_exists(self, sender_linkedin_id: str, recipient_linkedin_id: str) -> bool:
        """Check if a conversation already exists"""
        return (sender_linkedin_id, recipient_linkedin_id) in self.conversations
    
    def has_successful_initial_outreach(self, sender_linkedin_id: str, recipient_linkedin_id: str) -> bool:
        """
        Check if there's already a successfully sent initial outreach to this recipient.
        Only blocks if a message was actually sent successfully.
        Does NOT block if previous messages were: failed, cancelled, scheduled, or sending.
        """
        # Check all messages for this sender-recipient pair
        for msg in self.messages.values():
            if (msg.sender_linkedin_id == sender_linkedin_id and 
                msg.recipient_linkedin_id == recipient_linkedin_id and
                msg.is_initial_reachout and
                msg.status == "sent"):  # Only "sent" status blocks retry
                return True
        return False
    
    def get_conversation_stage(self, chat_id: str) -> str:
        """Get the current stage for a conversation"""
        return self.conversation_stages.get(chat_id, "initial_outreach")
    
    def update_conversation_stage(self, chat_id: str, stage: str):
        """Update the conversation stage"""
        self.conversation_stages[chat_id] = stage
        logger.info(f"Conversation {chat_id[:8]} stage updated to: {stage}")
    
    def add_to_conversation_history(
        self,
        chat_id: str,
        message_id: str,
        direction: str,
        sender_linkedin_id: str,
        recipient_linkedin_id: str,
        message: str,
        timestamp: Optional[datetime] = None,
        has_attachment: bool = False,
        attachment_info: str = ""
    ):
        """Add a message to conversation history"""
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        conv_msg = ConversationMessage(
            message_id=message_id,
            chat_id=chat_id,
            direction=direction,
            sender_linkedin_id=sender_linkedin_id,
            recipient_linkedin_id=recipient_linkedin_id,
            message=message,
            timestamp=timestamp,
            has_attachment=has_attachment,
            attachment_info=attachment_info
        )
        
        if chat_id not in self.conversation_history:
            self.conversation_history[chat_id] = []
        
        self.conversation_history[chat_id].append(conv_msg)
        logger.info(f"Added {direction} message to conversation {chat_id[:8]}")
    
    def get_conversation_history(self, chat_id: str) -> List[Dict[str, Any]]:
        """Get full conversation history for a chat"""
        if chat_id not in self.conversation_history:
            return []
        
        history = []
        for msg in self.conversation_history[chat_id]:
            history.append({
                "message_id": msg.message_id,
                "direction": msg.direction,
                "sender_linkedin_id": msg.sender_linkedin_id,
                "recipient_linkedin_id": msg.recipient_linkedin_id,
                "message": msg.message,
                "timestamp": msg.timestamp.isoformat(),
                "has_attachment": msg.has_attachment,
                "attachment_info": msg.attachment_info
            })
        
        # Sort by timestamp
        history.sort(key=lambda x: x["timestamp"])
        return history
    
    def get_all_conversations(self) -> List[Dict[str, Any]]:
        """Get summary of all conversations"""
        conversations = []
        
        for (sender_id, recipient_id), chat_id in self.conversations.items():
            # Get message count
            message_count = len(self.conversation_history.get(chat_id, []))
            
            # Get last message timestamp
            history = self.conversation_history.get(chat_id, [])
            last_message_time = None
            last_message_preview = ""
            
            if history:
                last_msg = history[-1]
                last_message_time = last_msg.timestamp
                last_message_preview = last_msg.message[:100]
            
            # Get current stage
            stage = self.conversation_stages.get(chat_id, "initial_outreach")
            
            # Get job_id from messages
            job_id = "unknown"
            for msg in self.messages.values():
                if msg.chat_id == chat_id:
                    job_id = msg.job_id
                    break
            
            conversations.append({
                "chat_id": chat_id,
                "sender_linkedin_id": sender_id,
                "recipient_linkedin_id": recipient_id,
                "message_count": message_count,
                "stage": stage,
                "job_id": job_id,
                "last_message_time": last_message_time.isoformat() if last_message_time else None,
                "last_message_preview": last_message_preview
            })
        
        # Sort by last message time (most recent first)
        conversations.sort(key=lambda x: x["last_message_time"] or "", reverse=True)
        return conversations
    
    def enqueue_message(
        self,
        unipile_account_id: str,
        recipient_linkedin_id: str,
        sender_linkedin_id: str,
        job_id: str,
        message: str,
        is_invite: bool,
        is_initial_reachout: bool,
        scheduled_at: Optional[datetime] = None,
        conversation_stage: str = "initial_outreach"
    ) -> Dict[str, Any]:
        """
        Add a message to the queue
        
        Returns:
            Dict with message_id, chat_id, status, scheduled_at
        """
        # Check for duplicate initial outreach
        # Only block if there's already a SUCCESSFUL initial outreach
        # Allow retry if previous attempts failed
        if is_initial_reachout:
            if self.has_successful_initial_outreach(sender_linkedin_id, recipient_linkedin_id):
                logger.warning(
                    f"Duplicate initial outreach detected (previous was successful): {sender_linkedin_id} -> {recipient_linkedin_id}"
                )
                return {
                    "status": "error",
                    "error": "Initial outreach already sent successfully to this recipient"
                }
            else:
                # If conversation exists but no successful message, allow retry
                if self.conversation_exists(sender_linkedin_id, recipient_linkedin_id):
                    logger.info(
                        f"Allowing retry for failed initial outreach: {sender_linkedin_id} -> {recipient_linkedin_id}"
                    )
        
        # Generate IDs
        message_id = str(uuid.uuid4())
        chat_id = str(uuid.uuid4())
        
        # Calculate scheduled time if not provided
        if scheduled_at is None:
            scheduled_at = self.calculate_scheduled_time()
        
        # Create queued message
        queued_msg = QueuedMessage(
            message_id=message_id,
            chat_id=chat_id,
            unipile_account_id=unipile_account_id,
            recipient_linkedin_id=recipient_linkedin_id,
            sender_linkedin_id=sender_linkedin_id,
            job_id=job_id,
            message=message,
            is_invite=is_invite,
            is_initial_reachout=is_initial_reachout,
            scheduled_at=scheduled_at,
            conversation_stage=conversation_stage
        )
        
        # Add to queue
        self.messages[message_id] = queued_msg
        
        # Track conversation
        self.conversations[(sender_linkedin_id, recipient_linkedin_id)] = chat_id
        
        # Track/update conversation stage
        self.conversation_stages[chat_id] = conversation_stage
        
        logger.info(
            f"Message queued: {message_id} | "
            f"Type: {'INVITE' if is_invite else 'MESSAGE'} | "
            f"Scheduled: {scheduled_at.isoformat()}"
        )
        
        return {
            "message_id": message_id,
            "chat_id": chat_id,
            "status": "scheduled",
            "scheduled_at": scheduled_at.isoformat()
        }
    
    def get_pending_messages(self) -> List[QueuedMessage]:
        """Get all messages that are ready to be sent"""
        now = datetime.utcnow()
        return [
            msg for msg in self.messages.values()
            if msg.status == "scheduled" and msg.scheduled_at <= now
        ]
    
    async def send_message(self, message_id: str) -> bool:
        """
        Send a queued message via Unipile
        
        Returns:
            True if successful, False otherwise
        """
        msg = self.messages.get(message_id)
        if not msg:
            logger.error(f"Message not found: {message_id}")
            return False
        
        try:
            msg.status = "sending"
            
            # Send via Unipile
            if msg.is_invite:
                result = await unipile_client.send_invitation(
                    account_id=msg.unipile_account_id,
                    recipient_linkedin_id=msg.recipient_linkedin_id,
                    message=msg.message
                )
            else:
                result = await unipile_client.send_message(
                    account_id=msg.unipile_account_id,
                    recipient_linkedin_id=msg.recipient_linkedin_id,
                    message=msg.message
                )
            
            # Update status
            msg.status = "sent"
            msg.sent_at = datetime.utcnow()
            
            # Log to conversation history
            self.add_to_conversation_history(
                chat_id=msg.chat_id,
                message_id=message_id,
                direction="outbound",
                sender_linkedin_id=msg.sender_linkedin_id,
                recipient_linkedin_id=msg.recipient_linkedin_id,
                message=msg.message,
                timestamp=msg.sent_at
            )
            
            logger.info(f"Message sent successfully: {message_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message {message_id}: {e}")
            
            msg.retry_count += 1
            msg.error_message = str(e)
            
            if msg.retry_count >= settings.MAX_RETRY_ATTEMPTS:
                msg.status = "error"
                logger.error(f"Message {message_id} failed after {msg.retry_count} retries")
            else:
                msg.status = "scheduled"
                # Reschedule with delay
                msg.scheduled_at = datetime.utcnow() + timedelta(minutes=5)
                logger.info(f"Message {message_id} rescheduled for retry {msg.retry_count}")
            
            return False
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        status_counts = {}
        for msg in self.messages.values():
            status_counts[msg.status] = status_counts.get(msg.status, 0) + 1
        
        return {
            "total_messages": len(self.messages),
            "total_conversations": len(self.conversations),
            "by_status": status_counts,
            "pending_count": len(self.get_pending_messages())
        }
    
    def cancel_message(self, message_id: str) -> bool:
        """Cancel a scheduled message"""
        msg = self.messages.get(message_id)
        if not msg:
            return False
        
        if msg.status in ["sent", "error"]:
            logger.warning(f"Cannot cancel message {message_id} with status: {msg.status}")
            return False
        
        msg.status = "cancelled"
        logger.info(f"Message cancelled: {message_id}")
        return True


# Global queue manager instance
queue_manager = QueueManager()

