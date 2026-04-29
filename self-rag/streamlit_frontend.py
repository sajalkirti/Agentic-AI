import streamlit as st
from self_rag_step7 import app
from langchain_core.messages import HumanMessage

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="SRE Log Analyzer",
    page_icon="",
    layout="centered"
)

# -----------------------------
# HEADER (COPILOT STYLE)
# -----------------------------
st.markdown(
    """
    <div style="text-align:center;">
        <h1> Welcome to SRE Log Analyzer System</h1>
        <p style="color:gray;">AI-powered incident root cause analysis engine</p>
    </div>
    """,
    unsafe_allow_html=True
)

st.divider()

# -----------------------------
# SESSION STATE
# -----------------------------
CONFIG = {'configurable': {'thread_id': 'thread-1'}}

if "message_history" not in st.session_state:
    st.session_state.message_history = []

# -----------------------------
# CHAT HISTORY RENDER
# -----------------------------
for msg in st.session_state.message_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# -----------------------------
# USER INPUT
# -----------------------------
user_input = st.chat_input("Ask about logs, errors, or correlation IDs...")

if user_input:

    # -----------------------------
    # USER MESSAGE BLOCK
    # -----------------------------
    st.session_state.message_history.append(
        {"role": "user", "content": user_input}
    )

    with st.chat_message("user"):
        st.markdown(f"###  User Query")
        st.markdown(user_input)
        st.divider()

    # -----------------------------
    # INITIAL STATE
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
    }

    # -----------------------------
    # PROCESSING SPINNER
    # -----------------------------
    with st.spinner(" Analyzing logs and tracing incident flow..."):
        result = app.invoke(
            initial_state,
            config={"recursion_limit": 80}
        )

    ai_message = result.get("answer", "No response generated.")

    # -----------------------------
    # ASSISTANT RESPONSE BLOCK
    # -----------------------------
    st.session_state.message_history.append(
        {"role": "assistant", "content": ai_message}
    )

    with st.chat_message("assistant"):
        st.markdown(f"###  SRE Analysis Result")

        st.markdown(ai_message)

        st.divider()

        # Optional debug-style insights (VERY useful for SRE demo)
        if result.get("issup"):
            st.markdown(f"** Support Level:** `{result.get('issup')}`")

        if result.get("isuse"):
            st.markdown(f"**✅ Usefulness:** `{result.get('isuse')}`")

        if result.get("evidence"):
            st.markdown("** Evidence:**")
            for e in result["evidence"]:
                st.markdown(f"- {e}")

        st.divider()