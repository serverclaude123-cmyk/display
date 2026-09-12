"""Live MQTT feed for the dashboard.

A single background paho-mqtt client (cached across Streamlit reruns) keeps the
latest retained JSON payload in memory. The dashboard just reads `live()` on
every 2 s auto-refresh — no network call in the render path.
"""
from __future__ import annotations

import json
import socket
import threading
import time

import paho.mqtt.client as mqtt
import streamlit as st

from lib.config import MQTT

# paho's underlying socket.create_connection() call has no timeout of its own,
# so if the network silently drops packets to the broker (rather than
# rejecting the connection) it can hang for minutes with zero callback fired —
# exactly the "connecting… forever, no error" symptom. A process-wide default
# socket timeout forces that connect attempt to fail fast and visibly instead.
# This app's only other network use is Streamlit's own async server, which is
# unaffected (it doesn't rely on the blocking-socket default timeout).
socket.setdefaulttimeout(10)

_state = {
    "payload": None, "rx_epoch": 0.0, "connected": False, "error": None,
    "connect_attempts": 0, "last_attempt_epoch": 0.0,
}
_lock = threading.Lock()


def _build_client() -> mqtt.Client:
    with _lock:
        _state["error"] = None  # clear any stale error from a prior cached attempt

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"dashboard-{int(time.time())}",
        clean_session=True,
    )
    if MQTT["username"]:
        client.username_pw_set(MQTT["username"], MQTT["password"])
    if MQTT["tls"]:
        client.tls_set()  # uses the system/certifi CA bundle

    def on_connect(c, _u, _flags, reason_code, _props=None):
        ok = int(reason_code) == 0
        with _lock:
            _state["connected"] = ok
            _state["error"] = None if ok else f"broker refused: {reason_code}"
        if ok:
            c.subscribe(MQTT["topic"], qos=1)

    def on_connect_fail(_c, _u):
        # TLS/network-level failure — never reaches the MQTT CONNACK, so
        # on_connect never fires. Without this hook the UI just hangs at
        # "connecting…" with zero explanation.
        with _lock:
            _state["connected"] = False
            _state["error"] = "connect_fail: could not reach/negotiate TLS with the broker"

    def on_disconnect(_c, _u, *args):
        with _lock:
            _state["connected"] = False
            if args:  # VERSION2: (disconnect_flags, reason_code, properties)
                _state["error"] = f"disconnected: {args[-2] if len(args) >= 2 else args[-1]}"

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
    client.on_connect_fail = on_connect_fail
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=30)

    with _lock:
        _state["connect_attempts"] += 1
        _state["last_attempt_epoch"] = time.time()
    try:
        client.connect_async(MQTT["host"], MQTT["port"], keepalive=45)
        client.loop_start()
    except Exception as exc:  # noqa: BLE001 - e.g. DNS failure raised synchronously
        with _lock:
            _state["error"] = f"connect_async raised: {exc}"
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


def publish_cmd(cmd: str) -> bool:
    """Publish an "ON"/"OFF" breaker command. Returns True once it's queued
    for delivery (not proof the device received or executed it — watch the
    live status a couple seconds later for that)."""
    client = _client()
    if not client.is_connected():
        return False
    info = client.publish(MQTT["cmd_topic"], cmd, qos=1, retain=False)
    return info.rc == mqtt.MQTT_ERR_SUCCESS
