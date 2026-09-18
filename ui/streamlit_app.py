"""
Simple test UI.
Cholao: streamlit run ui/streamlit_app.py
(Age dummy API port 8001 e ar chat server port 8000 e chalu thakte hobe)
"""

import uuid

import requests
import streamlit as st

API = "http://localhost:8000"

st.set_page_config(page_title="ShopMate", page_icon="🛍️")
st.title("🛍️ E-commerce Agent")

with st.sidebar:
    st.header("Settings")
    user_id = st.selectbox("User", ["U100", "U200", "guest"], index=0)
    mode = st.radio("Mode", ["Single agent", "Multi-agent"], index=0)

    if "session_id" not in st.session_state:
        st.session_state.session_id = f"ui-{uuid.uuid4().hex[:10]}"
    st.caption(f"Session: `{st.session_state.session_id}`")

    if st.button("Clear chat (Redis theke o muche jabe)"):
        requests.delete(f"{API}/sessions/{st.session_state.session_id}")
        st.session_state.messages = []
        st.rerun()

    if st.button(" New session"):
        st.session_state.session_id = f"ui-{uuid.uuid4().hex[:10]}"
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.caption("Try: *5000 takar moddhe headphone dekhao* · "
               "*ORD-1001 kothay ache?* · *last order ta return korte chai*")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("meta"):
            st.caption(m["meta"])

if prompt := st.chat_input("Kichu jiggesh korun..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    endpoint = "/chat" if mode == "Single agent" else "/chat/multi"
    with st.chat_message("assistant"):
        with st.spinner("Vabchi..."):
            try:
                r = requests.post(
                    f"{API}{endpoint}",
                    json={
                        "message": prompt,
                        "session_id": st.session_state.session_id,
                        "user_id": None if user_id == "guest" else user_id,
                    },
                    timeout=120,
                )
                r.raise_for_status()
                data = r.json()
                answer = data["answer"]
                meta = ""
                if data.get("tools_used"):
                    meta = "🔧 " + ", ".join(t["tool"] for t in data["tools_used"])
                elif data.get("handled_by"):
                    meta = f"👤 {data['handled_by']}"
            except Exception as e:
                answer, meta = f"⚠️ Error: {e}", ""

            st.markdown(answer)
            if meta:
                st.caption(meta)

    st.session_state.messages.append({"role": "assistant", "content": answer, "meta": meta})
