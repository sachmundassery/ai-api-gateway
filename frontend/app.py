import streamlit as st
import httpx
import time

import os
BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="AI API Gateway",
    page_icon="🚀",
    layout="wide"
)

# --- Auth helpers ---
def login(username: str, password: str):
    try:
        response = httpx.post(f"{BASE_URL}/auth/login", json={
            "username": username,
            "password": password
        })
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Connection error: {e}")
        return None

def get_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}

def fetch_stats():
    try:
        response = httpx.get(f"{BASE_URL}/monitoring/stats", headers=get_headers())
        return response.json()
    except Exception:
        return {}

def fetch_logs():
    try:
        response = httpx.get(f"{BASE_URL}/monitoring/logs?limit=5", headers=get_headers())
        return response.json().get("logs", [])
    except Exception:
        return []

# --- Session state ---
if "token" not in st.session_state:
    st.session_state.token = None
if "username" not in st.session_state:
    st.session_state.username = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Login page ---
if not st.session_state.token:
    st.title("🚀 AI API Gateway")
    st.caption("Production-grade AI with auth, rate limiting, caching and monitoring")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.subheader("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login", use_container_width=True):
            result = login(username, password)
            if result:
                st.session_state.token = result["access_token"]
                st.session_state.username = result["username"]
                st.rerun()
            else:
                st.error("Invalid credentials")

        st.info("Credentials: string / string")

# --- Main dashboard ---
else:
    st.title("🚀 AI API Gateway Dashboard")
    st.caption(f"Logged in as **{st.session_state.username}**")

    if st.button("Logout", type="secondary"):
        st.session_state.token = None
        st.session_state.username = None
        st.session_state.messages = []
        st.rerun()

    # --- Stats row ---
    stats = fetch_stats()
    if stats:
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Total Requests", stats.get("total_requests", 0))
        col2.metric("Cache Hit Rate", stats.get("cache_hit_rate", "0%"))
        col3.metric("Avg Latency", f"{stats.get('avg_latency_ms', 0)}ms")
        col4.metric("Errors", stats.get("errors", 0))
        col5.metric("Success Rate", stats.get("success_rate", "100%"))

    st.divider()

    # --- Two column layout ---
    col_chat, col_monitor = st.columns([3, 2])

    # --- Chat interface ---
    with col_chat:
        st.subheader("💬 AI Chat")

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
                if message.get("metadata"):
                    meta = message["metadata"]
                    cols = st.columns(3)
                    cols[0].caption(f"{'✅ Cached' if meta.get('cached') else '🤖 LLM'}")
                    cols[1].caption(f"⚡ {meta.get('latency_ms', 0)}ms")
                    if meta.get("similarity_score"):
                        cols[2].caption(f"🎯 {meta.get('similarity_score')} similarity")

        if prompt := st.chat_input("Ask anything..."):
            st.session_state.messages.append({
                "role": "user",
                "content": prompt
            })

            with st.chat_message("user"):
                st.write(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Processing..."):
                    try:
                        response = httpx.post(
                            f"{BASE_URL}/ai/query",
                            json={"question": prompt, "context": ""},
                            headers=get_headers(),
                            timeout=30
                        )

                        if response.status_code == 200:
                            data = response.json()
                            st.write(data["answer"])

                            cols = st.columns(3)
                            cols[0].caption(f"{'✅ Cached' if data.get('cached') else '🤖 LLM'}")
                            cols[1].caption(f"⚡ {data.get('latency_ms', 0)}ms")
                            if data.get("similarity_score"):
                                cols[2].caption(f"🎯 {data.get('similarity_score')} similarity")

                            rate_info = data.get("rate_limit_info", {})
                            remaining = rate_info.get("requests_remaining", 0)
                            if remaining <= 2:
                                st.warning(f"⚠️ Only {remaining} requests remaining in this window!")

                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": data["answer"],
                                "metadata": data
                            })

                        elif response.status_code == 429:
                            st.error("❌ Rate limit exceeded! Please wait 60 seconds.")
                        elif response.status_code == 401:
                            st.error("❌ Session expired. Please login again.")
                            st.session_state.token = None
                            st.rerun()
                        else:
                            st.error(f"Error: {response.status_code}")

                    except Exception as e:
                        st.error(f"Connection error: {e}")

    # --- Monitoring panel ---
    with col_monitor:
        st.subheader("📊 Live Monitoring")

        if st.button("🔄 Refresh Stats"):
            st.rerun()

        logs = fetch_logs()
        if logs:
            st.caption("Recent requests:")
            for log in logs:
                status_icon = "✅" if log.get("status") == "success" else "❌"
                cached_icon = "💾" if log.get("cached") else "🤖"
                with st.expander(
                    f"{status_icon} {cached_icon} {log.get('question', '')[:40]}..."
                ):
                    st.write(f"**User:** {log.get('username')}")
                    st.write(f"**Latency:** {log.get('latency_ms')}ms")
                    st.write(f"**Cached:** {log.get('cached')}")
                    st.write(f"**Time:** {log.get('timestamp')}")
        else:
            st.info("No requests yet — ask something!")

        st.divider()
        st.subheader("🔑 Rate Limit Info")
        try:
            rl_response = httpx.get(
                f"{BASE_URL}/rate-limit-test",
                headers=get_headers()
            )
            if rl_response.status_code == 200:
                rl_data = rl_response.json()
                rl_info = rl_data.get("rate_limit_info", {})
                remaining = rl_info.get("requests_remaining", 0)
                limit = rl_info.get("limit", 10)
                st.progress(remaining / limit)
                st.caption(f"{remaining}/{limit} requests remaining")
        except Exception:
            st.caption("Rate limit info unavailable")