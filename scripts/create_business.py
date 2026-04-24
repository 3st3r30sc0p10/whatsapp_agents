#!/usr/bin/env python3
"""Onboard a new SME tenant: Supabase row, Claude Managed Agent + Environment, Kapso webhook."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from anthropic import AsyncAnthropic  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.core.agent import AgentService  # noqa: E402
from app.core.kapso_platform import register_kapso_webhook  # noqa: E402
from app.db.queries import create_business, update_business_agent_ids, update_business  # noqa: E402
from app.models.business import BusinessCreate, BusinessUpdate  # noqa: E402


async def run(
    name: str,
    slug: str,
    phone_number_id: str,
    context: str,
    plan: str,
    webhook_url: str | None,
) -> None:
    settings = get_settings()
    biz = await create_business(
        BusinessCreate(
            name=name,
            slug=slug,
            phone_number_id=phone_number_id,
            business_context=context,
            plan=plan,  # type: ignore[arg-type]
        )
    )
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    agent = AgentService(client, settings)
    agent_id, environment_id = await agent.create_agent_and_environment(name, context)
    await update_business_agent_ids(biz.id, agent_id, environment_id)

    if webhook_url:
        register_kapso_webhook(
            settings.kapso_api_key,
            phone_number_id,
            webhook_url,
            settings.kapso_webhook_secret,
        )
        await update_business(biz.id, BusinessUpdate(webhook_registered=True))

    print(
        json.dumps(
            {
                "business_id": biz.id,
                "slug": slug,
                "phone_number_id": phone_number_id,
                "agent_id": agent_id,
                "environment_id": environment_id,
                "webhook_registered": bool(webhook_url),
            },
            indent=2,
        )
    )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--name", required=True)
    p.add_argument("--slug", required=True)
    p.add_argument("--phone-number-id", required=True)
    p.add_argument("--context", required=True, dest="context")
    p.add_argument("--plan", default="basico", choices=["basico", "estandar", "pro"])
    p.add_argument(
        "--webhook-url",
        default=None,
        help="Full URL to POST /webhook/whatsapp (e.g. https://app.railway.app/webhook/whatsapp)",
    )
    args = p.parse_args()
    asyncio.run(
        run(
            args.name,
            args.slug,
            args.phone_number_id,
            args.context,
            args.plan,
            args.webhook_url,
        )
    )


if __name__ == "__main__":
    main()
