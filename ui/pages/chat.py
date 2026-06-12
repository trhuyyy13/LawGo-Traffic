import os

import httpx
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Chat — LawGo Traffic", page_icon="🚦", layout="centered")
st.title("Hỏi về luật giao thông")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

prompt = st.chat_input("Mô tả tình huống hoặc đặt câu hỏi...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Đang tra cứu..."):
            try:
                resp = httpx.post(f"{API_URL}/chat", json={"message": prompt}, timeout=30)
                answer = resp.json().get("answer", "Lỗi kết nối API.")
            except Exception as e:
                answer = f"Lỗi: {e}"
        st.write(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})
