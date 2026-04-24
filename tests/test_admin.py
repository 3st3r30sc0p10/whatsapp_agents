from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

import app.config as app_config
from app.main import app
from app.models.business import Business
from app.models.session import MessageLog


@pytest.mark.asyncio
async def test_admin_auth_optional_when_key_unset(monkeypatch: pytest.MonkeyPatch, test_business: Business):
    monkeypatch.delenv("ADMIN_API_KEY", raising=False)
    app_config.get_settings.cache_clear()

    fake = MagicMock()
    fake.list_businesses = AsyncMock(return_value=[test_business])
    import app.api.admin as admin

    app.dependency_overrides[admin.get_db] = lambda: fake
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get("/admin/businesses")
        assert r.status_code == 200
    finally:
        app.dependency_overrides.clear()
        app_config.get_settings.cache_clear()


@pytest.mark.asyncio
async def test_admin_auth_rejects_missing_or_wrong_header_when_key_set(
    monkeypatch: pytest.MonkeyPatch, test_business: Business
):
    monkeypatch.setenv("ADMIN_API_KEY", "super-secret")
    app_config.get_settings.cache_clear()

    fake = MagicMock()
    fake.list_businesses = AsyncMock(return_value=[test_business])
    import app.api.admin as admin

    app.dependency_overrides[admin.get_db] = lambda: fake
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r_missing = await ac.get("/admin/businesses")
            r_wrong = await ac.get("/admin/businesses", headers={"X-Admin-Key": "nope"})
        assert r_missing.status_code == 401
        assert r_wrong.status_code == 401
    finally:
        app.dependency_overrides.clear()
        app_config.get_settings.cache_clear()


@pytest.mark.asyncio
async def test_admin_auth_accepts_correct_header_when_key_set(
    monkeypatch: pytest.MonkeyPatch, test_business: Business
):
    monkeypatch.setenv("ADMIN_API_KEY", "super-secret")
    app_config.get_settings.cache_clear()

    fake = MagicMock()
    fake.list_businesses = AsyncMock(return_value=[test_business])
    import app.api.admin as admin

    app.dependency_overrides[admin.get_db] = lambda: fake
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get("/admin/businesses", headers={"X-Admin-Key": "super-secret"})
        assert r.status_code == 200
    finally:
        app.dependency_overrides.clear()
        app_config.get_settings.cache_clear()


@pytest.mark.asyncio
async def test_list_businesses(monkeypatch: pytest.MonkeyPatch, test_business: Business):
    fake = MagicMock()
    fake.list_businesses = AsyncMock(return_value=[test_business])
    import app.api.admin as admin

    app.dependency_overrides[admin.get_db] = lambda: fake
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get("/admin/businesses")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["slug"] == test_business.slug
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_logs_endpoint(monkeypatch: pytest.MonkeyPatch, test_business: Business):
    logs = [
        MessageLog(
            id="1",
            business_id=test_business.id,
            client_phone="573",
            direction="inbound",
            content="hola",
            whatsapp_message_id="w1",
        )
    ]
    fake = MagicMock()
    fake.get_message_logs = AsyncMock(return_value=logs)
    import app.api.admin as admin

    app.dependency_overrides[admin.get_db] = lambda: fake
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get(f"/admin/businesses/{test_business.id}/logs")
        assert r.status_code == 200
        assert r.json()[0]["direction"] == "inbound"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_usage_endpoint(monkeypatch: pytest.MonkeyPatch, test_business: Business):
    from app.models.session import UsageCounter

    fake = MagicMock()
    fake.get_business_by_id = AsyncMock(return_value=test_business)
    fake.get_or_create_usage_counter = AsyncMock(
        return_value=UsageCounter(id="1", business_id=test_business.id, month_year="2026-04", message_count=2)
    )
    import app.api.admin as admin

    app.dependency_overrides[admin.get_db] = lambda: fake
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get(f"/admin/businesses/{test_business.id}/usage")
        assert r.status_code == 200
        body = r.json()
        assert body["message_count"] == 2
        assert "percentage" in body
    finally:
        app.dependency_overrides.clear()
