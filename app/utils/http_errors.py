"""Parse HTTP/API errors into structured form for storage and API responses."""
import json
import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


def _build_display(parsed: Dict[str, Any]) -> str:
    if parsed.get("title") and parsed.get("detail"):
        return f"{parsed['title']}: {parsed['detail']}"
    if parsed.get("detail"):
        return str(parsed["detail"])
    if parsed.get("title"):
        return str(parsed["title"])
    if parsed.get("type"):
        return str(parsed["type"])
    return str(parsed.get("display") or "Unknown error")


def parse_http_error(exc: BaseException) -> Dict[str, Any]:
    """
    Extract structured error info from httpx (or other) exceptions.
    Unipile returns JSON like: {"status":422,"type":"errors/cannot_resend_yet",...}
    """
    result: Dict[str, Any] = {
        "display": str(exc),
        "status": None,
        "type": None,
        "title": None,
        "detail": None,
        "source": None,
    }

    if isinstance(exc, httpx.HTTPStatusError):
        result["status"] = exc.response.status_code
        if exc.request is not None:
            result["source"] = str(exc.request.url)

        try:
            body = exc.response.json()
            if isinstance(body, dict):
                result["status"] = body.get("status") or result["status"]
                result["type"] = body.get("type")
                result["title"] = body.get("title")
                result["detail"] = body.get("detail") or body.get("message")
                result["display"] = _build_display(result)
                return result
        except Exception:
            logger.debug("Could not parse error response as JSON", exc_info=True)

        text = (exc.response.text or "")[:500]
        if text:
            result["detail"] = text
            result["display"] = f"HTTP {exc.response.status_code}: {text[:200]}"

    return result


def serialize_error(parsed: Dict[str, Any]) -> str:
    """JSON string for the messages.error_message column."""
    store = {
        k: parsed[k]
        for k in ("display", "status", "type", "title", "detail", "source")
        if parsed.get(k) is not None
    }
    return json.dumps(store)


def deserialize_stored_error(stored: Optional[str]) -> Optional[Dict[str, Any]]:
    """Parse DB value; supports legacy plain-text errors."""
    if not stored:
        return None
    try:
        data = json.loads(stored)
        if isinstance(data, dict):
            if not data.get("display"):
                data["display"] = _build_display(data)
            return data
    except json.JSONDecodeError:
        pass
    return {"display": stored, "legacy": True}


def enrich_message(msg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add human-readable error_message and structured error object for API clients.
    """
    out = dict(msg)
    parsed = deserialize_stored_error(msg.get("error_message"))

    if parsed:
        out["error_message"] = parsed.get("display") or msg.get("error_message")
        out["error"] = {
            k: parsed[k]
            for k in ("status", "type", "title", "detail", "source")
            if parsed.get(k) is not None
        } or None
    else:
        out["error_message"] = msg.get("error_message")
        out["error"] = None

    return out
