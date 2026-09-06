"""Live MQTT feed for the dashboard.

A single background paho-mqtt client (cached across Streamlit reruns) keeps the
latest retained JSON payload in memory. The dashboard just reads `live()` on
every 2 s auto-refresh — no network call in the render path.
"""
from __future__ import annotations

import json
import threading
import time

import paho.mqtt.client as mqtt
import streamlit as st

from lib.config import MQTT

_state = {"payload": None, "rx_epoch": 0.0, "connected": False, "error": None}
_lock = threading.Lock()


def _build_client() -> mqtt.Client:
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"dashboard-{int(time.time())}",
        clean_session=True,
    )
    if MQTT["username"]:
        client.username_pw_set(MQTT["username"], MQTT["password"])
    if MQTT["tls"]:
        client.tls_set()

    def on_connect(c, _u, _flags, reason_code, _props=None):
        ok = int(reason_code) == 0
        with _lock:
            _state["connected"] = ok
            _state["error"] = None if ok else f"connect rc={reason_code}"
        c.subscribe(MQTT["topic"], qos=1)

    def on_disconnect(_c, _u, *_a):
        with _lock:
            _state["connected"] = False

    def on_message(_c, _u, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            with _lock:
                _state["payload"] = payload
                _state["rx_epoch"] = time.time()
                _state["error"] = None
        except Exception as exc:  # noqa: BLE001
            with _lock:
                _state["error"] = f"bad payload: {exc}"

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    client.connect_async(MQTT["host"], MQTT["port"], keepalive=45)
    client.loop_start()
    return client


@st.cache_resource(show_spinner=False)
def _client() -> mqtt.Client:
    return _build_client()


def live() -> dict:
    """Return {payload, rx_epoch, connected, error, age_s}."""
    _client()
    with _lock:
        snap = dict(_state)
    snap["age_s"] = time.time() - snap["rx_epoch"] if snap["rx_epoch"] else None
    return snap
