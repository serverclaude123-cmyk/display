"""Read-only Supabase (PostgREST) access for the history pages."""
from __future__ import annotations

import httpx

from lib.config import SUPABASE

_BASE = f"{SUPABASE['url']}/rest/v1"
_HEADERS = {
    "apikey": SUPABASE["anon_key"],
    "Authorization": f"Bearer {SUPABASE['anon_key']}",
    "Accept": "application/json",
}


def configured() -> bool:
    return bool(SUPABASE["url"] and SUPABASE["anon_key"])


def query(path: str, params: dict) -> list[dict]:
    resp = httpx.get(f"{_BASE}/{path}", params=params, headers=_HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.json()


def latest_reading() -> dict | None:
    rows = query("readings", {"select": "ts,kwh,p_total", "order": "ts.desc", "limit": 1})
    return rows[0] if rows else None
