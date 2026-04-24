from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from anthropic import NotFoundError

from app.config import Settings
from app.core.agent import AgentService, SYSTEM_PROMPT_TEMPLATE


def _settings(**kwargs: object) -> Settings:
    base = dict(
        anthropic_api_key="x",
        kapso_api_key="k",
        kapso_webhook_secret="s",
        mem0_api_key="m",
        supabase_url="https://x.supabase.co",
        supabase_key="key",
    )
    base.update(kwargs)
    return Settings(**base)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_create_agent_calls_beta_apis(monkeypatch: pytest.MonkeyPatch):
    settings = _settings(agent_model="claude-sonnet-4-6")
    client = MagicMock()
    client.beta.agents.create = AsyncMock(return_value=MagicMock(id="ag_1"))
    client.beta.environments.create = AsyncMock(return_value=MagicMock(id="env_1"))
    svc = AgentService(client, settings)
    aid, eid = await svc.create_agent_and_environment("Biz", "ctx")
    assert aid == "ag_1"
    assert eid == "env_1"
    client.beta.agents.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_or_create_session_reuses_valid(monkeypatch: pytest.MonkeyPatch):
    settings = _settings()
    client = MagicMock()
    client.beta.sessions.retrieve = AsyncMock(return_value=MagicMock(id="sess_old"))
    client.beta.sessions.create = AsyncMock(return_value=MagicMock(id="sess_new"))
    svc = AgentService(client, settings)
    sid = await svc.get_or_create_session("573", "ag", "env", "sess_old")
    assert sid == "sess_old"
    client.beta.sessions.create.assert_not_called()


@pytest.mark.asyncio
async def test_get_or_create_session_new_on_404(monkeypatch: pytest.MonkeyPatch):
    settings = _settings()
    client = MagicMock()

    async def boom(_sid: str):
        req = httpx.Request("GET", "https://api.anthropic.com")
        resp = httpx.Response(404, request=req)
        raise NotFoundError("nope", response=resp, body={})

    client.beta.sessions.retrieve = boom
    client.beta.sessions.create = AsyncMock(return_value=MagicMock(id="sess_new"))
    svc = AgentService(client, settings)
    sid = await svc.get_or_create_session("573", "ag", "env", "bad")
    assert sid == "sess_new"


@pytest.mark.asyncio
async def test_send_message_collects_text(monkeypatch: pytest.MonkeyPatch):
    settings = _settings()
    client = MagicMock()

    class FakeBlock:
        type = "text"
        text = "Hola "

    class FakeBlock2:
        type = "text"
        text = "mundo"

    class Ev:
        type = "agent.message"
        content = [FakeBlock(), FakeBlock2()]

    class FakeStream:
        def __init__(self) -> None:
            self._events = [Ev()]

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return None

        def __aiter__(self):
            self._i = 0
            return self

        async def __anext__(self):
            if self._i >= len(self._events):
                raise StopAsyncIteration
            e = self._events[self._i]
            self._i += 1
            return e

    events_m = MagicMock()
    events_m.send = AsyncMock()
    events_m.stream = AsyncMock(return_value=FakeStream())
    sessions_m = MagicMock()
    sessions_m.events = events_m
    client.beta.sessions = sessions_m
    svc = AgentService(client, settings)
    out = await svc.send_message("sess", "ping")
    assert out == "Hola mundo"


def test_system_prompt_template_has_placeholders():
    s = SYSTEM_PROMPT_TEMPLATE.format(business_name="X", business_context="Y")
    assert "X" in s and "Y" in s
