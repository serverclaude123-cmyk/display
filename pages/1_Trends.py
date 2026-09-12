"""Trends & history now live on the device (SD-card logging)."""
from __future__ import annotations

import streamlit as st

from lib.config import DEVICE_URL

st.set_page_config(page_title="Trends", page_icon="📈", layout="centered")
st.title("📈 Trends & history")

st.info(
    "History is logged to the meter's **SD card** (every 10 s, 1-year FIFO) and "
    "served by the ESP32 itself — not stored in the cloud."
)

if DEVICE_URL:
    st.link_button("Open the device dashboard →", DEVICE_URL, type="primary")
    st.caption(f"`{DEVICE_URL}` — reachable from any device on the same Wi-Fi.")
else:
    st.write(
        "Open **`http://<esp32-ip>/`** in a browser on the same Wi-Fi network. "
        "The ESP32 prints its IP to the serial monitor and shows it on the LCD."
    )
    st.caption("Set `device_url` under `[ui]` in the app secrets to show a button here.")

st.divider()
st.markdown(
    "- **Live tiles** — V, I, P, cos φ, frequency, temperature, energy\n"
    "- **Trend charts** — voltage, current, power, temperature per day\n"
    "- **Energy** — kWh per day bar chart\n"
    "- **Download** — raw CSV for any day"
)
