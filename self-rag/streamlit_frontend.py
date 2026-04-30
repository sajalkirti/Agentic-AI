import streamlit as st
import html
from self_rag_step7 import app

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="🚀 SRE Log Analyzer",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# -----------------------------
# HEADER
# -----------------------------
st.markdown(
    """
    <div style="text-align:center;">
        <h1>🚀 SRE Log Analyzer</h1>
        <p style="color:gray;">AI-powered incident root cause analysis engine</p>
    </div>
    """,
    unsafe_allow_html=True
)

st.divider()

# -----------------------------
# HELPER
# -----------------------------
def format_message(text):
    return html.escape(text).replace("\n", "<br>")

# -----------------------------
# SESSION STATE
# -----------------------------
if "message_history" not in st.session_state:
    st.session_state.message_history = []

# -----------------------------
# CUSTOM UI
# -----------------------------
st.markdown("""
<style>
.message-row { display: flex; padding: 10px 0; }
.message-row-user { justify-content: flex-end; }
.message-row-assistant { justify-content: flex-start; }

.user-message {
    background: #f1f3f5;
    padding: 10px 14px;
    border-radius: 10px;
    max-width: 75%;
}

.assistant-message {
    padding: 10px 14px;
    max-width: 80%;
}

.badge {
    font-size: 12px;
    font-weight: bold;
    margin-bottom: 4px;
    color: #555;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# SHOW CHAT HISTORY
# -----------------------------
for msg in st.session_state.message_history:

    # -------------------------
    # SAFE NORMALIZATION
    # -------------------------
    if isinstance(msg, dict):
        role = msg.get("role", "")
        content = msg.get("content", "")
    else:
        # fallback if string or broken entry
        role = "assistant"
        content = str(msg)

    # -------------------------
    # RENDER USER MESSAGE
    # -------------------------
    if role == "user":
        st.markdown(f"""
        <div class="message-row message-row-user">
            <div class="user-message">{format_message(content)}</div>
        </div>
        """, unsafe_allow_html=True)

    # -------------------------
    # RENDER ASSISTANT MESSAGE
    # -------------------------
    else:
        st.markdown(f"""
        <div class="message-row message-row-assistant">
            <div>
                <div class="badge">🤖 LogAnalyzer</div>
                <div class="assistant-message">{format_message(content)}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# -----------------------------
# INPUT
# -----------------------------
user_input = st.chat_input("Ask about logs, errors, CorrelationId, driver issues...")

if user_input:

    # Save user message
    st.session_state.message_history.append(
        {"role": "user", "content": user_input}
    )

    # Display user message immediately
    st.markdown(f"""
    <div class="message-row message-row-user">
        <div class="user-message">{format_message(user_input)}</div>
    </div>
    """, unsafe_allow_html=True)

    # -----------------------------
    # GRAPH INPUT STATE (CLEAN)
    # -----------------------------
    initial_state = {
        "question": user_input,
        "retrieval_query": user_input,
        "rewrite_tries": 0,
        "docs": [],
        "relevant_docs": [],
        "context": "",
        "answer": "",
        "issup": "",
        "evidence": [],
        "retries": 0,
        "isuse": "not_useful",
        "use_reason": "",
        "message_history": st.session_state.message_history,
    }

    # -----------------------------
    # RUN AGENT
    # -----------------------------
    with st.spinner("🔍 Analyzing logs and tracing incident flow..."):
        result = app.invoke(
            initial_state,
            config={"recursion_limit": 80},
        )

    # -----------------------------
    # UPDATE CHAT HISTORY (IMPORTANT FIX)
    # -----------------------------
    st.session_state.message_history = result.get(
    "message_history",
    st.session_state.message_history
    )

    ai_message = result.get("answer", "No response generated.")

    st.session_state.message_history.append(
        {"role": "assistant", "content": ai_message}
    )

    # -----------------------------
    # DISPLAY RESPONSE
    # -----------------------------
    st.markdown(f"""
    <div class="message-row message-row-assistant">
        <div>
            <div class="badge">🤖 LogAnalyzer</div>
            <div class="assistant-message">{format_message(ai_message)}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # -----------------------------
    # DEBUG INFO
    # -----------------------------
    st.divider()

    if result.get("issup"):
        st.markdown(f"**📊 Support Level:** `{result['issup']}`")

    if result.get("isuse"):
        st.markdown(f"**✅ Usefulness:** `{result['isuse']}`")

    if result.get("evidence"):
        st.markdown("**🔍 Evidence:**")
        for e in result["evidence"]:
            st.markdown(f"- {e}")