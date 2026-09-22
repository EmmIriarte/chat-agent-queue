"""
Supabase Database Layer
Handles all database operations for conversations and messages using Supabase Python client
"""

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

from app.config import settings
from app.database import get_supabase_client

logger = logging.getLogger(__name__)


class SupabaseDB:
    """
    Supabase database operations using Python client
    """
    
    def __init__(self):
        self._client = None
        
    def _get_client(self):
        """Get Supabase client, initializing if needed (lazy initialization)"""
        if self._client is None:
            supabase_client_instance = get_supabase_client()
            self._client = supabase_client_instance.client
            if not self._client:
                logger.error("Supabase client not initialized")
                raise Exception("Supabase client not available")
        return self._client
        
    async def connect(self):
        """Initialize Supabase connection (already done in supabase_client)"""
        try:
            # Access client to ensure it's initialized
            _ = self._get_client()
            logger.info("✅ Supabase client connected")
                
        except Exception as e:
            logger.error(f"❌ Failed to connect to Supabase: {e}")
            raise
            
    async def disconnect(self):
        """Nothing to disconnect - Supabase handles connection pooling"""
        logger.info("Supabase disconnect (no-op)")
    
    # =========================================================================
    # CONVERSATION OPERATIONS
    # =========================================================================
    
    async def create_conversation(
        self,
        chat_id: UUID,
        sender_linkedin_id: str,
        recipient_linkedin_id: str,
        unipile_account_id: str,
        calendar_account_id: Optional[str],
        job_id: str,
        stage: str = "initial_outreach",
        ai_enabled: bool = True
    ) -> Dict[str, Any]:
        """Create a new conversation"""
        try:
            data = {
                "chat_id": str(chat_id),
                "sender_linkedin_id": sender_linkedin_id,
                "recipient_linkedin_id": recipient_linkedin_id,
                "unipile_account_id": unipile_account_id,
                "calendar_account_id": calendar_account_id,
                "job_id": job_id,
                "stage": stage,
                "ai_enabled": ai_enabled
            }
            
            result = self._get_client().table("conversations").insert(data).execute()
            
            if result.data and len(result.data) > 0:
                logger.info(f"✅ Created conversation: {chat_id}")
                return result.data[0]
            else:
                raise Exception("No data returned from conversation insert")
                
        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
            raise
    
    async def get_conversation(self, chat_id: UUID) -> Optional[Dict[str, Any]]:
        """Get conversation by chat_id"""
        try:
            result = self._get_client().table("conversations").select("*").eq("chat_id", str(chat_id)).execute()
            return result.data[0] if result.data and len(result.data) > 0 else None
        except Exception as e:
            logger.error(f"Error getting conversation: {e}")
            return None
    
    async def find_conversation(
        self,
        sender_linkedin_id: str,
        recipient_linkedin_id: str
    ) -> Optional[Dict[str, Any]]:
        """Find conversation by sender-recipient pair (checks both directions)"""
        try:
            # Try A->B first
            result = self._get_client().table("conversations")\
                .select("*")\
                .eq("sender_linkedin_id", sender_linkedin_id)\
                .eq("recipient_linkedin_id", recipient_linkedin_id)\
                .execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            
            # Try B->A
            result = self._get_client().table("conversations")\
                .select("*")\
                .eq("sender_linkedin_id", recipient_linkedin_id)\
                .eq("recipient_linkedin_id", sender_linkedin_id)\
                .execute()
            
            return result.data[0] if result.data and len(result.data) > 0 else None
            
        except Exception as e:
            logger.error(f"Error finding conversation: {e}")
            return None
    
    async def update_conversation_stage(
        self,
        chat_id: UUID,
        stage: str
    ) -> bool:
        """Update conversation stage"""
        try:
            result = self._get_client().table("conversations")\
                .update({"stage": stage})\
                .eq("chat_id", str(chat_id))\
                .execute()
            
            return result.data and len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error updating conversation stage: {e}")
            return False
    
    async def list_conversations_by_job(self, job_id: str) -> List[Dict[str, Any]]:
        """Get all conversations for a specific job"""
        try:
            result = self._get_client().table("conversations")\
                .select("*")\
                .eq("job_id", job_id)\
                .order("created_at", desc=True)\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error listing conversations by job: {e}")
            return []
    
    async def list_all_conversations(self) -> List[Dict[str, Any]]:
        """Get all conversations"""
        try:
            result = self._get_client().table("conversations")\
                .select("*")\
                .order("updated_at", desc=True)\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error listing all conversations: {e}")
            return []
    
    # =========================================================================
    # MESSAGE OPERATIONS
    # =========================================================================
    
    async def create_message(
        self,
        message_id: UUID,
        chat_id: UUID,
        sender_linkedin_id: str,
        recipient_linkedin_id: str,
        unipile_account_id: str,
        job_id: str,
        message: str,
        direction: str,
        message_type: str = "message",
        is_initial_reachout: bool = False,
        status: str = "scheduled",
        scheduled_at: Optional[datetime] = None,
        conversation_stage: Optional[str] = None,
        has_attachment: bool = False,
        attachment_info: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new message"""
        try:
            data = {
                "message_id": str(message_id),
                "chat_id": str(chat_id),
                "sender_linkedin_id": sender_linkedin_id,
                "recipient_linkedin_id": recipient_linkedin_id,
                "unipile_account_id": unipile_account_id,
                "job_id": job_id,
                "message": message,
                "direction": direction,
                "message_type": message_type,
                "is_initial_reachout": is_initial_reachout,
                "status": status,
                "scheduled_at": scheduled_at.isoformat() if scheduled_at else None,
                "conversation_stage": conversation_stage,
                "has_attachment": has_attachment,
                "attachment_info": attachment_info
            }
            
            result = self._get_client().table("messages").insert(data).execute()
            
            if result.data and len(result.data) > 0:
                logger.info(f"✅ Created message: {message_id} ({direction}, {status})")
                return result.data[0]
            else:
                raise Exception("No data returned from message insert")
                
        except Exception as e:
            logger.error(f"Error creating message: {e}")
            raise
    
    async def get_message(self, message_id: UUID) -> Optional[Dict[str, Any]]:
        """Get message by ID"""
        try:
            result = self._get_client().table("messages")\
                .select("*")\
                .eq("message_id", str(message_id))\
                .execute()
            
            return result.data[0] if result.data and len(result.data) > 0 else None
            
        except Exception as e:
            logger.error(f"Error getting message: {e}")
            return None
    
    async def update_message_status(
        self,
        message_id: UUID,
        status: str,
        error_message: Optional[str] = None,
        sent_at: Optional[datetime] = None
    ) -> bool:
        """Update message status"""
        try:
            update_data = {"status": status}
            if error_message is not None:
                update_data["error_message"] = error_message
            if sent_at is not None:
                update_data["sent_at"] = sent_at.isoformat()
            
            result = self._get_client().table("messages")\
                .update(update_data)\
                .eq("message_id", str(message_id))\
                .execute()
            
            return result.data and len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error updating message status: {e}")
            return False
    
    async def increment_retry_count(self, message_id: UUID) -> int:
        """Increment retry count and return new value"""
        try:
            # Get current count first
            msg = await self.get_message(message_id)
            if not msg:
                return 0
            
            new_count = (msg.get("retry_count", 0) or 0) + 1
            
            result = self._get_client().table("messages")\
                .update({"retry_count": new_count})\
                .eq("message_id", str(message_id))\
                .execute()
            
            return new_count if result.data else 0
            
        except Exception as e:
            logger.error(f"Error incrementing retry count: {e}")
            return 0
    
    async def list_scheduled_messages(self) -> List[Dict[str, Any]]:
        """Get all scheduled messages ready to be sent"""
        try:
            from datetime import datetime, timezone
            
            now = datetime.now(timezone.utc).isoformat()
            
            result = self._get_client().table("messages")\
                .select("*")\
                .eq("status", "scheduled")\
                .lte("scheduled_at", now)\
                .order("scheduled_at")\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error listing scheduled messages: {e}")
            return []
    
    async def list_all_messages(self) -> List[Dict[str, Any]]:
        """Get all messages"""
        try:
            result = self._get_client().table("messages")\
                .select("*")\
                .order("created_at", desc=True)\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error listing all messages: {e}")
            return []
    
    async def list_messages_by_chat(self, chat_id: UUID) -> List[Dict[str, Any]]:
        """Get all messages for a conversation"""
        try:
            result = self._get_client().table("messages")\
                .select("*")\
                .eq("chat_id", str(chat_id))\
                .order("created_at")\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error listing messages by chat: {e}")
            return []
    
    async def list_messages_by_job(self, job_id: str) -> List[Dict[str, Any]]:
        """Get all messages for a specific job"""
        try:
            result = self._get_client().table("messages")\
                .select("*")\
                .eq("job_id", job_id)\
                .order("created_at")\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error listing messages by job: {e}")
            return []
    
    async def check_successful_initial_outreach(
        self,
        sender_linkedin_id: str,
        recipient_linkedin_id: str
    ) -> bool:
        """Check if there's already a successful initial outreach"""
        try:
            result = self._get_client().table("messages")\
                .select("message_id")\
                .eq("sender_linkedin_id", sender_linkedin_id)\
                .eq("recipient_linkedin_id", recipient_linkedin_id)\
                .eq("is_initial_reachout", True)\
                .eq("status", "sent")\
                .limit(1)\
                .execute()
            
            return result.data and len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error checking initial outreach: {e}")
            return False
    
    # =========================================================================
    # ANALYTICS & SUMMARY QUERIES
    # =========================================================================
    
    async def get_queue_statistics(self) -> Dict[str, Any]:
        """Get overall queue statistics"""
        try:
            # Get all messages for stats
            result = self._get_client().table("messages").select("*").execute()
            messages = result.data if result.data else []
            
            stats = {
                "total_messages": len(messages),
                "scheduled": len([m for m in messages if m.get("status") == "scheduled"]),
                "sent": len([m for m in messages if m.get("status") == "sent"]),
                "error": len([m for m in messages if m.get("status") == "error"]),
                "cancelled": len([m for m in messages if m.get("status") == "cancelled"]),
                "total_conversations": len(set([m.get("chat_id") for m in messages if m.get("chat_id")])),
                "total_jobs": len(set([m.get("job_id") for m in messages if m.get("job_id")]))
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting queue statistics: {e}")
            raise
    
    async def get_conversation_summary_by_job(self, job_id: str) -> List[Dict[str, Any]]:
        """Get conversation summary for a specific job with message counts"""
        try:
            # Get all conversations for this job
            conv_result = self.client.table("conversations")\
                .select("*")\
                .eq("job_id", job_id)\
                .execute()
            
            conversations = conv_result.data if conv_result.data else []
            chat_ids = [c.get("chat_id") for c in conversations if c.get("chat_id")]
            
            # Get all messages for these conversations
            messages = []
            for chat_id in chat_ids:
                msg_result = self.client.table("messages")\
                    .select("*")\
                    .eq("chat_id", chat_id)\
                    .execute()
                
                if msg_result.data:
                    messages.extend(msg_result.data)
            
            # Build summary
            summary = []
            for conv in conversations:
                conv_messages = [m for m in messages if m.get("chat_id") == conv.get("chat_id")]
                
                summary.append({
                    "chat_id": conv.get("chat_id"),
                    "sender_linkedin_id": conv.get("sender_linkedin_id"),
                    "recipient_linkedin_id": conv.get("recipient_linkedin_id"),
                    "stage": conv.get("stage"),
                    "created_at": conv.get("created_at"),
                    "total_messages": len(conv_messages),
                    "inbound_messages": len([m for m in conv_messages if m.get("direction") == "inbound"]),
                    "outbound_messages": len([m for m in conv_messages if m.get("direction") == "outbound"]),
                    "sent_messages": len([m for m in conv_messages if m.get("status") == "sent"]),
                    "scheduled_messages": len([m for m in conv_messages if m.get("status") == "scheduled"]),
                    "error_messages": len([m for m in conv_messages if m.get("status") == "error"]),
                    "last_message_at": max([m.get("created_at") for m in conv_messages], default=None)
                })
            
            return sorted(summary, key=lambda x: x.get("last_message_at") or "", reverse=True)
            
        except Exception as e:
            logger.error(f"Error getting conversation summary by job: {e}")
            return []
    
    async def list_all_conversations(self) -> List[Dict[str, Any]]:
        """Get all conversations with message counts"""
        try:
            result = self._get_client().table("conversations")\
                .select("*")\
                .order("updated_at", desc=True)\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error listing all conversations: {e}")
            return []
    
    async def get_fresh_message_for_chat(self, chat_id: UUID) -> Optional[Dict[str, Any]]:
        """Get the latest message content for sending as fresh message"""
        try:
            # Get conversation
            conv_result = self.client.table("conversations")\
                .select("*")\
                .eq("chat_id", str(chat_id))\
                .execute()
            
            if not conv_result.data or len(conv_result.data) == 0:
                return None
            
            conversation = conv_result.data[0]
            
            # Get latest outbound message
            msg_result = self.client.table("messages")\
                .select("*")\
                .eq("chat_id", str(chat_id))\
                .eq("direction", "outbound")\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            
            if not msg_result.data or len(msg_result.data) == 0:
                return None
            
            return {
                "conversation": conversation,
                "latest_message": msg_result.data[0]
            }
            
        except Exception as e:
            logger.error(f"Error getting fresh message: {e}")
            raise


# Global instance - create but don't initialize client until connect() is called
db = SupabaseDB()
