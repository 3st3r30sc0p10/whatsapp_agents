import asyncio
import re
import time
from datetime import datetime, timezone

import structlog

from app.config import Settings
from app.core.agent import AgentService
from app.core.memory import MemoryService
from app.core.whatsapp import KapsoClient
from app.db.queries import DatabaseService
from app.models.business import Business

logger = structlog.get_logger()


def _phone_suffix(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    return digits[-4:] if len(digits) >= 4 else digits


def _month_year() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


class MessageOrchestrator:
    def __init__(
        self,
        settings: Settings,
        memory: MemoryService,
        agent: AgentService,
        db: DatabaseService,
    ) -> None:
        self._settings = settings
        self._memory = memory
        self._agent = agent
        self._db = db
        self._biz_cache: dict[str, tuple[float, Business]] = {}
        self._cache_ttl_sec = 60.0

    def _cache_get(self, business_id: str) -> Business | None:
        now = time.monotonic()
        hit = self._biz_cache.get(business_id)
        if not hit:
            return None
        ts, biz = hit
        if now - ts > self._cache_ttl_sec:
            del self._biz_cache[business_id]
            return None
        return biz

    def _cache_set(self, business_id: str, biz: Business) -> None:
        self._biz_cache[business_id] = (time.monotonic(), biz)

    async def _get_business_config(self, business_id: str) -> Business:
        cached = self._cache_get(business_id)
        if cached:
            return cached
        biz = await self._db.get_business_by_id(business_id)
        if not biz:
            raise LookupError(f"business not found: {business_id}")
        self._cache_set(business_id, biz)
        return biz

    def _build_prompt(self, memory_context: str, user_message: str) -> str:
        if memory_context:
            return f"{memory_context}\n\nMensaje del cliente:\n{user_message}"
        return user_message

    def _memory_user_id(self, business_id: str, client_phone: str) -> str:
        return f"{business_id}:{client_phone}"

    async def _handle_escalation(
        self, business: Business, client_phone: str, response: str
    ) -> None:
        if "[ESCALATE]" not in response:
            return
        logger.info(
            "escalation_triggered",
            business_id=business.id,
            client_phone_suffix=_phone_suffix(client_phone),
        )

    def _usage_exceeded(self, business: Business, current_count: int) -> bool:
        limit = business.monthly_message_limit
        if limit < 0:
            return False
        return current_count >= limit

    async def handle_incoming_message(
        self,
        business_id: str,
        client_phone: str,
        message_text: str,
        whatsapp_message_id: str,
    ) -> None:
        t0 = time.perf_counter()
        log = logger.bind(
            business_id=business_id,
            client_phone_suffix=_phone_suffix(client_phone),
        )
        wa: KapsoClient | None = None
        try:
            if await self._db.inbound_whatsapp_message_exists(whatsapp_message_id):
                log.warning("duplicate_inbound_skipped", wa_message_id=whatsapp_message_id)
                return

            business = await self._get_business_config(business_id)
            if not business.agent_id or not business.environment_id:
                log.error("business_missing_agent_ids")
                return

            await self._db.log_message(
                business_id,
                client_phone,
                "inbound",
                message_text,
                whatsapp_message_id,
            )

            wa = KapsoClient(
                self._settings.kapso_api_key,
                business.phone_number_id,
                self._settings.kapso_webhook_secret,
            )
            try:
                await wa.send_typing_indicator(client_phone)
            except Exception:
                pass

            month = _month_year()
            usage = await self._db.get_or_create_usage_counter(business_id, month)
            if self._usage_exceeded(business, usage.message_count):
                await wa.send_text(
                    client_phone,
                    "Por el momento hemos alcanzado el límite de mensajes del plan. Un asesor te contactará pronto.",
                )
                await self._db.log_message(
                    business_id,
                    client_phone,
                    "outbound",
                    "plan_limit_message",
                    None,
                )
                return

            mem_uid = self._memory_user_id(business_id, client_phone)
            memories = await asyncio.to_thread(
                self._memory.search, message_text, mem_uid
            )
            memory_context = MemoryService.format_for_prompt(memories)

            row = await self._db.get_session(client_phone, business_id)
            db_sid = row.session_id if row else None

            session_id = await self._agent.get_or_create_session(
                client_phone,
                business.agent_id,
                business.environment_id,
                db_sid,
            )
            if not row or row.session_id != session_id:
                await self._db.upsert_session(client_phone, business_id, session_id)

            prompt = self._build_prompt(memory_context, message_text)
            response_text: str | None = None
            try:
                response_text = await self._agent.send_message(session_id, prompt)
            except Exception as exc1:
                log.warning("claude_send_failed_retry", error_type=type(exc1).__name__)
                new_sid = await self._agent.get_or_create_session(
                    client_phone,
                    business.agent_id,
                    business.environment_id,
                    None,
                )
                await self._db.upsert_session(client_phone, business_id, new_sid)
                try:
                    response_text = await self._agent.send_message(new_sid, prompt)
                    session_id = new_sid
                except Exception as exc2:
                    log.error("claude_send_failed", error_type=type(exc2).__name__)
                    response_text = (
                        "Disculpa, tuve un inconveniente técnico. Por favor escribe de nuevo en un momento."
                    )

            if response_text is None:
                log.error("empty_response_text")
                response_text = (
                    "Disculpa, tuve un inconveniente técnico. "
                    "Por favor escribe de nuevo en un momento."
                )
            await self._handle_escalation(business, client_phone, response_text)

            await wa.send_text(client_phone, response_text)
            await asyncio.to_thread(
                self._memory.add, message_text, response_text, mem_uid
            )

            await self._db.log_message(
                business_id,
                client_phone,
                "outbound",
                response_text,
                None,
            )
            await self._db.increment_session_message_count(client_phone, business_id)
            new_usage = await self._db.increment_usage_counter(business_id, month)

            duration_ms = int((time.perf_counter() - t0) * 1000)
            log.info(
                "message_processed",
                message_length=len(message_text),
                memory_results=len(memories),
                response_length=len(response_text),
                duration_ms=duration_ms,
                usage_count=new_usage,
            )
        except Exception as exc:
            logger.exception(
                "orchestrator_fatal",
                business_id=business_id,
                client_phone_suffix=_phone_suffix(client_phone),
                error_type=type(exc).__name__,
            )
            try:
                business = await self._db.get_business_by_id(business_id)
                if business:
                    fallback = KapsoClient(
                        self._settings.kapso_api_key,
                        business.phone_number_id,
                        self._settings.kapso_webhook_secret,
                    )
                    try:
                        await fallback.send_text(
                            client_phone,
                            "Disculpa, tuve un inconveniente técnico. Por favor escribe de nuevo en un momento.",
                        )
                    finally:
                        await fallback.aclose()
            except Exception:
                pass
        finally:
            if wa is not None:
                try:
                    await wa.aclose()
                except Exception:
                    pass
