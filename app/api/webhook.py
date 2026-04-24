import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from app.config import Settings, get_settings
from app.core.orchestrator import MessageOrchestrator
from app.core.whatsapp import verify_kapso_signature
from app.dependencies import get_orchestrator
from app.db.queries import get_business_by_phone_number_id
from app.models.message import KapsoWebhookPayload

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhook"])


@router.get("/webhook/whatsapp")
async def whatsapp_webhook_verify(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> PlainTextResponse:
    q = request.query_params
    if q.get("hub.mode") != "subscribe":
        return PlainTextResponse("bad request", status_code=400)
    challenge = q.get("hub.challenge")
    if not challenge:
        return PlainTextResponse("missing challenge", status_code=400)
    token = q.get("hub.verify_token")
    if settings.kapso_verify_token and token != settings.kapso_verify_token:
        return PlainTextResponse("forbidden", status_code=403)
    return PlainTextResponse(challenge)


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
    orchestrator: MessageOrchestrator = Depends(get_orchestrator),
) -> JSONResponse:
    body = await request.body()
    sig = request.headers.get("x-webhook-signature", "")
    if not verify_kapso_signature(settings.kapso_webhook_secret, body, sig):
        logger.warning("invalid_webhook_signature")
        return JSONResponse({"detail": "invalid signature"}, status_code=401)

    try:
        payload = KapsoWebhookPayload.model_validate_json(body)
    except Exception as exc:
        logger.warning("invalid_webhook_json", extra={"error": str(exc)})
        return JSONResponse({"detail": "invalid payload"}, status_code=400)

    if payload.event != "whatsapp.message.received":
        return JSONResponse({"status": "ignored"})

    msg = payload.message
    if msg is None or msg.type != "text" or not msg.text:
        return JSONResponse({"status": "ignored"})

    business = await get_business_by_phone_number_id(payload.phone_number_id)
    if not business:
        logger.error("business_not_found_for_phone", extra={"phone_number_id": payload.phone_number_id})
        return JSONResponse({"status": "ok"})

    text = msg.text.body
    background_tasks.add_task(
        orchestrator.handle_incoming_message,
        business.id,
        msg.from_,
        text,
        msg.id,
    )
    return JSONResponse({"status": "ok"})
