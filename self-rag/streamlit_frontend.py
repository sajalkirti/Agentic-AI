import time
import streamlit as st

from self_rag_step7 import app
from self_rag_step7 import save_memory


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Enterprise Observability Intelligence Platform",
    page_icon=" ",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.st-emotion-cache-1fnxiie {
    display: none;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# CUSTOM CSS
# =========================================================

st.markdown("""
<style>

/* ============================================
MAIN APP
============================================ */

html, body, [class*="css"] {
    font-family: Inter, sans-serif;
}


.block-container {
    padding-top: 0.4rem !important;  /* reduces gap above title */
}
/* ============================================
SIDEBAR
============================================ */



/* ============================================
SIDEBAR
============================================ */

/* =====================================================
REMOVE EXTRA SPACE ABOVE + BELOW SIDEBAR HEADER ONLY
===================================================== */

/* remove top padding inside sidebar */
[data-testid="stSidebarContent"] {
    padding-top: 0.3rem !important;
}

/* remove default margin from title block */
.sidebar-title {
    margin-top: 0rem !important;
    margin-bottom: 0.2rem !important;
}

/* remove spacing from caption (subtitle) */
[data-testid="stSidebar"] .stCaption {
    margin-top: 0rem !important;
    margin-bottom: 0.5rem !important;
}

/* remove default hr spacing */
[data-testid="stSidebar"] hr {
    margin-top: 0.3rem !important;
    margin-bottom: 0.3rem !important;
}

[data-testid="stSidebar"] {
    background: #F8FAFC;
    border-right: 2px solid #CBD5E1;
}

/* Main title */

.sidebar-title {
    font-size: 24px;
    font-weight: 700;
    color: #0F172A;
    margin-bottom: 10px;
}

/* Section cards */

.sidebar-section {
    padding: 16px;
    border-radius: 14px;
    margin-bottom: 16px;

    background: #FFFFFF;

    border: 1px solid #CBD5E1;

    box-shadow:
        0 2px 6px rgba(0,0,0,0.05);
}

/* Different colored sections */

.sidebar-section:nth-of-type(1) {
    background: #E0F2FE;
}

.sidebar-section:nth-of-type(2) {
    background: #DCFCE7;
}

.sidebar-section:nth-of-type(3) {
    background: #FEF9C3;
}

/* Section headings */

.section-title {
    color: #0F172A;
    font-weight: 700;
    font-size: 16px;
    margin-bottom: 12px;
}

/* Sample questions */

.sample-question {
    background: white;

    color: #1E293B;

    border-left: 4px solid #38BDF8;

    padding: 10px;

    border-radius: 8px;

    margin-bottom: 8px;

    font-size: 14px;

    box-shadow:
        0 1px 3px rgba(0,0,0,0.05);
}

/* ============================================
CHAT
============================================ */

.chat-title {
    color: #0F172A;
}

.chat-subtitle {
    color: #475569;
}

[data-testid="stChatMessage"] {
    padding: 14px;
    border-radius: 16px;
    margin-bottom: 14px;
}

[data-testid="stChatMessageContent"] {
    color: #1E293B !important;
    font-size: 15px;
    line-height: 1.6;
}

/* ============================================
USER MSG
============================================ */

[data-testid="stChatMessage"]:has(.user) {
    background: #E0F2FE;
    border: 1px solid #7DD3FC;
}

/* ============================================
ASSISTANT MSG
============================================ */

[data-testid="stChatMessage"]:has(.assistant) {
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
}

/* ============================================
CODE BLOCKS
============================================ */

pre {
    border-radius: 10px !important;
}

/* ============================================
SCROLLBAR
============================================ */

::-webkit-scrollbar {
    width: 10px;
}

::-webkit-scrollbar-thumb {
    background: #374151;
    border-radius: 10px;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# SESSION STATE
# =========================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "memory_store" not in st.session_state:
    st.session_state.memory_store = []

if "debug_mode" not in st.session_state:
    st.session_state.debug_mode = False


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown(
        '<div class="sidebar-title">Enterprise AI</div>',
        unsafe_allow_html=True
    )

    st.caption(
        "Enterprise Log Investigation Copilot"
    )

    st.markdown("---")
    
    st.page_link(
    "pages/Dashboard.py",
    label="Dashboard",
    icon="📊"
    )

    # =====================================================
    # PROJECT OVERVIEW
    # =====================================================

    st.markdown("""
    <div class="sidebar-section">

    <div class="section-title">
    🚀 Platform Highlights
    </div>

    ✅ Multi-Log Correlation  
    ✅ AI Root Cause Analysis  
    ✅ Cross-System Tracing  
    ✅ Memory-Based Answers  
    ✅ DB + App + Analytics Support  
    ✅ Correlation ID Tracking  
    ✅ Stack Trace Investigation  
    ✅ Failure Pattern Detection  

    </div>
    """, unsafe_allow_html=True)

    # =====================================================
    # LOG TYPES
    # =====================================================

    st.markdown("""
    <div class="sidebar-section">

    <div class="section-title">
    📂 Supported Logs
    </div>

    • Application Logs  
    • Database Logs  
    • Analytics Logs  
    • API Failures  
    • Transaction Logs  
    • Stack Traces  
    • Authentication Logs  
    • Card Validation Logs  

    </div>
    """, unsafe_allow_html=True)
    
    
 
    


    # =====================================================
    # QUESTION FORMAT
    # =====================================================

    st.markdown("""
    <div class="sidebar-section">

    <div class="section-title">
     Best Question Formats
    </div>

    </div>
    """, unsafe_allow_html=True)

    questions = [
        "Why did driver45 fail card validation?",
        "Investigate REQ-AB1234 timeout",
        "Show DB failures for CARD-1002",
        "Why did payment transaction fail?",
        "Find authentication failures for driver22",
        "Trace events for john@enterprise.com",
        "Root cause for analytics timeout issue",
        "Which module caused NullReferenceException?"
    ]

    for q in questions:

        st.markdown(
            f"""
            <div class="sample-question">
            {q}
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")

    # =====================================================
    # DEBUG MODE
    # =====================================================

    st.session_state.debug_mode = st.toggle(
        "Debug Investigation Mode",
        value=False
    )

    st.markdown("---")

    # =====================================================
    # MEMORY
    # =====================================================

    with st.expander("🧠 Investigation Memory"):

        if st.session_state.memory_store:

            for item in reversed(
                st.session_state.memory_store[-5:]
            ):

                st.markdown("### Question")
                st.write(item["question"])

                st.markdown("### Answer")
                st.write(item["answer"][:200] + "...")

                st.markdown("---")

        else:

            st.info("No memory available.")

    # =====================================================
    # EXPORT CHAT
    # =====================================================

    if st.session_state.messages:

        export_text = ""

        for msg in st.session_state.messages:

            export_text += (
                f"{msg['role'].upper()}:\n"
                f"{msg['content']}\n\n"
            )

        st.download_button(
            "📥 Export Investigation",
            export_text,
            file_name="enterprise_investigation.txt"
        )

    # =====================================================
    # CLEAR CHAT
    # =====================================================

    if st.button("🗑️ Clear Conversation"):

        st.session_state.messages = []
        st.session_state.memory_store = []

        st.rerun()


# =========================================================
# MAIN HEADER
# =========================================================

st.markdown("""
<div class="chat-title">

#  Enterprise AI Investigation Console

</div>

<div class="chat-subtitle">

AI-powered enterprise log analysis across
Application, Database, and Analytics systems

</div>
""", unsafe_allow_html=True)


# =========================================================
# LOAD CHAT HISTORY
# =========================================================

for msg in st.session_state.messages:

    with st.chat_message(msg["role"]):

        st.markdown(msg["content"])


# =========================================================
# CHAT INPUT
# =========================================================

user_input = st.chat_input(
    "Ask about failures, users, cards, correlation IDs..."
)


# =========================================================
# MAIN FLOW
# =========================================================

if user_input:

    # =====================================================
    # USER MESSAGE
    # =====================================================

    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })

    with st.chat_message("user"):

        st.markdown(user_input)

    # =====================================================
    # INITIAL STATE
    # =====================================================

    initial_state = {

        "question": user_input,

        "retrieval_query": user_input,
        "rewrite_tries": 0,
        "need_retrieval": True,

        "docs": [],
        "relevant_docs": [],

        "context": "",
        "answer": "",

        "issup": "no_support",
        "evidence": [],
        "retries": 0,

        "isuse": "not_useful",
        "use_reason": "",
    }

    # =====================================================
    # RUN GRAPH
    # =====================================================

    with st.spinner("Analyzing enterprise logs..."):

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

        placeholder = st.empty()

        full_response = ""

        for word in ai_message.split():

            full_response += word + " "

            placeholder.markdown(full_response)

            time.sleep(0.01)

        # =================================================
        # DEBUG PANEL
        # =================================================

        if st.session_state.debug_mode:

            with st.expander(
                "🔍 Investigation Details"
            ):

                tab1, tab2, tab3, tab4 = st.tabs([
                    "Retrieval",
                    "Evidence",
                    "Support",
                    "Documents"
                ])

                # =========================================
                # RETRIEVAL
                # =========================================

                with tab1:

                    st.write(
                        "Need Retrieval:",
                        result.get("need_retrieval")
                    )

                    st.write(
                        "Rewrite Attempts:",
                        result.get("rewrite_tries")
                    )

                    st.write(
                        "Documents Retrieved:",
                        len(result.get("docs", []))
                    )

                    st.write(
                        "Relevant Documents:",
                        len(result.get("relevant_docs", []))
                    )

                # =========================================
                # EVIDENCE
                # =========================================

                with tab2:

                    evidence = result.get(
                        "evidence",
                        []
                    )

                    if evidence:

                        for e in evidence:

                            st.code(e)

                    else:

                        st.info("No evidence found.")

                # =========================================
                # SUPPORT
                # =========================================

                with tab3:

                    st.write(
                        "Support Status:",
                        result.get("issup")
                    )

                    st.write(
                        "Usefulness:",
                        result.get("isuse")
                    )

                    st.write(
                        "Reason:",
                        result.get("use_reason")
                    )

                # =========================================
                # DOCUMENTS
                # =========================================

                with tab4:

                    docs = result.get(
                        "relevant_docs",
                        []
                    )

                    if docs:

                        for idx, doc in enumerate(docs):

                            st.markdown(
                                f"### Document {idx+1}"
                            )

                            st.code(
                                doc.page_content
                            )

                    else:

                        st.info(
                            "No relevant docs found."
                        )

    # =====================================================
    # SAVE MEMORY
    # =====================================================

 #   save_memory(
    #    question=user_input,
    #    answer=ai_message
  #  )

    st.session_state.memory_store.append({
        "question": user_input,
        "answer": ai_message
    })

    # =====================================================
    # SAVE CHAT
    # =====================================================

    st.session_state.messages.append({
        "role": "assistant",
        "content": ai_message
    })