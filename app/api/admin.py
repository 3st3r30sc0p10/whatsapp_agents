from secrets import compare_digest
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.db.queries import DatabaseService
from app.dependencies import _memory_service
from app.models.business import Business, BusinessCreate, BusinessUpdate

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(
    request: Request,
    settings: Settings = Depends(get_settings),
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> None:
    configured_key = (settings.admin_api_key or "").strip()
    # MVP behavior: admin auth is optional unless a key is configured.
    if not configured_key:
        return
    if not x_admin_key or not compare_digest(x_admin_key, configured_key):
        raise HTTPException(status_code=401, detail="invalid admin key")


def get_db() -> DatabaseService:
    return DatabaseService()


@router.post("/businesses", dependencies=[Depends(_require_admin)])
async def create_business(
    body: BusinessCreate,
    db: DatabaseService = Depends(get_db),
) -> Business:
    return await db.create_business(body)


@router.get("/businesses", dependencies=[Depends(_require_admin)])
async def list_businesses(db: DatabaseService = Depends(get_db)) -> list[Business]:
    return await db.list_businesses(include_inactive=True)


@router.get("/businesses/{business_id}", dependencies=[Depends(_require_admin)])
async def get_business(business_id: str, db: DatabaseService = Depends(get_db)) -> Business:
    b = await db.get_business_by_id(business_id)
    if not b:
        raise HTTPException(status_code=404, detail="not found")
    return b


@router.patch("/businesses/{business_id}", dependencies=[Depends(_require_admin)])
async def patch_business(
    business_id: str,
    body: BusinessUpdate,
    db: DatabaseService = Depends(get_db),
) -> Business:
    try:
        return await db.update_business(business_id, body)
    except LookupError:
        raise HTTPException(status_code=404, detail="not found") from None


@router.delete("/businesses/{business_id}", dependencies=[Depends(_require_admin)])
async def delete_business(business_id: str, db: DatabaseService = Depends(get_db)) -> dict[str, str]:
    await db.deactivate_business(business_id)
    return {"status": "deactivated"}


@router.get("/businesses/{business_id}/sessions", dependencies=[Depends(_require_admin)])
async def list_sessions(business_id: str, db: DatabaseService = Depends(get_db)):
    return await db.list_sessions(business_id)


@router.delete(
    "/businesses/{business_id}/sessions/{client_phone}",
    dependencies=[Depends(_require_admin)],
)
async def delete_session_route(business_id: str, client_phone: str, db: DatabaseService = Depends(get_db)):
    await db.delete_session(client_phone, business_id)
    return {"status": "deleted"}


@router.get("/businesses/{business_id}/logs", dependencies=[Depends(_require_admin)])
async def logs(business_id: str, db: DatabaseService = Depends(get_db)):
    return await db.get_message_logs(business_id, 100)


class UsageOut(BaseModel):
    month: str
    message_count: int
    limit: int
    percentage: float


@router.get("/businesses/{business_id}/usage", dependencies=[Depends(_require_admin)])
async def usage(business_id: str, db: DatabaseService = Depends(get_db)) -> UsageOut:
    from datetime import datetime, timezone

    b = await db.get_business_by_id(business_id)
    if not b:
        raise HTTPException(status_code=404, detail="not found")
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    counter = await db.get_or_create_usage_counter(business_id, month)
    limit = b.monthly_message_limit
    pct = 0.0
    if limit > 0:
        pct = round(100.0 * counter.message_count / limit, 1)
    return UsageOut(
        month=month,
        message_count=counter.message_count,
        limit=limit,
        percentage=pct,
    )


def _mem_uid(business_id: str, phone: str) -> str:
    return f"{business_id}:{phone}"


@router.get("/businesses/{business_id}/memories/{client_phone}", dependencies=[Depends(_require_admin)])
async def list_memories(
    business_id: str,
    client_phone: str,
) -> list[dict[str, Any]]:
    mem = _memory_service()
    uid = _mem_uid(business_id, client_phone)
    return mem.get_all(uid)


@router.delete("/businesses/{business_id}/memories/{client_phone}", dependencies=[Depends(_require_admin)])
async def delete_memories(business_id: str, client_phone: str):
    mem = _memory_service()
    uid = _mem_uid(business_id, client_phone)
    mem.delete_all(uid)
    return {"status": "deleted"}