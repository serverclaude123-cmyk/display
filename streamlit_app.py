"""Window 1 — Live power dashboard (1- or 3-phase, refreshes every 2 s from MQTT)."""
from __future__ import annotations

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from lib.config import LIVE_REFRESH_MS, MQTT
from lib.mqtt_live import get_log, live, publish_cmd
from lib.timeutil import epoch_to_tz, fmt_age, now_tz

st.set_page_config(page_title="Power Meter — Live", page_icon="⚡", layout="wide")
st_autorefresh(interval=LIVE_REFRESH_MS, key="live_refresh")

PHASES = ["A · L1", "B · L2", "C · L3"]
LL = ["L1–L2", "L2–L3", "L3–L1"]


def g(payload: dict, key: str, idx: int | None = None, default=0.0):
    val = payload.get(key, default)
    if idx is not None:
        try:
            return val[idx]
        except (TypeError, IndexError, KeyError):
            return default
    return val if val is not None else default


snap = live()
p = snap["payload"]

nphases = int(g(p, "phases", default=3)) if p else 3
sw = int(g(p, "sw", default=-1)) if p else -1
BREAKER = {1: ("🟢 ON", "green"), 0: ("🔴 OFF", "red"), 2: ("🟡 OPENING", "orange")}.get(sw, ("⚪ UNKNOWN", "gray"))

left, right = st.columns([0.7, 0.3])
with left:
    st.title("⚡ Power Meter" + ("" if nphases == 3 else "  ·  1-phase"))
    st.markdown(f"**BREAKER:** :{BREAKER[1]}[{BREAKER[0]}]")
with right:
    st.caption(f"🕒 {now_tz():%Y-%m-%d %H:%M:%S} WIB")
    if snap["connected"]:
        st.caption("🟢 MQTT connected")
    else:
        st.caption(f"🔴 MQTT offline — {snap['error'] or 'connecting…'}")
    if snap["age_s"] is not None:
        rx = epoch_to_tz(snap["rx_epoch"])
        st.caption(f"last packet {rx:%H:%M:%S} ({fmt_age(snap['age_s'])})")

with st.expander("🔧 MQTT connection debug"):
    st.json({k: v for k, v in snap.items() if k != "payload"})
    st.caption("Broker/topic this app is using (from Secrets):")
    st.code(f"host={MQTT['host']}:{MQTT['port']}  tls={MQTT['tls']}  topic={MQTT['topic']}")
    st.caption("paho's internal log (does it even send CONNECT / hear anything back?):")
    log = get_log()
    st.code("\n".join(log) if log else "(empty)")

if p is None:
    st.info("Waiting for the first MQTT message…")
    st.stop()

if snap["age_s"] and snap["age_s"] > 15:
    st.warning(f"Data is stale — last update {fmt_age(snap['age_s'])}.")

# ── Breaker control (MQTT command topic, confirm-before-send) ──────────────
if "confirm_cmd" not in st.session_state:
    st.session_state.confirm_cmd = None

if st.session_state.confirm_cmd is None:
    bcol1, bcol2, _ = st.columns([1, 1, 3])
    if bcol1.button("🔴 Turn breaker OFF", use_container_width=True):
        st.session_state.confirm_cmd = "OFF"
        st.rerun()
    if bcol2.button("🟢 Turn breaker ON", use_container_width=True):
        st.session_state.confirm_cmd = "ON"
        st.rerun()
else:
    cmd = st.session_state.confirm_cmd
    st.warning(f"Confirm: send **{cmd}** to the breaker?")
    ycol, ncol, _ = st.columns([1, 1, 3])
    if ycol.button(f"Yes, turn {cmd}", type="primary", use_container_width=True):
        ok = publish_cmd(cmd)
        st.session_state.confirm_cmd = None
        if ok:
            st.success("Command sent — status above updates within ~2 s.")
        else:
            st.error("Could not send — MQTT isn't connected right now.")
        st.rerun()
    if ncol.button("Cancel", use_container_width=True):
        st.session_state.confirm_cmd = None
        st.rerun()

if nphases == 1:
    # ── Single-phase ──────────────────────────────────────────────────────
    st.subheader("Line")
    a = st.columns(4)
    a[0].metric("Voltage", f"{g(p, 'v_ln', 0):.1f} V")
    a[1].metric("Current", f"{g(p, 'i', 0):.2f} A")
    a[2].metric("Active power", f"{g(p, 'p_total'):.3f} kW")
    a[3].metric("cos φ", f"{g(p, 'pf_total'):.3f}")

    st.subheader("System")
    c = st.columns(3)
    c[0].metric("Frequency", f"{g(p, 'freq'):.2f} Hz")
    c[1].metric("Temperature", f"{g(p, 'temp'):.1f} °C")
    c[2].metric("Energy (lifetime)", f"{g(p, 'kwh'):,.1f} kWh")
else:
    # ── Per-phase cards ───────────────────────────────────────────────────
    st.subheader("Per phase")
    for col, name, i in zip(st.columns(3), PHASES, range(3)):
        with col:
            st.markdown(f"**Phase {name}**")
            st.metric("Voltage L-N", f"{g(p, 'v_ln', i):.1f} V")
            st.metric("Current", f"{g(p, 'i', i):.2f} A")
            st.metric("Power", f"{g(p, 'p', i):.3f} kW")
            st.metric("cos φ", f"{g(p, 'pf', i):.3f}")

    st.subheader("Phase to phase")
    for col, name, i in zip(st.columns(3), LL, range(3)):
        col.metric(f"Voltage {name}", f"{g(p, 'v_ll', i):.1f} V")

    st.subheader("System")
    c = st.columns(6)
    c[0].metric("Total active power", f"{g(p, 'p_total'):.3f} kW")
    c[1].metric("Total cos φ", f"{g(p, 'pf_total'):.3f}")
    c[2].metric("Frequency", f"{g(p, 'freq'):.2f} Hz")
    c[3].metric("Temperature", f"{g(p, 'temp'):.1f} °C")
    c[4].metric("Energy (lifetime)", f"{g(p, 'kwh'):,.1f} kWh")
    avg_vln = sum(g(p, "v_ln", i) for i in range(3)) / 3
    c[5].metric("Avg V L-N", f"{avg_vln:.1f} V")

st.caption(
    "Live view + breaker control both go over MQTT, so this works from anywhere — not just "
    "on the same Wi-Fi. Trend & energy history is on the meter's SD card — see the "
    "**Trends** page (or the device's own page at `http://<esp32-ip>/`)."
)
