"""Provider-neutral adapters for citizen messaging webhooks.

The adapter deliberately returns only the fields needed by the Maker pipeline.
Sender identifiers are hashed at the edge and raw provider payloads are never
logged or forwarded to Gemini.
"""
import hashlib
import json
from typing import Any, Dict


def _first(*values: Any) -> Any:
    return next((value for value in values if value not in (None, "")), "")


def _hash_sender(value: Any) -> str:
    token = str(value or "anonymous").strip().encode("utf-8")
    return hashlib.sha256(token).hexdigest()[:24]


def _whatsapp_cloud(payload: Dict[str, Any]) -> Dict[str, Any]:
    value = payload.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {})
    message = (value.get("messages") or [{}])[0]
    contact = (value.get("contacts") or [{}])[0]
    location = message.get("location") or {}
    return {
        "text": ((message.get("text") or {}).get("body") or message.get("caption") or "").strip(),
        "sender": _first(message.get("from"), contact.get("wa_id")),
        "location_hint": _first(
            location.get("name"),
            f"{location.get('latitude')},{location.get('longitude')}" if location else "",
        ),
        "provider_message_id": message.get("id", ""),
    }


def _twilio(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "text": _first(payload.get("Body"), payload.get("body"), payload.get("text")).strip(),
        "sender": _first(payload.get("From"), payload.get("from"), payload.get("sender")),
        "location_hint": _first(payload.get("Location"), payload.get("location"), payload.get("location_hint")),
        "provider_message_id": _first(payload.get("MessageSid"), payload.get("message_id")),
    }


def normalize_webhook(provider: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize WhatsApp Cloud, Twilio-style, and generic webhook payloads."""
    provider_key = provider.lower().replace("-", "_")
    if provider_key in {"whatsapp", "whatsapp_cloud", "meta"}:
        result = _whatsapp_cloud(payload)
        channel = "whatsapp_bot"
    elif provider_key in {"twilio", "twilio_sms", "sms"}:
        result = _twilio(payload)
        channel = "sms"
    else:
        result = {
            "text": _first(payload.get("raw_text"), payload.get("text"), payload.get("message"), payload.get("body")).strip(),
            "sender": _first(payload.get("sender"), payload.get("from"), payload.get("phone")),
            "location_hint": _first(payload.get("location_hint"), payload.get("location")),
            "provider_message_id": _first(payload.get("message_id"), payload.get("id")),
        }
        channel = "whatsapp_bot" if provider_key == "whatsapp_bot" else "sms"

    if not result["text"]:
        raise ValueError("Webhook payload does not contain a text message")
    if len(result["text"]) > 8_000:
        raise ValueError("Webhook message exceeds 8000 characters")
    result.update({
        "provider": provider_key,
        "channel": channel,
        "sender_token": f"sha256:{_hash_sender(result.pop('sender', 'anonymous'))}",
        "demand_volume": 1,
    })
    return result


def parse_payload(raw_body: bytes, content_type: str = "") -> Dict[str, Any]:
    """Decode JSON or form-encoded webhook bodies without retaining raw input."""
    if "application/json" in (content_type or "").lower() or raw_body.lstrip().startswith(b"{"):
        payload = json.loads(raw_body.decode("utf-8"))
    else:
        from urllib.parse import parse_qs
        payload = {key: values[-1] for key, values in parse_qs(raw_body.decode("utf-8")).items()}
    if not isinstance(payload, dict):
        raise ValueError("Webhook payload must be an object")
    return payload
