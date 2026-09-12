"""Window 1 — Live power dashboard (1- or 3-phase, refreshes every 2 s from MQTT)."""
from __future__ import annotations

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from lib.config import LIVE_REFRESH_MS
from lib.mqtt_live import live
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

left, right = st.columns([0.7, 0.3])
left.title("⚡ Power Meter" + ("" if nphases == 3 else "  ·  1-phase"))
with right:
    st.caption(f"🕒 {now_tz():%Y-%m-%d %H:%M:%S} WIB")
    if snap["connected"]:
        st.caption("🟢 MQTT connected")
    else:
        st.caption(f"🔴 MQTT offline — {snap['error'] or 'connecting…'}")
    if snap["age_s"] is not None:
        rx = epoch_to_tz(snap["rx_epoch"])
        st.caption(f"last packet {rx:%H:%M:%S} ({fmt_age(snap['age_s'])})")

if p is None:
    st.info("Waiting for the first MQTT message…")
    st.stop()

if snap["age_s"] and snap["age_s"] > 15:
    st.warning(f"Data is stale — last update {fmt_age(snap['age_s'])}.")

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
    "Live view is MQTT. Trend history is logged to the meter's SD card and "
    "served by the device — see the **Trends** page in the sidebar."
)
