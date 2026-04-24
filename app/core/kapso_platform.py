"""Kapso Platform API (webhook registration), separate from Meta message sending."""

from __future__ import annotations

from typing import Any

import httpx


def register_kapso_webhook(
    api_key: str,
    phone_number_id: str,
    webhook_url: str,
    secret_key: str,
) -> dict[str, Any]:
    url = f"https://api.kapso.ai/platform/v1/whatsapp/phone_numbers/{phone_number_id}/webhooks"
    body = {
        "whatsapp_webhook": {
            "url": webhook_url,
            "secret_key": secret_key,
            "events": ["whatsapp.message.received"],
            "active": True,
        }
    }
    r = httpx.post(
        url,
        headers={"X-API-Key": api_key, "Content-Type": "application/json"},
        json=body,
        timeout=60.0,
    )
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, dict) else {}
