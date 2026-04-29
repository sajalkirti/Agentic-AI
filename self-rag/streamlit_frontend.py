import streamlit as st
import importlib
import self_rag_step7
from langchain_core.messages import HumanMessage

# -----------------------------
# 🔥 FORCE FULL RELOAD (IMPORTANT)
# -----------------------------
importlib.reload(self_rag_step7)

st.cache_data.clear()
st.cache_resource.clear()

app = self_rag_step7.app

# -----------------------------
# Session state init
# -----------------------------
CONFIG = {"configurable": {"thread_id": "thread-1"}}

if "message_history" not in st.session_state:
    st.session_state["message_history"] = []

# -----------------------------
# Render chat history
# -----------------------------
for message in st.session_state["message_history"]:
    with st.chat_message(message["role"]):
        st.text(message["content"])

# -----------------------------
# User input
# -----------------------------
user_input = st.chat_input("Type here")

if user_input:

    # Store user message
    st.session_state["message_history"].append(
        {"role": "user", "content": user_input}
    )

    with st.chat_message("user"):
        st.text(user_input)

    # -----------------------------
    # Build initial graph state
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
    # Run agent graph
    # -----------------------------
    with st.spinner("Analyzing logs..."):
        result = app.invoke(
            initial_state,
            config={"recursion_limit": 80},
        )

    ai_message = result.get("answer", "No response generated.")

    # Store assistant response
    st.session_state["message_history"].append(
        {"role": "assistant", "content": ai_message}
    )

    with st.chat_message("assistant"):
        st.text(ai_message)