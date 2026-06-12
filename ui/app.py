import os

import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="LawGo Traffic", page_icon="🚦", layout="centered")

st.title("🚦 LawGo Traffic")
st.caption("AI Legal Assistant — Luật Giao thông Đường bộ Việt Nam")

st.info("Chat interface coming soon. See sidebar for available pages.")
