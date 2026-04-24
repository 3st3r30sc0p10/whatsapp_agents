import hashlib
import hmac

import httpx
import pytest

from app.core.whatsapp import KapsoClient, verify_kapso_signature


def test_verify_kapso_signature_valid():
    body = b'{"a":1}'
    secret = "mysecret"
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_kapso_signature(secret, body, sig) is True
    assert verify_kapso_signature(secret, body, f"sha256={sig}") is True


def test_verify_kapso_signature_invalid():
    body = b"x"
    assert verify_kapso_signature("s", body, "deadbeef") is False


@pytest.mark.asyncio
async def test_kapso_send_text_uses_correct_url(httpx_mock):
    httpx_mock.add_response(url=httpx.URL("https://api.kapso.ai/meta/whatsapp/v24.0/pid123/messages"), json={"ok": True})
    c = KapsoClient("k", "pid123", "wh")
    try:
        r = await c.send_text("573001234567", "hola")
        assert r.get("ok") is True
    finally:
        await c.aclose()


@pytest.mark.asyncio
async def test_kapso_typing_swallows_error(httpx_mock):
    httpx_mock.add_response(status_code=400)
    c = KapsoClient("k", "pid", "wh")
    try:
        r = await c.send_typing_indicator("573001234567")
        assert r == {}
    finally:
        await c.aclose()
