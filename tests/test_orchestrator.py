from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.config import Settings
from app.core.agent import AgentService
from app.core.memory import MemoryService
from app.core.orchestrator import MessageOrchestrator
from app.models.business import Business
from app.models.session import AgentSession, UsageCounter


def _settings() -> Settings:
    return Settings(
        anthropic_api_key="x",
        kapso_api_key="k",
        kapso_webhook_secret="s",
        mem0_api_key="m",
        supabase_url="https://x.supabase.co",
        supabase_key="key",
    )


@pytest.mark.asyncio
async def test_orchestrator_happy_path(monkeypatch: pytest.MonkeyPatch, test_business: Business):
    settings = _settings()
    memory = MagicMock()
    memory.search = MagicMock(return_value=["prefiere té"])
    memory.add = MagicMock()

    agent = MagicMock(spec=AgentService)
    agent.get_or_create_session = AsyncMock(return_value="sess1")
    agent.send_message = AsyncMock(return_value="¡Hola! ¿En qué te ayudo?")

    class FakeWA:
        def __init__(self, *a, **kw) -> None:
            self.send_text = AsyncMock(return_value={})
            self.send_typing_indicator = AsyncMock(return_value={})
            self.aclose = AsyncMock()

    monkeypatch.setattr("app.core.orchestrator.KapsoClient", FakeWA)

    db = MagicMock()
    db.inbound_whatsapp_message_exists = AsyncMock(return_value=False)
    db.get_business_by_id = AsyncMock(return_value=test_business)
    db.log_message = AsyncMock()
    db.get_or_create_usage_counter = AsyncMock(
        return_value=UsageCounter(id="1", business_id=test_business.id, month_year="2026-04", message_count=0)
    )
    db.get_session = AsyncMock(return_value=None)
    db.upsert_session = AsyncMock()
    db.increment_session_message_count = AsyncMock()
    db.increment_usage_counter = AsyncMock(return_value=1)

    orch = MessageOrchestrator(settings, memory, agent, db)
    await orch.handle_incoming_message(test_business.id, "573001234567", "hola", "wamid-1")
    agent.send_message.assert_awaited()
    memory.add.assert_called_once()
    db.increment_usage_counter.assert_awaited()


@pytest.mark.asyncio
async def test_orchestrator_mem0_failure_continues(monkeypatch: pytest.MonkeyPatch, test_business: Business):
    settings = _settings()
    mock_client = MagicMock()
    mock_client.search.side_effect = RuntimeError("down")
    monkeypatch.setattr(MemoryService, "_mem", lambda self: mock_client)
    memory = MemoryService(api_key="x")

    agent = MagicMock(spec=AgentService)
    agent.get_or_create_session = AsyncMock(return_value="sess1")
    agent.send_message = AsyncMock(return_value="ok")

    class FakeWA:
        def __init__(self, *a, **kw) -> None:
            self.send_text = AsyncMock(return_value={})
            self.send_typing_indicator = AsyncMock(return_value={})
            self.aclose = AsyncMock()

    monkeypatch.setattr("app.core.orchestrator.KapsoClient", FakeWA)

    db = MagicMock()
    db.inbound_whatsapp_message_exists = AsyncMock(return_value=False)
    db.get_business_by_id = AsyncMock(return_value=test_business)
    db.log_message = AsyncMock()
    db.get_or_create_usage_counter = AsyncMock(
        return_value=UsageCounter(id="1", business_id=test_business.id, month_year="2026-04", message_count=0)
    )
    db.get_session = AsyncMock(return_value=None)
    db.upsert_session = AsyncMock()
    db.increment_session_message_count = AsyncMock()
    db.increment_usage_counter = AsyncMock(return_value=1)

    orch = MessageOrchestrator(settings, memory, agent, db)
    await orch.handle_incoming_message(test_business.id, "573001234567", "hola", "wamid-2")
    agent.send_message.assert_awaited()


@pytest.mark.asyncio
async def test_orchestrator_usage_limit(monkeypatch: pytest.MonkeyPatch, test_business: Business):
    settings = _settings()
    b = test_business.model_copy(update={"monthly_message_limit": 10})
    memory = MagicMock(spec=MemoryService)
    agent = MagicMock(spec=AgentService)

    class FakeWA:
        def __init__(self, *a, **kw) -> None:
            self.send_text = AsyncMock(return_value={})
            self.send_typing_indicator = AsyncMock(return_value={})
            self.aclose = AsyncMock()

    monkeypatch.setattr("app.core.orchestrator.KapsoClient", FakeWA)

    db = MagicMock()
    db.inbound_whatsapp_message_exists = AsyncMock(return_value=False)
    db.get_business_by_id = AsyncMock(return_value=b)
    db.log_message = AsyncMock()
    db.get_or_create_usage_counter = AsyncMock(
        return_value=UsageCounter(id="1", business_id=b.id, month_year="2026-04", message_count=10)
    )

    orch = MessageOrchestrator(settings, memory, agent, db)
    await orch.handle_incoming_message(b.id, "573001234567", "hola", "wamid-3")
    agent.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_orchestrator_claude_fallback(monkeypatch: pytest.MonkeyPatch, test_business: Business):
    settings = _settings()
    memory = MagicMock()
    memory.search = MagicMock(return_value=[])
    memory.add = MagicMock()

    agent = MagicMock(spec=AgentService)
    agent.get_or_create_session = AsyncMock(return_value="sess1")
    agent.send_message = AsyncMock(side_effect=[RuntimeError("fail"), RuntimeError("fail2")])

    class FakeWA:
        def __init__(self, *a, **kw) -> None:
            self.send_text = AsyncMock(return_value={})
            self.send_typing_indicator = AsyncMock(return_value={})
            self.aclose = AsyncMock()

    monkeypatch.setattr("app.core.orchestrator.KapsoClient", FakeWA)

    db = MagicMock()
    db.inbound_whatsapp_message_exists = AsyncMock(return_value=False)
    db.get_business_by_id = AsyncMock(return_value=test_business)
    db.log_message = AsyncMock()
    db.get_or_create_usage_counter = AsyncMock(
        return_value=UsageCounter(id="1", business_id=test_business.id, month_year="2026-04", message_count=0)
    )
    db.get_session = AsyncMock(return_value=None)
    db.upsert_session = AsyncMock()
    db.increment_session_message_count = AsyncMock()
    db.increment_usage_counter = AsyncMock(return_value=1)

    orch = MessageOrchestrator(settings, memory, agent, db)
    await orch.handle_incoming_message(test_business.id, "573001234567", "hola", "wamid-4")
    assert agent.send_message.await_count == 2
