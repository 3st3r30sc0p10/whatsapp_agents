import asyncio
from datetime import datetime, timezone
from typing import Any, Optional

from supabase import Client

from app.db.client import get_supabase_client
from app.models.business import Business, BusinessCreate, BusinessUpdate
from app.models.session import AgentSession, MessageLog, UsageCounter


def _business_from_row(row: dict[str, Any]) -> Business:
    return Business(
        id=str(row["id"]),
        name=row["name"],
        slug=row["slug"],
        phone_number_id=row["phone_number_id"],
        business_context=row["business_context"],
        agent_id=row.get("agent_id"),
        environment_id=row.get("environment_id"),
        webhook_registered=bool(row.get("webhook_registered", False)),
        is_active=bool(row.get("is_active", True)),
        plan=row.get("plan", "basico"),
        monthly_message_limit=int(row.get("monthly_message_limit", 500)),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


def _session_from_row(row: dict[str, Any]) -> AgentSession:
    return AgentSession(
        id=str(row["id"]),
        client_phone=row["client_phone"],
        business_id=str(row["business_id"]),
        session_id=row["session_id"],
        message_count=int(row.get("message_count", 0)),
        last_message_at=row.get("last_message_at"),
        created_at=row.get("created_at"),
    )


def _log_from_row(row: dict[str, Any]) -> MessageLog:
    return MessageLog(
        id=str(row["id"]),
        business_id=str(row["business_id"]),
        client_phone=row["client_phone"],
        direction=row["direction"],
        content=row["content"],
        whatsapp_message_id=row.get("whatsapp_message_id"),
        processed_at=row.get("processed_at"),
    )


def _usage_from_row(row: dict[str, Any]) -> UsageCounter:
    return UsageCounter(
        id=str(row["id"]),
        business_id=str(row["business_id"]),
        month_year=row["month_year"],
        message_count=int(row.get("message_count", 0)),
    )


def _sb() -> Client:
    return get_supabase_client()


async def get_business_by_phone_number_id(phone_number_id: str) -> Optional[Business]:
    def _run() -> Optional[Business]:
        r = (
            _sb()
            .table("businesses")
            .select("*")
            .eq("phone_number_id", phone_number_id)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        if not r.data:
            return None
        return _business_from_row(r.data[0])

    return await asyncio.to_thread(_run)


async def get_business_by_id(business_id: str) -> Optional[Business]:
    def _run() -> Optional[Business]:
        r = _sb().table("businesses").select("*").eq("id", business_id).limit(1).execute()
        if not r.data:
            return None
        return _business_from_row(r.data[0])

    return await asyncio.to_thread(_run)


async def update_business_agent_ids(
    business_id: str, agent_id: str, environment_id: str
) -> None:
    def _run() -> None:
        _sb().table("businesses").update(
            {"agent_id": agent_id, "environment_id": environment_id}
        ).eq("id", business_id).execute()

    await asyncio.to_thread(_run)


async def list_businesses(include_inactive: bool = False) -> list[Business]:
    def _run() -> list[Business]:
        q = _sb().table("businesses").select("*")
        if not include_inactive:
            q = q.eq("is_active", True)
        r = q.order("created_at", desc=True).execute()
        return [_business_from_row(row) for row in (r.data or [])]

    return await asyncio.to_thread(_run)


async def create_business(data: BusinessCreate) -> Business:
    def _run() -> Business:
        payload = {
            "name": data.name,
            "slug": data.slug,
            "phone_number_id": data.phone_number_id,
            "business_context": data.business_context,
            "plan": data.plan,
            "monthly_message_limit": data.monthly_message_limit,
        }
        r = _sb().table("businesses").insert(payload).execute()
        if not r.data:
            raise RuntimeError("Supabase insert returned no data")
        return _business_from_row(r.data[0])

    return await asyncio.to_thread(_run)


async def update_business(business_id: str, data: BusinessUpdate) -> Business:
    def _run() -> Business:
        patch: dict[str, Any] = {}
        if data.name is not None:
            patch["name"] = data.name
        if data.business_context is not None:
            patch["business_context"] = data.business_context
        if data.plan is not None:
            patch["plan"] = data.plan
        if data.monthly_message_limit is not None:
            patch["monthly_message_limit"] = data.monthly_message_limit
        if data.is_active is not None:
            patch["is_active"] = data.is_active
        if data.webhook_registered is not None:
            patch["webhook_registered"] = data.webhook_registered
        if not patch:
            existing = (
                _sb().table("businesses").select("*").eq("id", business_id).limit(1).execute()
            )
            if not existing.data:
                raise LookupError("business not found")
            return _business_from_row(existing.data[0])
        r = _sb().table("businesses").update(patch).eq("id", business_id).execute()
        if not r.data:
            raise LookupError("business not found")
        return _business_from_row(r.data[0])

    return await asyncio.to_thread(_run)


async def deactivate_business(business_id: str) -> None:
    await update_business(business_id, BusinessUpdate(is_active=False))


async def get_session(client_phone: str, business_id: str) -> Optional[AgentSession]:
    def _run() -> Optional[AgentSession]:
        r = (
            _sb()
            .table("agent_sessions")
            .select("*")
            .eq("client_phone", client_phone)
            .eq("business_id", business_id)
            .limit(1)
            .execute()
        )
        if not r.data:
            return None
        return _session_from_row(r.data[0])

    return await asyncio.to_thread(_run)


async def upsert_session(client_phone: str, business_id: str, session_id: str) -> None:
    def _run() -> None:
        _sb().table("agent_sessions").upsert(
            {
                "client_phone": client_phone,
                "business_id": business_id,
                "session_id": session_id,
                "last_message_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="client_phone,business_id",
        ).execute()

    await asyncio.to_thread(_run)


async def increment_session_message_count(client_phone: str, business_id: str) -> None:
    def _run() -> None:
        r = (
            _sb()
            .table("agent_sessions")
            .select("message_count")
            .eq("client_phone", client_phone)
            .eq("business_id", business_id)
            .limit(1)
            .execute()
        )
        if not r.data:
            return
        n = int(r.data[0].get("message_count", 0)) + 1
        _sb().table("agent_sessions").update(
            {"message_count": n, "last_message_at": datetime.now(timezone.utc).isoformat()}
        ).eq("client_phone", client_phone).eq("business_id", business_id).execute()

    await asyncio.to_thread(_run)


async def delete_session(client_phone: str, business_id: str) -> None:
    def _run() -> None:
        _sb().table("agent_sessions").delete().eq("client_phone", client_phone).eq(
            "business_id", business_id
        ).execute()

    await asyncio.to_thread(_run)


async def list_sessions(business_id: str) -> list[AgentSession]:
    def _run() -> list[AgentSession]:
        r = (
            _sb()
            .table("agent_sessions")
            .select("*")
            .eq("business_id", business_id)
            .order("last_message_at", desc=True)
            .execute()
        )
        return [_session_from_row(row) for row in (r.data or [])]

    return await asyncio.to_thread(_run)


async def log_message(
    business_id: str,
    client_phone: str,
    direction: str,
    content: str,
    wa_message_id: str | None,
) -> None:
    def _run() -> None:
        wid = wa_message_id if wa_message_id else None
        _sb().table("message_logs").insert(
            {
                "business_id": business_id,
                "client_phone": client_phone,
                "direction": direction,
                "content": content,
                "whatsapp_message_id": wid,
            }
        ).execute()

    await asyncio.to_thread(_run)


async def get_message_logs(business_id: str, limit: int = 100) -> list[MessageLog]:
    def _run() -> list[MessageLog]:
        r = (
            _sb()
            .table("message_logs")
            .select("*")
            .eq("business_id", business_id)
            .order("processed_at", desc=True)
            .limit(limit)
            .execute()
        )
        return [_log_from_row(row) for row in (r.data or [])]

    return await asyncio.to_thread(_run)


async def inbound_whatsapp_message_exists(whatsapp_message_id: str) -> bool:
    if not whatsapp_message_id:
        return False

    def _run() -> bool:
        r = (
            _sb()
            .table("message_logs")
            .select("id")
            .eq("whatsapp_message_id", whatsapp_message_id)
            .eq("direction", "inbound")
            .limit(1)
            .execute()
        )
        return bool(r.data)

    return await asyncio.to_thread(_run)


async def get_or_create_usage_counter(business_id: str, month_year: str) -> UsageCounter:
    def _run() -> UsageCounter:
        r = (
            _sb()
            .table("usage_counters")
            .select("*")
            .eq("business_id", business_id)
            .eq("month_year", month_year)
            .limit(1)
            .execute()
        )
        if r.data:
            return _usage_from_row(r.data[0])
        ins = (
            _sb()
            .table("usage_counters")
            .insert({"business_id": business_id, "month_year": month_year})
            .execute()
        )
        if not ins.data:
            raise RuntimeError("usage counter insert failed")
        return _usage_from_row(ins.data[0])

    return await asyncio.to_thread(_run)


async def increment_usage_counter(business_id: str, month_year: str) -> int:
    def _run() -> int:
        sb = _sb()
        r = (
            sb.table("usage_counters")
            .select("*")
            .eq("business_id", business_id)
            .eq("month_year", month_year)
            .limit(1)
            .execute()
        )
        if not r.data:
            sb.table("usage_counters").insert(
                {"business_id": business_id, "month_year": month_year, "message_count": 1}
            ).execute()
            return 1
        row = r.data[0]
        new_count = int(row.get("message_count", 0)) + 1
        sb.table("usage_counters").update({"message_count": new_count}).eq(
            "id", row["id"]
        ).execute()
        return new_count

    return await asyncio.to_thread(_run)


class DatabaseService:
    """Groups DB access for dependency injection."""

    async def get_business_by_phone_number_id(self, phone_number_id: str) -> Optional[Business]:
        return await get_business_by_phone_number_id(phone_number_id)

    async def get_business_by_id(self, business_id: str) -> Optional[Business]:
        return await get_business_by_id(business_id)

    async def update_business_agent_ids(
        self, business_id: str, agent_id: str, environment_id: str
    ) -> None:
        await update_business_agent_ids(business_id, agent_id, environment_id)

    async def list_businesses(self, include_inactive: bool = False) -> list[Business]:
        return await list_businesses(include_inactive)

    async def create_business(self, data: BusinessCreate) -> Business:
        return await create_business(data)

    async def update_business(self, business_id: str, data: BusinessUpdate) -> Business:
        return await update_business(business_id, data)

    async def deactivate_business(self, business_id: str) -> None:
        await deactivate_business(business_id)

    async def get_session(self, client_phone: str, business_id: str) -> Optional[AgentSession]:
        return await get_session(client_phone, business_id)

    async def upsert_session(self, client_phone: str, business_id: str, session_id: str) -> None:
        await upsert_session(client_phone, business_id, session_id)

    async def increment_session_message_count(
        self, client_phone: str, business_id: str
    ) -> None:
        await increment_session_message_count(client_phone, business_id)

    async def delete_session(self, client_phone: str, business_id: str) -> None:
        await delete_session(client_phone, business_id)

    async def list_sessions(self, business_id: str) -> list[AgentSession]:
        return await list_sessions(business_id)

    async def log_message(
        self,
        business_id: str,
        client_phone: str,
        direction: str,
        content: str,
        wa_message_id: str | None,
    ) -> None:
        await log_message(business_id, client_phone, direction, content, wa_message_id)

    async def get_message_logs(self, business_id: str, limit: int = 100) -> list[MessageLog]:
        return await get_message_logs(business_id, limit)

    async def inbound_whatsapp_message_exists(self, whatsapp_message_id: str) -> bool:
        return await inbound_whatsapp_message_exists(whatsapp_message_id)

    async def get_or_create_usage_counter(
        self, business_id: str, month_year: str
    ) -> UsageCounter:
        return await get_or_create_usage_counter(business_id, month_year)

    async def increment_usage_counter(self, business_id: str, month_year: str) -> int:
        return await increment_usage_counter(business_id, month_year)
