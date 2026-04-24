import os
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test")
os.environ.setdefault("KAPSO_API_KEY", "kap_test")
os.environ.setdefault("KAPSO_WEBHOOK_SECRET", "secret_secret_secret_secret_01")
os.environ.setdefault("MEM0_API_KEY", "m0-test")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "eyJ-test")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("LOG_LEVEL", "INFO")

import app.config as app_config

app_config.get_settings.cache_clear()

from app.main import app  # noqa: E402
from app.models.business import Business  # noqa: E402


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Any:
    app_config.get_settings.cache_clear()
    yield
    app_config.get_settings.cache_clear()


@pytest.fixture
def test_business() -> Business:
    return Business(
        id="b1111111-1111-4111-8111-111111111111",
        name="Test Biz",
        slug="test-biz",
        phone_number_id="647015955153740",
        business_context="Negocio de prueba en Colombia.",
        agent_id="agent_test_1",
        environment_id="env_test_1",
        webhook_registered=True,
        is_active=True,
        plan="basico",
        monthly_message_limit=500,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_kapso_client(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    from unittest.mock import MagicMock

    m = MagicMock()
    m.verify_signature = MagicMock(return_value=True)
    m.send_text = AsyncMock(return_value={"ok": True})
    m.send_typing_indicator = AsyncMock(return_value={})
    m.aclose = AsyncMock()
    monkeypatch.setattr("app.api.webhook.verify_kapso_signature", lambda secret, body, sig: True)
    return m


@pytest.fixture
async def test_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
