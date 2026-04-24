import hashlib
import hmac
import logging
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

KAPSO_MESSAGES_URL = "https://api.kapso.ai/meta/whatsapp/v24.0/{phone_number_id}/messages"


def verify_kapso_signature(webhook_secret: str, payload_bytes: bytes, signature: str) -> bool:
    if not signature or not webhook_secret:
        return False
    sig = signature.strip()
    if sig.lower().startswith("sha256="):
        sig = sig.split("=", 1)[1]
    expected = hmac.new(
        webhook_secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    try:
        return hmac.compare_digest(expected.lower(), sig.lower())
    except Exception:
        return False


class KapsoClient:
    def __init__(self, api_key: str, phone_number_id: str, webhook_secret: str) -> None:
        self._api_key = api_key
        self._phone_number_id = phone_number_id
        self._webhook_secret = webhook_secret
        self._http = httpx.AsyncClient(timeout=60.0)

    async def aclose(self) -> None:
        await self._http.aclose()

    def verify_signature(self, payload_bytes: bytes, signature: str) -> bool:
        return verify_kapso_signature(self._webhook_secret, payload_bytes, signature)

    def _headers(self) -> dict[str, str]:
        return {
            "X-API-Key": self._api_key,
            "Content-Type": "application/json",
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def _post_json(self, url: str, body: dict[str, Any]) -> dict[str, Any]:
        r = await self._http.post(url, headers=self._headers(), json=body)
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, dict) else {}

    async def send_text(self, to: str, text: str) -> dict[str, Any]:
        url = KAPSO_MESSAGES_URL.format(phone_number_id=self._phone_number_id)
        body: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
        return await self._post_json(url, body)

    async def send_typing_indicator(self, to: str) -> dict[str, Any]:
        url = KAPSO_MESSAGES_URL.format(phone_number_id=self._phone_number_id)
        body: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "typing",
            "typing": {"type": "text"},
        }
        try:
            return await self._post_json(url, body)
        except Exception as exc:
            logger.debug("typing indicator failed: %s", exc)
            return {}
