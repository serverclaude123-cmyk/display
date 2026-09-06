"""Window 2 — Trends for current, power, temperature and voltage (Asia/Jakarta)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from lib import db
from lib.timeutil import TZ

st.set_page_config(page_title="Trends", page_icon="📈", layout="wide")
st.title("📈 Trends")
st.caption("Times shown in Asia/Jakarta (WIB, UTC+7).")

if not db.configured():
    st.error("Supabase is not configured — set `[supabase]` url / anon_key in secrets.")
    st.stop()

# range -> (hours, source table, resample rule, autorefresh ms)
RANGES = {
    "1 hour":  (1,   "readings",      "30s",  30_000),
    "6 hours": (6,   "readings",      "2min", 30_000),
    "24 hours":(24,  "readings_5min", "5min", 300_000),
    "7 days":  (168, "readings_5min", "30min",300_000),
    "30 days": (720, "readings_5min", "3h",   300_000),
}

label = st.radio("Range", list(RANGES), index=2, horizontal=True)
hours, source, rule, refresh_ms = RANGES[label]
st_autorefresh(interval=refresh_ms, key="trends_refresh")

tcol = "ts" if source == "readings" else "bucket"
since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
cols = f"{tcol},v_ln_a,v_ln_b,v_ln_c,v_ll_ab,v_ll_bc,v_ll_ca,i_a,i_b,i_c,p_a,p_b,p_c,p_total,temp"


@st.cache_data(ttl=25, show_spinner="Loading history…")
def load(source: str, tcol: str, cols: str, since_iso: str) -> pd.DataFrame:
    rows = db.query(source, {
        "select": cols,
        tcol: f"gte.{since_iso}",
        "order": f"{tcol}.asc",
        "limit": 50_000,
    })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["t"] = pd.to_datetime(df[tcol], utc=True).dt.tz_convert(TZ)
    return df.drop(columns=[tcol]).set_index("t")


df = load(source, tcol, cols, since)
if df.empty:
    st.info("No data in this range yet.")
    st.stop()

if len(df) > 1500:
    df = df.resample(rule).mean(numeric_only=True).dropna(how="all")

df = df.reset_index()
st.caption(f"{len(df):,} points · source `{source}`")


def line_chart(title: str, series: list[tuple[str, str]], unit: str) -> None:
    fig = go.Figure()
    for col, name in series:
        if col in df:
            fig.add_scatter(x=df["t"], y=df[col], name=name, mode="lines")
    fig.update_layout(
        title=title,
        height=300,
        margin=dict(l=10, r=10, t=40, b=10),
        yaxis_title=unit,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)


c1, c2 = st.columns(2)
with c1:
    line_chart("Voltage L-N", [("v_ln_a", "L1"), ("v_ln_b", "L2"), ("v_ln_c", "L3")], "V")
    line_chart("Voltage L-L", [("v_ll_ab", "L1-L2"), ("v_ll_bc", "L2-L3"), ("v_ll_ca", "L3-L1")], "V")
    line_chart("Temperature", [("temp", "Temp")], "°C")
with c2:
    line_chart("Current", [("i_a", "L1"), ("i_b", "L2"), ("i_c", "L3")], "A")
    line_chart("Power", [("p_a", "L1"), ("p_b", "L2"), ("p_c", "L3"), ("p_total", "Total")], "kW")
