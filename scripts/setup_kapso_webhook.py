#!/usr/bin/env python3
"""Register Kapso WhatsApp webhook for a phone number."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402
from app.core.kapso_platform import register_kapso_webhook  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="Register Kapso webhook for a WhatsApp number")
    p.add_argument("--phone-number-id", required=True)
    p.add_argument("--webhook-url", required=True)
    p.add_argument("--secret-key", default=None, help="Defaults to KAPSO_WEBHOOK_SECRET from .env")
    args = p.parse_args()
    settings = get_settings()
    secret = args.secret_key or settings.kapso_webhook_secret
    out = register_kapso_webhook(
        settings.kapso_api_key,
        args.phone_number_id,
        args.webhook_url,
        secret,
    )
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
