"""DB query helpers with mocked Supabase client."""

from unittest.mock import AsyncMock, MagicMock

import pytest

import app.db.queries as q


@pytest.mark.asyncio
async def test_get_business_by_phone(monkeypatch: pytest.MonkeyPatch):
    row = {
        "id": "b1",
        "name": "N",
        "slug": "s",
        "phone_number_id": "p1",
        "business_context": "c",
        "agent_id": "a",
        "environment_id": "e",
        "webhook_registered": True,
        "is_active": True,
        "plan": "basico",
        "monthly_message_limit": 100,
    }
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[row]
    )
    monkeypatch.setattr(q, "_sb", lambda: sb)
    b = await q.get_business_by_phone_number_id("p1")
    assert b is not None and b.slug == "s"


@pytest.mark.asyncio
async def test_get_business_by_id_none(monkeypatch: pytest.MonkeyPatch):
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
    monkeypatch.setattr(q, "_sb", lambda: sb)
    assert await q.get_business_by_id("x") is None


@pytest.mark.asyncio
async def test_update_business_agent_ids(monkeypatch: pytest.MonkeyPatch):
    sb = MagicMock()
    sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
    monkeypatch.setattr(q, "_sb", lambda: sb)
    await q.update_business_agent_ids("b1", "ag", "env")


@pytest.mark.asyncio
async def test_list_businesses_active_only(monkeypatch: pytest.MonkeyPatch):
    row = {
        "id": "b1",
        "name": "N",
        "slug": "s",
        "phone_number_id": "p",
        "business_context": "c",
        "plan": "pro",
        "monthly_message_limit": -1,
    }
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
        data=[row]
    )
    monkeypatch.setattr(q, "_sb", lambda: sb)
    lst = await q.list_businesses(include_inactive=False)
    assert len(lst) == 1


@pytest.mark.asyncio
async def test_list_businesses_all(monkeypatch: pytest.MonkeyPatch):
    row = {
        "id": "b1",
        "name": "N",
        "slug": "s",
        "phone_number_id": "p",
        "business_context": "c",
        "plan": "basico",
        "monthly_message_limit": 500,
    }
    sb = MagicMock()
    sb.table.return_value.select.return_value.order.return_value.execute.return_value = MagicMock(data=[row])
    monkeypatch.setattr(q, "_sb", lambda: sb)
    lst = await q.list_businesses(include_inactive=True)
    assert len(lst) == 1


@pytest.mark.asyncio
async def test_create_business(monkeypatch: pytest.MonkeyPatch):
    from app.models.business import BusinessCreate

    row = {
        "id": "b1",
        "name": "N",
        "slug": "s",
        "phone_number_id": "p",
        "business_context": "c",
        "plan": "basico",
        "monthly_message_limit": 500,
    }
    sb = MagicMock()
    sb.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[row])
    monkeypatch.setattr(q, "_sb", lambda: sb)
    b = await q.create_business(
        BusinessCreate(name="N", slug="s", phone_number_id="p", business_context="c")
    )
    assert b.id == "b1"


@pytest.mark.asyncio
async def test_get_session_none(monkeypatch: pytest.MonkeyPatch):
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[]
    )
    monkeypatch.setattr(q, "_sb", lambda: sb)
    assert await q.get_session("573", "b1") is None


@pytest.mark.asyncio
async def test_upsert_session(monkeypatch: pytest.MonkeyPatch):
    sb = MagicMock()
    sb.table.return_value.upsert.return_value.execute.return_value = MagicMock()
    monkeypatch.setattr(q, "_sb", lambda: sb)
    await q.upsert_session("573", "b1", "sess1")


@pytest.mark.asyncio
async def test_increment_session_message_count(monkeypatch: pytest.MonkeyPatch):
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"message_count": 2}]
    )
    sb.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
    monkeypatch.setattr(q, "_sb", lambda: sb)
    await q.increment_session_message_count("573", "b1")


@pytest.mark.asyncio
async def test_increment_session_no_row(monkeypatch: pytest.MonkeyPatch):
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[]
    )
    monkeypatch.setattr(q, "_sb", lambda: sb)
    await q.increment_session_message_count("573", "b1")


@pytest.mark.asyncio
async def test_increment_usage_counter(monkeypatch: pytest.MonkeyPatch):
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"id": "u1", "message_count": 5}]
    )
    sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
    monkeypatch.setattr(q, "_sb", lambda: sb)
    n = await q.increment_usage_counter("b1", "2026-04")
    assert n == 6


@pytest.mark.asyncio
async def test_increment_usage_counter_new(monkeypatch: pytest.MonkeyPatch):
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[]
    )
    sb.table.return_value.insert.return_value.execute.return_value = MagicMock()
    monkeypatch.setattr(q, "_sb", lambda: sb)
    n = await q.increment_usage_counter("b1", "2026-05")
    assert n == 1


@pytest.mark.asyncio
async def test_log_message(monkeypatch: pytest.MonkeyPatch):
    sb = MagicMock()
    sb.table.return_value.insert.return_value.execute.return_value = MagicMock()
    monkeypatch.setattr(q, "_sb", lambda: sb)
    await q.log_message("b1", "573", "inbound", "hi", "w1")


@pytest.mark.asyncio
async def test_inbound_exists(monkeypatch: pytest.MonkeyPatch):
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"id": "x"}]
    )
    monkeypatch.setattr(q, "_sb", lambda: sb)
    assert await q.inbound_whatsapp_message_exists("w1") is True


@pytest.mark.asyncio
async def test_inbound_exists_empty_id(monkeypatch: pytest.MonkeyPatch):
    assert await q.inbound_whatsapp_message_exists("") is False


@pytest.mark.asyncio
async def test_get_or_create_usage_insert(monkeypatch: pytest.MonkeyPatch):
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[]
    )
    sb.table.return_value.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": "1", "business_id": "b1", "month_year": "2026-04", "message_count": 0}]
    )
    monkeypatch.setattr(q, "_sb", lambda: sb)
    u = await q.get_or_create_usage_counter("b1", "2026-04")
    assert u.month_year == "2026-04"


@pytest.mark.asyncio
async def test_get_or_create_usage_existing(monkeypatch: pytest.MonkeyPatch):
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"id": "1", "business_id": "b1", "month_year": "2026-04", "message_count": 3}]
    )
    monkeypatch.setattr(q, "_sb", lambda: sb)
    u = await q.get_or_create_usage_counter("b1", "2026-04")
    assert u.message_count == 3


@pytest.mark.asyncio
async def test_delete_session(monkeypatch: pytest.MonkeyPatch):
    sb = MagicMock()
    sb.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
    monkeypatch.setattr(q, "_sb", lambda: sb)
    await q.delete_session("573", "b1")


@pytest.mark.asyncio
async def test_get_message_logs(monkeypatch: pytest.MonkeyPatch):
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[
            {
                "id": "l1",
                "business_id": "b1",
                "client_phone": "573",
                "direction": "outbound",
                "content": "x",
                "whatsapp_message_id": None,
            }
        ]
    )
    monkeypatch.setattr(q, "_sb", lambda: sb)
    logs = await q.get_message_logs("b1", 10)
    assert len(logs) == 1


@pytest.mark.asyncio
async def test_list_sessions(monkeypatch: pytest.MonkeyPatch):
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
        data=[
            {
                "id": "s1",
                "client_phone": "573",
                "business_id": "b1",
                "session_id": "claude_sess",
                "message_count": 1,
            }
        ]
    )
    monkeypatch.setattr(q, "_sb", lambda: sb)
    ss = await q.list_sessions("b1")
    assert len(ss) == 1


@pytest.mark.asyncio
async def test_update_business_patch(monkeypatch: pytest.MonkeyPatch):
    from app.models.business import BusinessUpdate

    row = {
        "id": "b1",
        "name": "N2",
        "slug": "s",
        "phone_number_id": "p",
        "business_context": "new",
        "plan": "basico",
        "monthly_message_limit": 500,
    }
    sb = MagicMock()
    sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[row])
    monkeypatch.setattr(q, "_sb", lambda: sb)
    b = await q.update_business("b1", BusinessUpdate(name="N2"))
    assert b.name == "N2"


@pytest.mark.asyncio
async def test_update_business_empty_patch(monkeypatch: pytest.MonkeyPatch):
    from app.models.business import BusinessUpdate

    row = {
        "id": "b1",
        "name": "N",
        "slug": "s",
        "phone_number_id": "p",
        "business_context": "c",
        "plan": "basico",
        "monthly_message_limit": 500,
    }
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[row]
    )
    monkeypatch.setattr(q, "_sb", lambda: sb)
    b = await q.update_business("b1", BusinessUpdate())
    assert b.slug == "s"


@pytest.mark.asyncio
async def test_deactivate_business(monkeypatch: pytest.MonkeyPatch):
    m = AsyncMock()
    monkeypatch.setattr(q, "update_business", m)
    await q.deactivate_business("b1")
    m.assert_awaited_once()


@pytest.mark.asyncio
async def test_database_service_delegates(monkeypatch: pytest.MonkeyPatch):
    from app.db.queries import DatabaseService
    from app.models.session import AgentSession

    async def fake_get(bid: str):
        return None

    async def fake_sessions(bid: str):
        return [AgentSession(id="1", client_phone="573", business_id="b1", session_id="s")]

    monkeypatch.setattr(q, "get_business_by_id", fake_get)
    monkeypatch.setattr(q, "list_sessions", fake_sessions)
    svc = DatabaseService()
    assert await svc.get_business_by_id("x") is None
    assert len(await svc.list_sessions("b1")) == 1
