import streamlit as st
from self_rag_step7 import app, new_memory, detect_identity, identity_context


# =========================================================
# SESSION STATE
# =========================================================

if "message_history" not in st.session_state:
    st.session_state["message_history"] = []

# Per-session Q&A memory (not shared across users / browser sessions).
if "memory" not in st.session_state:
    st.session_state["memory"] = new_memory()

# Per-session identity the user has stated about themselves (e.g. "I am driver002").
if "identity" not in st.session_state:
    st.session_state["identity"] = {}


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
    # UPDATE IDENTITY + BUILD CONVERSATION CONTEXT
    # -----------------------------------------------------

    detected = detect_identity(user_input)
    if detected:
        st.session_state["identity"].update(detected)

    user_context = identity_context(st.session_state["identity"])

    # recent turns BEFORE the current question (capped to keep prompts small)
    prior = st.session_state["message_history"][:-1][-6:]
    history = "\n".join(
        f"{m['role']}: {m['content']}" for m in prior
    )

    # -----------------------------------------------------
    # INITIAL GRAPH STATE
    # -----------------------------------------------------

    initial_state = {

        # question
        "question": user_input,

        # conversation context
        "history": history,
        "user_context": user_context,

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
        "from_memory": False,

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

    try:
        with st.spinner("Analyzing logs..."):

            result = app.invoke(
                initial_state,
                config={
                    "recursion_limit": 80,
                    "configurable": {
                        "memory": st.session_state["memory"]
                    }
                }
            )
    except Exception as e:
        st.error(f"Analysis failed: {e}")
        st.stop()

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
    # Memory is already persisted inside the graph (per-session, via config).

    # -----------------------------------------------------
    # SAVE ASSISTANT MESSAGE
    # -----------------------------------------------------

    st.session_state["message_history"].append(
        {
            "role": "assistant",
            "content": ai_message
        }
    )

# =========================================================
# SIDEBAR: SESSION IDENTITY
# =========================================================

with st.sidebar:

    st.header("Session identity")

    identity = st.session_state.get("identity", {})

    if identity:
        st.json(identity)
    else:
        st.caption('No identity yet. Try: "I am driver002".')