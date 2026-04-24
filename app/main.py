import logging

import structlog
from fastapi import FastAPI

from app.api import admin, webhook
from app.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(message)s")


def configure_structlog() -> None:
    settings = get_settings()
    processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]
    if settings.app_env == "production":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )


configure_structlog()

app = FastAPI(title="WhatsApp Agent SaaS", version="0.1.0")

app.include_router(webhook.router)
app.include_router(admin.router)


@app.get("/health")
async def health():
    s = get_settings()
    return {"status": "ok", "env": s.app_env}
