"""Pydantic schemas for API requests and responses"""
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class ApiErrorDetail(BaseModel):
    """Structured provider/API error (e.g. Unipile / LinkedIn)."""
    status: Optional[int] = None
    type: Optional[str] = None
    title: Optional[str] = None
    detail: Optional[str] = None
    source: Optional[str] = None


# Unipile Webhook Schemas
class UnipileAttendee(BaseModel):
    """Attendee in a conversation"""
    attendee_id: str
    attendee_name: str
    attendee_provider_id: str  # LinkedIn ID
    attendee_profile_url: Optional[str] = None
    attendee_specifics: Optional[dict] = None


class UnipileAccountInfo(BaseModel):
    """Account information from Unipile"""
    type: str  # 'LINKEDIN', 'INSTAGRAM', etc.
    feature: str  # 'classic', 'organization', 'sales_navigator', 'recruiter'
    user_id: str  # LinkedIn provider ID of account owner


class UnipileSender(BaseModel):
    """Sender information"""
    attendee_id: str
    attendee_name: str
    attendee_provider_id: str  # LinkedIn ID
    attendee_profile_url: Optional[str] = None
    attendee_specifics: Optional[dict] = None


class UnipileAttachment(BaseModel):
    """Message attachment (optional)"""
    id: Optional[str] = None
    size: Optional[dict] = None
    sticker: Optional[str] = None
    unavailable: Optional[str] = None
    mimetype: Optional[str] = None
    type: Optional[str] = None
    url: Optional[str] = None


class UnipileWebhookPayload(BaseModel):
    """Complete Unipile webhook payload"""
    account_id: str  # Unipile account ID
    account_type: str  # 'LINKEDIN', 'INSTAGRAM', 'WHATSAPP', 'TELEGRAM'
    account_info: UnipileAccountInfo
    event: str  # 'message_received', 'message_reaction', 'message_read', etc.
    chat_id: str  # Unipile chat ID
    timestamp: str  # ISO 8601 timestamp
    webhook_name: str
    message_id: str  # Unipile message ID
    message: str  # Message content
    sender: UnipileSender
    attendees: List[UnipileAttendee]
    attachments: List = []  # Can be empty list or list of attachment objects
    reaction: Optional[str] = None
    reaction_sender: Optional[UnipileSender] = None
    
    # Additional fields from real payload
    subject: Optional[str] = None
    provider_chat_id: Optional[str] = None
    provider_message_id: Optional[str] = None
    is_event: Optional[int] = None
    quoted: Optional[str] = None
    chat_content_type: Optional[str] = None
    message_type: Optional[str] = None
    is_group: Optional[bool] = None
    folder: Optional[List[str]] = None


# API Response Schemas
class WebhookResponse(BaseModel):
    """Response for webhook handler"""
    status: Literal["success", "error"]
    message: Optional[str] = None
    message_id: Optional[str] = None  # Our internal message_id if response queued
    chat_id: Optional[str] = None  # Our internal chat_id


class EnqueueMessageRequest(BaseModel):
    """Request to enqueue a new message"""
    unipile_account_id: str  # LinkedIn Unipile account ID (for messaging)
    calendar_account_id: Optional[str] = None  # Outlook/Google Unipile account ID (for calendar booking)
    recipient_linkedin_id: str
    job_id: str
    message: str
    is_invite: bool
    is_initial_reachout: bool
    scheduled_at: Optional[datetime] = None


class EnqueueMessageResponse(BaseModel):
    """Response for enqueue message"""
    message_id: str
    chat_id: str
    status: str
    scheduled_at: str
    error: Optional[str] = None


class BatchEnqueueRequest(BaseModel):
    """Request to enqueue multiple messages"""
    jobs: List[EnqueueMessageRequest]


class BatchEnqueueResponse(BaseModel):
    """Response for batch enqueue"""
    status: str
    total_jobs: int
    queued: int
    failed: int
    results: List[EnqueueMessageResponse]
    errors: List[str] = []

