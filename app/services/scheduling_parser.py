"""Scheduling parser for extracting calendar booking metadata from AI responses"""
import json
import logging
import re
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Lines the model must never send to the candidate; stripped post-parse (defense in depth).
_STAGE_LINE = re.compile(r"^STAGE:\s*(.+)\s*$", re.IGNORECASE | re.MULTILINE)
# Internal key:value metadata (e.g. SHOWING_INTEREST: true). Require SCREAMING_SNAKE key or long KEY.
_INTERNAL_KV_LINE = re.compile(
    r"^(?:[A-Z][A-Z0-9_]*_[A-Z0-9_]+|[A-Z][A-Z0-9_]{7,}):\s*.*$"
)
# Standalone SCREAMING_SNAKE tokens (dynamic flags); avoid lines with spaces (e.g. job titles).
_INTERNAL_FLAG_TOKEN_LINE = re.compile(r"^[A-Z][A-Z0-9_]*_[A-Z0-9_]+$")
_FENCED_JSON = re.compile(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", re.IGNORECASE)


def _normalize_stage_label(raw: str) -> str:
    s = raw.strip().lower().replace(" ", "_")
    return s if s else "ongoing"


def strip_internal_metadata_from_message(text: str) -> str:
    """
    Remove STAGE lines, internal flags (SHOWING_INTEREST, KEY: value), and fenced JSON
    from text that will be sent to the candidate.
    """
    if not text:
        return text
    out = text
    for m in _FENCED_JSON.finditer(out):
        try:
            json.loads(m.group(1))
            out = out.replace(m.group(0), "")
        except json.JSONDecodeError:
            continue
    lines = []
    for line in out.splitlines():
        stripped = line.strip()
        if not stripped:
            lines.append(line)
            continue
        if _STAGE_LINE.fullmatch(stripped):
            continue
        if _INTERNAL_KV_LINE.match(stripped):
            continue
        if " " not in stripped and _INTERNAL_FLAG_TOKEN_LINE.match(stripped):
            continue
        lines.append(line)
    cleaned = "\n".join(lines).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned


def _plaintext_stage_and_body(raw: str) -> Tuple[str, Optional[str]]:
    """Split body text from an optional trailing STAGE: line; strip internal lines from body."""
    stage_val: Optional[str] = None
    lines = raw.splitlines()
    body_lines = []
    for line in lines:
        stripped = line.strip()
        sm = _STAGE_LINE.fullmatch(stripped) if stripped else None
        if sm:
            stage_val = _normalize_stage_label(sm.group(1))
            continue
        if stripped and _INTERNAL_KV_LINE.match(stripped):
            continue
        if stripped and " " not in stripped and _INTERNAL_FLAG_TOKEN_LINE.match(stripped):
            continue
        body_lines.append(line)
    body = "\n".join(body_lines).strip()
    body = strip_internal_metadata_from_message(body)
    return body, stage_val


def parse_ai_response(ai_response: str) -> Dict[str, Any]:
    """
    Parse AI response that may contain JSON with booking data
    
    Args:
        ai_response: Full AI response text (may be JSON or plain text)
        
    Returns:
        Dict with 'message', 'stage', and optionally 'booking_data'
    """
    try:
        # Try to parse as pure JSON first
        data = json.loads(ai_response.strip())
        
        # Validate JSON structure
        if not isinstance(data, dict):
            logger.warning("AI response is JSON but not a dict")
            return {
                "message": strip_internal_metadata_from_message(str(ai_response)),
                "stage": "ongoing",
                "booking_data": None,
            }
        
        # Extract components
        message = data.get("message", "")
        stage = data.get("stage", "ongoing")
        booking_data = data.get("booking_data")
        if message:
            message = strip_internal_metadata_from_message(str(message))
        
        logger.info(f"✅ Parsed JSON response - Stage: {stage}, Has booking: {booking_data is not None}")
        
        return {
            "message": message,
            "stage": stage,
            "booking_data": booking_data
        }
        
    except json.JSONDecodeError:
        # Try to extract JSON from mixed text/JSON response
        logger.info("AI response is not pure JSON, trying to extract JSON from mixed response")
        
        # Find JSON object pattern: { ... }
        json_match = re.search(r'\{.*"message".*\}', ai_response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            try:
                data = json.loads(json_str)
                message = data.get("message", "")
                stage = data.get("stage", "ongoing")
                booking_data = data.get("booking_data")
                if message:
                    message = strip_internal_metadata_from_message(str(message))
                
                logger.info(f"✅ Extracted JSON from mixed response - Stage: {stage}, Has booking: {booking_data is not None}")
                
                return {
                    "message": message,
                    "stage": stage,
                    "booking_data": booking_data
                }
            except json.JSONDecodeError:
                logger.warning("Failed to parse extracted JSON")
        
        # Fenced JSON blocks (booking) + plaintext message / STAGE
        text_remainder = ai_response
        booking_data_fence: Optional[Dict[str, Any]] = None
        fence_message: Optional[str] = None
        fence_stage: Optional[str] = None
        for m in list(_FENCED_JSON.finditer(ai_response)):
            try:
                blob = json.loads(m.group(1))
                if isinstance(blob, dict) and "message" in blob:
                    fence_message = strip_internal_metadata_from_message(str(blob.get("message", "")))
                    booking_data = blob.get("booking_data")
                    if booking_data is not None:
                        booking_data_fence = booking_data
                    st = blob.get("stage")
                    if st:
                        fence_stage = str(st).strip().lower().replace(" ", "_")
                    text_remainder = text_remainder.replace(m.group(0), "")
            except json.JSONDecodeError:
                continue

        body, stage_from_text = _plaintext_stage_and_body(text_remainder.strip())
        combined_msg = body or (fence_message or "")
        combined_stage = stage_from_text or fence_stage
        if combined_msg or stage_from_text is not None or fence_stage or booking_data_fence:
            logger.info("AI response parsed as plaintext + optional STAGE / booking fence")
            return {
                "message": combined_msg or strip_internal_metadata_from_message(ai_response.strip()),
                "stage": combined_stage or "ongoing",
                "booking_data": booking_data_fence,
            }

        # Fallback: strip any leaked directives from full raw text
        logger.info("AI response is not JSON, using stripped text fallback")
        cleaned = strip_internal_metadata_from_message(ai_response.strip())
        return {
            "message": cleaned if cleaned else ai_response.strip(),
            "stage": "ongoing", 
            "booking_data": booking_data_fence,
        }
    except Exception as e:
        logger.error(f"Error parsing AI response: {e}")
        return {
            "message": strip_internal_metadata_from_message(str(ai_response)),
            "stage": "ongoing",
            "booking_data": None
        }


def parse_scheduling_action(ai_response: str) -> Optional[Dict[str, Any]]:
    """
    Extract scheduling metadata from AI response (backward compatibility)
    
    Args:
        ai_response: Full AI response text
        
    Returns:
        Dict with booking data or None
    """
    parsed = parse_ai_response(ai_response)
    return parsed.get("booking_data")


def parse_proposed_time(
    time_str: str,
    timezone: str = "UTC"
) -> Optional[datetime]:
    """
    Parse ISO datetime string to datetime object
    
    Args:
        time_str: ISO datetime string (e.g., "2025-10-29T14:00:00Z")
        timezone: Timezone (default UTC)
        
    Returns:
        datetime object or None if parsing failed
    """
    try:
        # AI now provides ISO format directly, so simple conversion
        parsed_dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        logger.info(f"✅ Parsed ISO datetime '{time_str}' → {parsed_dt.isoformat()}")
        return parsed_dt
    except ValueError as e:
        logger.error(f"❌ Error parsing ISO datetime '{time_str}': {e}")
        return None


def validate_booking_data(booking_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate that booking data is complete and valid
    
    Args:
        booking_data: Parsed booking data from AI
        
    Returns:
        (is_valid, error_message)
    """
    if not booking_data:
        return False, "No booking data provided"
    
    # Check required fields
    required_fields = ['datetime', 'email', 'candidate_name']
    missing_fields = [field for field in required_fields if not booking_data.get(field)]
    
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"
    
    # Validate datetime format
    try:
        datetime.fromisoformat(booking_data['datetime'].replace('Z', '+00:00'))
    except ValueError:
        return False, f"Invalid datetime format: {booking_data['datetime']}"
    
    # Validate duration
    duration = booking_data.get('duration', 30)
    if not isinstance(duration, int) or duration < 15 or duration > 120:
        logger.warning(f"Unusual duration: {duration} min (recommended: 15-120)")
    
    # Validate email format (basic check)
    email = booking_data.get('email', '')
    if '@' not in email or '.' not in email.split('@')[-1]:
        logger.warning(f"Email format looks suspicious: {email}")
    
    return True, None


def extract_booking_metadata(ai_response: str) -> Optional[Dict[str, Any]]:
    """
    Extract and validate booking metadata from AI response
    
    Args:
        ai_response: Full AI response text
        
    Returns:
        Validated booking data or None
    """
    parsed = parse_ai_response(ai_response)
    booking_data = parsed.get("booking_data")
    
    if not booking_data:
        logger.info("No booking data in AI response")
        return None
    
    # Validate the booking data
    is_valid, error = validate_booking_data(booking_data)
    
    if not is_valid:
        logger.error(f"Invalid booking data: {error}")
        return None
    
    logger.info(f"✅ Valid booking data extracted: {booking_data}")
    return booking_data