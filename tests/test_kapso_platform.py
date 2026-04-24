import httpx
import pytest

from app.core.kapso_platform import register_kapso_webhook


def test_register_kapso_webhook(httpx_mock):
    httpx_mock.add_response(
        url="https://api.kapso.ai/platform/v1/whatsapp/phone_numbers/abc/webhooks",
        json={"data": {"id": "w1"}},
    )
    out = register_kapso_webhook("key", "abc", "https://x/webhook/whatsapp", "sec")
    assert out["data"]["id"] == "w1"
