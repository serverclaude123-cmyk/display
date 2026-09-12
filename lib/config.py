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
# Where breaker ON/OFF commands are published; must match MQTT_CMD_TOPIC in the
# ESP32 sketch. Defaults to the state topic's sibling "…/cmd".
MQTT["cmd_topic"] = _get("mqtt", "cmd_topic", "") or (
    MQTT["topic"].rsplit("/", 1)[0] + "/cmd"
)

# UI
LIVE_REFRESH_MS = int(_get("ui", "live_refresh_ms", 2000) or 2000)
TIMEZONE = _get("ui", "timezone", "Asia/Jakarta")
DEVICE_URL = (_get("ui", "device_url", "") or "").rstrip("/")  # http://<esp32-ip> for the on-device trends
