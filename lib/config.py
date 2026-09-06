"""Configuration loader. Works inside Streamlit (st.secrets) and plain scripts (env)."""
from __future__ import annotations

import os

try:
    import streamlit as st

    _secrets = st.secrets
except Exception:  # not running under Streamlit
    _secrets = {}


def _get(section: str, key: str, default=None):
    if section in _secrets and key in _secrets[section]:
        return _secrets[section][key]
    env_key = f"{section.upper()}_{key.upper()}"
    return os.environ.get(env_key, default)


MQTT = {
    "host": _get("mqtt", "host", "localhost"),
    "port": int(_get("mqtt", "port", 8883) or 8883),
    "username": _get("mqtt", "username", "") or "",
    "password": _get("mqtt", "password", "") or "",
    "topic": _get("mqtt", "topic", "powermeter/meter01/state"),
    "tls": str(_get("mqtt", "tls", "true")).lower() == "true",
}

SUPABASE = {
    "url": (_get("supabase", "url", "") or "").rstrip("/"),
    "anon_key": _get("supabase", "anon_key", "") or "",
}

# UI
LIVE_REFRESH_MS = int(_get("ui", "live_refresh_ms", 2000) or 2000)
TIMEZONE = _get("ui", "timezone", "Asia/Jakarta")
