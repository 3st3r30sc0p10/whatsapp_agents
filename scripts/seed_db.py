#!/usr/bin/env python3
"""Insert demo businesses (no Claude agent — for UI / local DB checks only)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402
from app.db.client import get_supabase_client  # noqa: E402


def main() -> None:
    get_settings()
    sb = get_supabase_client()
    rows = [
        {
            "name": "Demo Restaurante",
            "slug": "demo-restaurante",
            "phone_number_id": "000000000000001",
            "business_context": "Demo en Bogotá. Menú del día $20.000.",
            "plan": "basico",
            "monthly_message_limit": 500,
        },
        {
            "name": "Demo Clínica",
            "slug": "demo-clinica",
            "phone_number_id": "000000000000002",
            "business_context": "Demo consultorio. Citas lun–vie 8am–5pm.",
            "plan": "estandar",
            "monthly_message_limit": -1,
        },
    ]
    sb.table("businesses").upsert(rows, on_conflict="slug").execute()
    print("Seed complete:", [r["slug"] for r in rows])


if __name__ == "__main__":
    main()
