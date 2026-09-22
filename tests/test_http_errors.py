"""Tests for API error parsing."""
import json

import httpx
import pytest

from app.utils.http_errors import (
    deserialize_stored_error,
    enrich_message,
    parse_http_error,
    serialize_error,
)


def test_parse_unipile_422():
    request = httpx.Request("POST", "https://api.example.com/users/invite")
    response = httpx.Response(
        422,
        json={
            "status": 422,
            "type": "errors/cannot_resend_yet",
            "title": "Cannot resend yet",
            "detail": "You have reached a temporary provider limit. Please try again later.",
        },
        request=request,
    )
    exc = httpx.HTTPStatusError("422", request=request, response=response)
    parsed = parse_http_error(exc)

    assert parsed["type"] == "errors/cannot_resend_yet"
    assert parsed["title"] == "Cannot resend yet"
    assert "provider limit" in parsed["detail"]
    assert "Cannot resend yet" in parsed["display"]


def test_roundtrip_storage_and_enrich():
    parsed = {
        "display": "Cannot resend yet: limit reached",
        "status": 422,
        "type": "errors/cannot_resend_yet",
        "title": "Cannot resend yet",
        "detail": "limit reached",
    }
    stored = serialize_error(parsed)
    msg = enrich_message({"message_id": "1", "error_message": stored, "status": "error"})

    assert msg["error_message"] == parsed["display"]
    assert msg["error"]["type"] == "errors/cannot_resend_yet"
    assert msg["error"]["status"] == 422


def test_legacy_plain_text_error():
    msg = enrich_message({"error_message": "Client error '422 Unprocessable Entity'"})
    assert msg["error"] is None
    assert "422" in msg["error_message"]
