"""Calendar service for managing Unipile calendar operations"""
import logging
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime, timedelta
from app.clients.unipile import unipile_client

logger = logging.getLogger(__name__)


class CalendarService:
    """Service for calendar operations"""
    
    def __init__(self):
        self.unipile_client = unipile_client
    
    async def find_default_calendar(self, calendar_account_id: str) -> Optional[str]:
        """
        Find the default calendar ID for a given account
        
        Args:
            calendar_account_id: The Outlook/Google Unipile account ID
            
        Returns:
            Calendar ID string, or None if not found
        """
        try:
            # Get all calendars for this account
            calendars_response = await self.unipile_client.get_calendars(calendar_account_id)
            calendars = calendars_response.get('data', [])
            
            if not calendars:
                logger.warning(f"⚠️  No calendars found for account: {calendar_account_id}")
                return None
            
            # Strategy 1: Find the default calendar that user owns
            for calendar in calendars:
                if calendar.get('is_default') and calendar.get('is_owned_by_user'):
                    calendar_id = calendar['id']
                    calendar_name = calendar.get('name', 'Unknown')
                    logger.info(f"✅ Found default calendar: '{calendar_name}' (ID: {calendar_id[:30]}...)")
                    return calendar_id
            
            # Strategy 2: Fallback to first owned, writable calendar
            for calendar in calendars:
                if calendar.get('is_owned_by_user') and not calendar.get('is_read_only'):
                    calendar_id = calendar['id']
                    calendar_name = calendar.get('name', 'Unknown')
                    logger.warning(f"⚠️  No default calendar found, using first owned: '{calendar_name}'")
                    return calendar_id
            
            # Strategy 3: Last resort - any calendar
            if calendars:
                calendar_id = calendars[0]['id']
                calendar_name = calendars[0].get('name', 'Unknown')
                logger.warning(f"⚠️  Using first available calendar: '{calendar_name}'")
                return calendar_id
            
            logger.error(f"❌ No suitable calendar found for account: {calendar_account_id}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error finding default calendar: {e}", exc_info=True)
            return None
    
    async def get_or_cache_calendar_id(
        self, 
        conversation: Dict[str, Any]
    ) -> Optional[str]:
        """
        Get calendar ID from cache or discover it
        
        Args:
            conversation: Conversation dict with calendar_account_id and calendar_id
            
        Returns:
            Calendar ID string, or None if not found
        """
        try:
            # Check if we have a cached calendar_id
            cached_calendar_id = conversation.get('calendar_id')
            if cached_calendar_id:
                logger.info(f"📅 Using cached calendar ID: {cached_calendar_id[:30]}...")
                return cached_calendar_id
            
            # No cache, need to discover the calendar
            calendar_account_id = conversation.get('calendar_account_id')
            if not calendar_account_id:
                logger.info("ℹ️  No calendar_account_id in conversation - skipping calendar operations")
                return None
            
            # Discover the default calendar
            calendar_id = await self.find_default_calendar(calendar_account_id)
            
            # Cache it in the database for future use
            if calendar_id:
                from app.db.postgres import db
                
                try:
                    db._get_client().table('conversations').update({
                        'calendar_id': calendar_id
                    }).eq('chat_id', str(conversation['chat_id'])).execute()
                    logger.info(f"💾 Cached calendar ID in database for future use")
                except Exception as e:
                    logger.error(f"Error caching calendar ID: {e}")
                    # Don't fail if caching fails - we still have the ID
            
            return calendar_id
            
        except Exception as e:
            logger.error(f"Error in get_or_cache_calendar_id: {e}", exc_info=True)
            return None
    
    def format_events_for_llm(self, events: List[Dict[str, Any]]) -> str:
        """
        Format calendar events into an LLM-friendly schedule
        
        Args:
            events: List of calendar events from Unipile API
            
        Returns:
            Formatted string for LLM context
        """
        if not events:
            return "No scheduled events found."
        
        # Filter out cancelled events and sort by start time
        active_events = [e for e in events if not e.get('is_cancelled', False)]
        
        if not active_events:
            return "No scheduled events found."
        
        # Sort by start time
        try:
            active_events.sort(key=lambda x: x.get('start', {}).get('date_time', ''))
        except Exception as e:
            logger.warning(f"Could not sort events: {e}")
        
        # Format each event
        formatted_lines = ["Your upcoming schedule:"]
        
        for event in active_events[:10]:  # Limit to next 10 events
            try:
                # Extract key info
                title = event.get('title', 'Untitled')
                start_dt = event.get('start', {}).get('date_time', 'Unknown time')
                end_dt = event.get('end', {}).get('date_time', '')
                location = event.get('location', '')
                is_all_day = event.get('is_all_day', False)
                
                # Parse and format datetime
                if start_dt != 'Unknown time':
                    try:
                        dt = datetime.fromisoformat(start_dt.replace('Z', '+00:00'))
                        day_name = dt.strftime('%A')  # Monday, Tuesday, etc.
                        date_str = dt.strftime('%B %d')  # October 22
                        time_str = dt.strftime('%I:%M %p')  # 02:00 PM
                        
                        if is_all_day:
                            formatted_lines.append(f"- {day_name}, {date_str}: {title} (All day)")
                        else:
                            # Calculate duration if end time available
                            duration = ""
                            if end_dt:
                                end = datetime.fromisoformat(end_dt.replace('Z', '+00:00'))
                                duration_mins = int((end - dt).total_seconds() / 60)
                                duration = f" ({duration_mins} min)"
                            
                            formatted_lines.append(f"- {day_name}, {date_str} at {time_str}{duration}: {title}")
                    except Exception as parse_error:
                        logger.warning(f"Could not parse datetime: {start_dt}, {parse_error}")
                        formatted_lines.append(f"- {start_dt}: {title}")
                else:
                    formatted_lines.append(f"- {title}")
                    
            except Exception as e:
                logger.warning(f"Could not format event: {e}")
                continue
        
        return "\n".join(formatted_lines)
    
    async def get_upcoming_schedule(
        self,
        calendar_account_id: str,
        calendar_id: Optional[str] = None,
        days_ahead: int = 7
    ) -> str:
        """
        Get LLM-friendly formatted schedule for the next N days
        
        Args:
            calendar_account_id: Outlook/Google account ID
            calendar_id: Optional calendar ID (will discover if not provided)
            days_ahead: Number of days to look ahead (default 7)
            
        Returns:
            Formatted schedule string for LLM
        """
        try:
            # Get calendar ID if not provided
            if not calendar_id:
                calendar_id = await self.find_default_calendar(calendar_account_id)
                if not calendar_id:
                    return "Could not access calendar."
            
            # Calculate date range
            now = datetime.now()
            start_date = now.isoformat()
            end_date = (now + timedelta(days=days_ahead)).isoformat()
            
            # Get events
            events_response = await self.unipile_client.get_calendar_events(
                calendar_id,
                start_date=start_date,
                end_date=end_date
            )
            
            events = events_response.get('data', [])
            
            # Format for LLM
            formatted_schedule = self.format_events_for_llm(events)
            
            logger.info(f"📅 Generated LLM-friendly schedule with {len(events)} events")
            return formatted_schedule
            
        except Exception as e:
            logger.error(f"Error getting upcoming schedule: {e}", exc_info=True)
            return "Could not retrieve calendar schedule."
    
    async def create_interview_event(
        self,
        conversation: Dict[str, Any],
        candidate_name: str,
        job_title: str,
        proposed_time: datetime,
        duration_minutes: int = 15,
        timezone: str = "UTC",
        candidate_email: Optional[str] = None,
        linkedin_url: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a calendar event for an interview
        
        Args:
            conversation: Conversation dict with calendar_account_id
            candidate_name: Name of the candidate
            job_title: Job position title
            proposed_time: Datetime object for meeting start
            duration_minutes: Duration in minutes (default 15)
            timezone: Timezone (default UTC)
            candidate_email: Optional candidate email for invite
            linkedin_url: Optional LinkedIn profile URL
            
        Returns:
            Created event data, or None if creation failed
        """
        try:
            # Get or discover calendar ID
            calendar_id = await self.get_or_cache_calendar_id(conversation)
            
            if not calendar_id:
                logger.warning("⚠️  No calendar available - cannot create event")
                return None
            
            # Build event details
            title = f"Interview: {candidate_name} - {job_title}"
            
            # Build description
            body_parts = [f"Candidate: {candidate_name}", f"Position: {job_title}"]
            if linkedin_url:
                body_parts.append(f"LinkedIn: {linkedin_url}")
            body_parts.append(f"Job ID: {conversation.get('job_id', 'N/A')}")
            body = "\n".join(body_parts)
            
            # Build attendees list if email provided
            attendees = None
            if candidate_email:
                attendees = [{
                    "email": candidate_email,
                    "display_name": candidate_name,
                    "type": "required",
                    "is_optional": False
                }]
            
            # Get calendar account ID
            calendar_account_id = conversation.get('calendar_account_id')
            if not calendar_account_id:
                logger.error("❌ No calendar_account_id in conversation")
                return None
            
            # Create the event
            event = await self.unipile_client.create_calendar_event(
                calendar_id=calendar_id,
                account_id=calendar_account_id,
                title=title,
                start_datetime=proposed_time.isoformat(),
                duration_minutes=duration_minutes,
                timezone=timezone,
                body=body,
                location="Video Call",  # Default to video call
                attendees=attendees
            )
            
            logger.info(f"✅ Interview event created: {candidate_name} at {proposed_time.strftime('%Y-%m-%d %H:%M')}")
            return event
            
        except Exception as e:
            logger.error(f"❌ Failed to create interview event: {e}", exc_info=True)
            return None
    
    async def check_availability(
        self,
        calendar_id: str,
        account_id: str,
        proposed_time: datetime,
        duration_minutes: int
    ) -> tuple[bool, Optional[str]]:
        """
        Check if proposed time slot is available (no conflicts)
        
        Args:
            calendar_id: Calendar ID to check
            account_id: Account ID to use for the calendar
            proposed_time: Proposed meeting start time
            duration_minutes: Duration of the meeting
            
        Returns:
            (is_available, conflict_message)
            - (True, None) if time slot is free
            - (False, "Conflict with: Team Meeting") if busy
        """
        try:
            # Calculate time window to check
            proposed_end = proposed_time + timedelta(minutes=duration_minutes)
            
            # Check events in a wider window (30 min before and after)
            start_check = proposed_time - timedelta(minutes=30)
            end_check = proposed_end + timedelta(minutes=30)
            
            logger.info(f"🔍 Checking availability from {proposed_time.isoformat()} for {duration_minutes} min")
            
            # Get events in this time window
            events_response = await self.unipile_client.get_calendar_events(
                calendar_id,
                account_id,
                start_date=start_check.isoformat(),
                end_date=end_check.isoformat()
            )
            
            events = events_response.get('data', [])
            logger.info(f"📅 Found {len(events)} events in time window")
            
            # Check for overlaps
            for event in events:
                # Skip cancelled events
                if event.get('is_cancelled', False):
                    continue
                
                # Skip all-day events (they don't block specific times)
                if event.get('is_all_day', False):
                    continue
                
                # Parse event times
                try:
                    event_start_str = event.get('start', {}).get('date_time')
                    event_end_str = event.get('end', {}).get('date_time')
                    
                    if not event_start_str or not event_end_str:
                        continue
                    
                    event_start = datetime.fromisoformat(event_start_str.replace('Z', '+00:00'))
                    event_end = datetime.fromisoformat(event_end_str.replace('Z', '+00:00'))
                    
                    # Check if times overlap
                    # Overlap condition: proposed_start < event_end AND proposed_end > event_start
                    if proposed_time < event_end and proposed_end > event_start:
                        event_title = event.get('title', 'Existing event')
                        conflict_msg = f"Conflict with: {event_title} ({event_start.strftime('%I:%M %p')} - {event_end.strftime('%I:%M %p')})"
                        logger.warning(f"⚠️  {conflict_msg}")
                        return False, conflict_msg
                        
                except Exception as parse_error:
                    logger.warning(f"Could not parse event times: {parse_error}")
                    continue
            
            # No conflicts found
            logger.info(f"✅ Time slot is available!")
            return True, None
            
        except Exception as e:
            logger.error(f"❌ Error checking availability: {e}", exc_info=True)
            # On error, assume available (don't block booking)
            return True, None


# Global instance
calendar_service = CalendarService()

