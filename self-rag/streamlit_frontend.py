import streamlit as st
from self_rag_step7 import save_memory
from self_rag_step7 import app


# =========================================================
# SESSION STATE
# =========================================================

if "message_history" not in st.session_state:
    st.session_state["message_history"] = []
    
if "memory_store" not in st.session_state:
    st.session_state["memory_store"] = []

    
# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="ShellFleet Log Analyzer",
    page_icon="🛠️",
    layout="wide"
)

st.title("🛠️ ShellFleet Log Analyzer")

# =========================================================
# CONFIG
# =========================================================

CONFIG = {
    "configurable": {
        "thread_id": "thread-1"
    }
}


# =========================================================
# LOAD CHAT HISTORY
# =========================================================

for message in st.session_state["message_history"]:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])

# =========================================================
# USER INPUT
# =========================================================

user_input = st.chat_input(
    "Ask about logs, users, cards, correlation IDs..."
)

# =========================================================
# MAIN FLOW
# =========================================================

if user_input:

    # -----------------------------------------------------
    # SAVE USER MESSAGE
    # -----------------------------------------------------

    st.session_state["message_history"].append(
        {
            "role": "user",
            "content": user_input
        }
    )

    with st.chat_message("user"):

        st.markdown(user_input)

    # -----------------------------------------------------
    # INITIAL GRAPH STATE
    # -----------------------------------------------------

    initial_state = {

        # question
        "question": user_input,

        # retrieval
        "retrieval_query": user_input,
        "rewrite_tries": 0,
        "need_retrieval": True,

        # documents
        "docs": [],
        "relevant_docs": [],

        # answer/context
        "context": "",
        "answer": "",

        # support verification
        "issup": "no_support",
        "evidence": [],
        "retries": 0,

        # usefulness
        "isuse": "not_useful",
        "use_reason": "",
    }

    # -----------------------------------------------------
    # RUN GRAPH
    # -----------------------------------------------------

    with st.spinner("Analyzing logs..."):

        result = app.invoke(
            initial_state,
            config={
                "recursion_limit": 80
            }
        )

    ai_message = result.get(
        "answer",
        "No answer found."
    )

    # =====================================================
    # ASSISTANT RESPONSE
    # =====================================================

    with st.chat_message("assistant"):

        st.markdown(ai_message)

        # -------------------------------------------------
        # OPTIONAL DEBUG DETAILS
        # -------------------------------------------------

        with st.expander("🔍 Investigation Details"):

            st.markdown("### Retrieval")

            st.write(
                "Need Retrieval:",
                result.get("need_retrieval")
            )

            st.write(
                "Rewrite Tries:",
                result.get("rewrite_tries", 0)
            )

            st.write(
                "Retrieved Docs:",
                len(result.get("docs", []))
            )

            st.write(
                "Relevant Docs:",
                len(result.get("relevant_docs", []))
            )

            st.markdown("---")

            st.markdown("### Verification")

            st.write(
                "Support Status:",
                result.get("issup")
            )

            evidence = result.get(
                "evidence",
                []
            )

            if evidence:

                st.markdown("#### Evidence")

                for item in evidence:

                    st.code(item)

            st.markdown("---")

            st.markdown("### Usefulness")

            st.write(
                "Usefulness:",
                result.get("isuse")
            )

            st.write(
                "Reason:",
                result.get("use_reason")
            )
    # SAVE MEMORY
    save_memory(
        question=user_input,
        answer=result["answer"]
    )
    st.session_state["memory_store"].append({
    "question": user_input,
    "answer": result["answer"]
    })
    # -----------------------------------------------------
    # SAVE ASSISTANT MESSAGE
    # -----------------------------------------------------

    st.session_state["message_history"].append(
        {
            "role": "assistant",
            "content": ai_message
        }
    )