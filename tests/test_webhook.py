import hashlib
import hmac
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

import app.config as app_config
from app.dependencies import get_orchestrator
from app.main import app
from app.models.business import Business


def _sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


@pytest.mark.asyncio
async def test_webhook_invalid_signature(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.api.webhook.verify_kapso_signature", lambda s, b, sig: False)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/webhook/whatsapp", content=b"{}", headers={"x-webhook-signature": "bad"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_webhook_non_text_ignored(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.api.webhook.verify_kapso_signature", lambda s, b, sig: True)
    monkeypatch.setattr(
        "app.api.webhook.get_business_by_phone_number_id", AsyncMock(return_value=None)
    )
    payload = {
        "event": "whatsapp.message.received",
        "phone_number_id": "1",
        "message": {
            "id": "m1",
            "from": "573001234567",
            "type": "image",
            "timestamp": "1",
        },
    }
    body = json.dumps(payload).encode()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/webhook/whatsapp",
            content=body,
            headers={"x-webhook-signature": _sign(body, app_config.get_settings().kapso_webhook_secret)},
        )
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "ignored"


@pytest.mark.asyncio
async def test_webhook_unknown_phone_logs_ok(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.api.webhook.verify_kapso_signature", lambda s, b, sig: True)
    monkeypatch.setattr(
        "app.api.webhook.get_business_by_phone_number_id", AsyncMock(return_value=None)
    )
    payload = {
        "event": "whatsapp.message.received",
        "phone_number_id": "unknown",
        "message": {
            "id": "m1",
            "from": "573001234567",
            "type": "text",
            "text": {"body": "hola"},
            "timestamp": "1",
        },
    }
    body = json.dumps(payload).encode()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/webhook/whatsapp",
            content=body,
            headers={"x-webhook-signature": _sign(body, app_config.get_settings().kapso_webhook_secret)},
        )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_webhook_valid_text_schedules_orchestrator(monkeypatch: pytest.MonkeyPatch, test_business: Business):
    monkeypatch.setattr("app.api.webhook.verify_kapso_signature", lambda s, b, sig: True)
    monkeypatch.setattr(
        "app.api.webhook.get_business_by_phone_number_id", AsyncMock(return_value=test_business)
    )
    orch = MagicMock()
    orch.handle_incoming_message = AsyncMock()
    app.dependency_overrides[get_orchestrator] = lambda: orch
    payload = {
        "event": "whatsapp.message.received",
        "phone_number_id": test_business.phone_number_id,
        "message": {
            "id": "wamid.xxx",
            "from": "573001234567",
            "type": "text",
            "text": {"body": "hola"},
            "timestamp": "1",
        },
    }
    body = json.dumps(payload).encode()
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post(
                "/webhook/whatsapp",
                content=body,
                headers={
                    "x-webhook-signature": _sign(
                        body, app_config.get_settings().kapso_webhook_secret
                    )
                },
            )
        assert r.status_code == 200
        assert orch.handle_incoming_message.await_count == 1
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_webhook_verify_challenge():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get(
            "/webhook/whatsapp",
            params={"hub.mode": "subscribe", "hub.challenge": "abc123", "hub.verify_token": "x"},
        )
    assert r.status_code == 200
    assert r.text == "abc123"
