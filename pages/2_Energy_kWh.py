"""Window 3 — Energy (kWh): daily, monthly, yearly (Asia/Jakarta calendar)."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from lib import db
from lib.timeutil import now_tz

st.set_page_config(page_title="Energy kWh", page_icon="🔋", layout="wide")
st.title("🔋 Energy — kWh")
st.caption("Daily / monthly / yearly consumption on the Asia/Jakarta calendar. Source: Supabase.")

if not db.configured():
    st.error("Supabase is not configured — set `[supabase]` url / anon_key in secrets.")
    st.stop()


@st.cache_data(ttl=300, show_spinner="Loading energy history…")
def load(view: str, key: str) -> pd.DataFrame:
    rows = db.query(view, {"select": "*", "order": f"{key}.asc"})
    df = pd.DataFrame(rows)
    if not df.empty:
        df[key] = pd.to_datetime(df[key])
        df["kwh"] = df["kwh"].astype(float).round(2)
    return df


daily = load("energy_daily", "day")
monthly = load("energy_monthly", "month")
yearly = load("energy_yearly", "year")
latest = db.latest_reading()

today = now_tz().date()
kwh_today = float(daily.loc[daily["day"].dt.date == today, "kwh"].sum()) if not daily.empty else 0.0
kwh_month = float(monthly.iloc[-1]["kwh"]) if not monthly.empty else 0.0
kwh_year = float(yearly.iloc[-1]["kwh"]) if not yearly.empty else 0.0

m = st.columns(4)
m[0].metric("Today", f"{kwh_today:,.1f} kWh")
m[1].metric("This month", f"{kwh_month:,.1f} kWh")
m[2].metric("This year", f"{kwh_year:,.1f} kWh")
m[3].metric("Meter counter", f"{latest['kwh']:,.1f} kWh" if latest else "—")

daily_tab, monthly_tab, yearly_tab = st.tabs(["Daily", "Monthly", "Yearly"])


def bar(df: pd.DataFrame, key: str, tick: str) -> None:
    if df.empty:
        st.info("No data yet.")
        return
    fig = px.bar(df, x=key, y="kwh", labels={"kwh": "kWh", key: ""})
    fig.update_xaxes(dtick=tick, tickformat="%Y-%m-%d" if key == "day" else "%Y-%m")
    fig.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df.iloc[::-1], use_container_width=True, hide_index=True)


with daily_tab:
    days = st.slider("Days to show", 7, 365, 30)
    bar(daily.tail(days), "day", "D1" if days <= 31 else "D7")
with monthly_tab:
    bar(monthly.tail(36), "month", "M1")
with yearly_tab:
    bar(yearly, "year", "M12")
