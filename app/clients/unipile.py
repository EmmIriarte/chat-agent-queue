"""Unipile API client for sending LinkedIn messages and invites"""
import logging
from typing import Dict, Any, Optional
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class UnipileClient:
    """Client for Unipile API interactions"""
    
    def __init__(self):
        # Construct full URL from DNS address
        self.base_url = f"https://{settings.UNIPILE_API_DNS}/api/v1"
        self.api_key = settings.UNIPILE_API_KEY
        
    async def send_invitation(
        self,
        account_id: str,
        recipient_linkedin_id: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Send a LinkedIn connection invitation
        
        Args:
            account_id: Unipile account ID
            recipient_linkedin_id: LinkedIn provider ID of recipient
            message: Invitation message
            
        Returns:
            API response dict
        """
        try:
            url = f"{self.base_url}/users/invite"
            
            headers = {
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json"
            }
            
            payload = {
                "account_id": account_id,
                "provider_id": recipient_linkedin_id,
                "message": message
            }
            
            logger.info(f"Sending invitation via Unipile: {account_id} -> {recipient_linkedin_id}")
            logger.debug(f"Unipile URL: {url}")
            logger.debug(f"Unipile Payload: {payload}")
            logger.debug(f"API Key present: {bool(self.api_key)}")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=30.0)
                
                # Log response details for debugging
                logger.debug(f"Unipile response status: {response.status_code}")
                logger.debug(f"Unipile response body: {response.text[:500]}")
                
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Invitation sent successfully: {result}")
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Unipile API HTTP error: {e}")
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text}")
            logger.error(f"Request URL: {e.request.url}")
            logger.error(f"Request payload: {payload}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"Unipile API error sending invitation: {e}")
            raise
        except Exception as e:
            logger.error(f"Error sending invitation: {e}")
            raise
    
    async def send_message(
        self,
        account_id: str,
        recipient_linkedin_id: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Send a LinkedIn direct message (start new chat or send to existing)
        
        Args:
            account_id: Unipile account ID
            recipient_linkedin_id: LinkedIn provider ID of recipient
            message: Message content
            
        Returns:
            API response dict
        """
        try:
            url = f"{self.base_url}/chats"
            
            headers = {
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json"
            }
            
            payload = {
                "account_id": account_id,
                "attendees_ids": [recipient_linkedin_id],
                "text": message
            }
            
            logger.info(f"Sending message via Unipile: {account_id} -> {recipient_linkedin_id}")
            logger.debug(f"Unipile URL: {url}")
            logger.debug(f"Unipile Payload: {payload}")
            logger.debug(f"API Key present: {bool(self.api_key)}")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=30.0)
                
                # Log response details for debugging
                logger.debug(f"Unipile response status: {response.status_code}")
                logger.debug(f"Unipile response body: {response.text[:500]}")
                
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Message sent successfully: {result}")
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Unipile API HTTP error: {e}")
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text}")
            logger.error(f"Request URL: {e.request.url}")
            logger.error(f"Request payload: {payload}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"Unipile API error sending message: {e}")
            raise
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            raise
    
    async def get_calendars(self, account_id: str) -> Dict[str, Any]:
        """
        Get all calendars for a given account
        
        Args:
            account_id: The calendar_account_id (Outlook/Google Unipile ID)
            
        Returns:
            Dict with 'data' key containing list of calendars
        """
        try:
            url = f"{self.base_url}/calendars"
            params = {"account_id": account_id}
            
            headers = {
                "X-API-KEY": self.api_key,
                "accept": "application/json"
            }
            
            logger.info(f"📅 Getting calendars for account: {account_id}")
            logger.debug(f"Request URL: {url}?account_id={account_id}")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, headers=headers, timeout=10.0)
                response.raise_for_status()
                
                result = response.json()
                calendar_count = len(result.get('data', []))
                logger.info(f"✅ Retrieved {calendar_count} calendar(s)")
                
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Unipile Calendar API HTTP error: {e}")
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"❌ Error getting calendars: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting calendars: {e}")
            raise
    
    async def get_calendar_events(
        self,
        calendar_id: str,
        account_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get all events from a calendar
        
        Args:
            calendar_id: The calendar ID from get_calendars()
            account_id: ID of the account to use
            start_date: Optional ISO datetime to filter events from (e.g., "2025-10-22T00:00:00Z")
            end_date: Optional ISO datetime to filter events to (e.g., "2025-10-29T23:59:59Z")
            
        Returns:
            Dict with 'data' key containing list of events and 'next_cursor' for pagination
        """
        try:
            url = f"{self.base_url}/calendars/{calendar_id}/events"
            
            params = {'account_id': account_id}  # Required parameter
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
            
            headers = {
                "X-API-KEY": self.api_key,
                "accept": "application/json"
            }
            
            logger.info(f"📅 Getting events from calendar: {calendar_id[:30]}...")
            if start_date or end_date:
                logger.debug(f"Date range: {start_date} to {end_date}")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, headers=headers, timeout=10.0)
                response.raise_for_status()
                
                result = response.json()
                event_count = len(result.get('data', []))
                logger.info(f"✅ Retrieved {event_count} event(s)")
                
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Unipile Calendar Events API HTTP error: {e}")
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"❌ Error getting calendar events: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting calendar events: {e}")
            raise
    
    async def create_calendar_event(
        self,
        calendar_id: str,
        account_id: str,
        title: str,
        start_datetime: str,
        duration_minutes: int,
        timezone: str = "UTC",
        body: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Create a calendar event
        
        Args:
            calendar_id: Calendar ID from get_calendars()
            account_id: ID of the account to use
            title: Event title (e.g., "Interview: John Doe - Python Developer")
            start_datetime: ISO datetime string (e.g., "2025-10-24T14:00:00")
            duration_minutes: Duration in minutes (15, 30, 60)
            timezone: Timezone (e.g., "Europe/Madrid", "UTC")
            body: Optional event description
            location: Optional location (e.g., "Zoom", "Microsoft Teams")
            attendees: Optional list of attendees [{"email": "...", "display_name": "...", "type": "required"}]
            
        Returns:
            Created event data from Unipile API
        """
        try:
            # Calculate end time
            from datetime import datetime, timedelta
            start_dt = datetime.fromisoformat(start_datetime)
            end_dt = start_dt + timedelta(minutes=duration_minutes)
            
            # Build payload
            payload = {
                "title": title,
                "start": {
                    "date_time": start_dt.isoformat(),
                    "time_zone": timezone
                },
                "end": {
                    "date_time": end_dt.isoformat(),
                    "time_zone": timezone
                },
                "visibility": "public",
                "transparency": "opaque"
            }
            
            # Add optional fields
            if body:
                payload["body"] = body
            if location:
                payload["location"] = location
            if attendees:
                payload["attendees"] = attendees
            
            url = f"{self.base_url}/calendars/{calendar_id}/events?account_id={account_id}"
            headers = {
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json",
                "accept": "application/json"
            }
            
            logger.info(f"📅 Creating calendar event: {title}")
            logger.debug(f"Event time: {start_dt.isoformat()} ({duration_minutes} min)")
            logger.debug(f"Calendar ID: {calendar_id[:30]}...")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=10.0)
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"✅ Calendar event created successfully")
                logger.debug(f"Event response: {result}")
                
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Unipile Create Event API HTTP error: {e}")
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"❌ Error creating calendar event: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating calendar event: {e}", exc_info=True)
            raise


# Global Unipile client instance
unipile_client = UnipileClient()

