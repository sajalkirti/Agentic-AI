import streamlit as st
import html
from self_rag_step7 import app
from langchain_core.messages import HumanMessage

# Page configuration
st.set_page_config(
    page_title="LogInsight - AI Assistant",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Helper function to format messages
def format_message(text):
    """Escape HTML and preserve line breaks"""
    text = html.escape(text)
    text = text.replace('\n', '<br>')
    return text

# Add custom CSS for chat UI
st.markdown("""
<style>
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Main container */
    .stApp {
        background-color: #ffffff;
        max-width: 1200px;
        margin: 0 auto;
    }
    
    /* Message rows */
    .message-row {
        display: flex;
        padding: 20px 0;
        width: 100%;
        align-items: flex-start;
    }
    
    .message-row-user {
        justify-content: flex-end;
        text-align: right;
    }
    
    .message-row-assistant {
        justify-content: flex-start;
    }
    
    /* User message - grey background on right */
    .user-message {
        color: #1f2328;
        font-size: 15px;
        line-height: 1.6;
        max-width: 80%;
        padding: 12px 16px;
        word-wrap: break-word;
        background-color: #f6f8fa;
        border-radius: 12px;
        border: 1px solid #d0d7de;
    }
    
    /* Assistant message container */
    .assistant-container {
        display: block;
        max-width: 90%;
    }
    
    /* Copilot icon/badge */
    .copilot-badge {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 12px;
    }
    
    .copilot-icon {
        width: 20px;
        height: 20px;
        background-color: #1f2328;
        border-radius: 4px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 11px;
        font-weight: 600;
    }
    
    .copilot-text {
        font-size: 14px;
        font-weight: 600;
        color: #1f2328;
    }
    
    /* Assistant message content */
    .assistant-message {
        color: #1f2328;
        font-size: 15px;
        line-height: 1.6;
        padding-left: 0;
    }
    
    .assistant-message p {
        margin: 0 0 12px 0;
    }
    
    .assistant-message ul {
        margin: 8px 0;
        padding-left: 20px;
    }
    
    .assistant-message li {
        margin: 6px 0;
    }
    
    /* Code styling */
    .assistant-message code {
        background-color: #f6f8fa;
        padding: 2px 6px;
        border-radius: 3px;
        font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace;
        font-size: 13px;
    }
    
    /* Links */
    .assistant-message a {
        color: #0969da;
        text-decoration: none;
    }
    
    .assistant-message a:hover {
        text-decoration: underline;
    }
    
    /* Input area */
    .stChatInput {
        max-width: 1200px;
        margin: 0 auto;
    }
    
    /* Remove extra padding */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# SESSION STATE
# -----------------------------
CONFIG = {'configurable': {'thread_id': 'thread-1'}}

if "message_history" not in st.session_state:
    st.session_state.message_history = []

# Show welcome message if no history
if len(st.session_state.message_history) == 0:
    st.markdown("""
    <div style="padding: 60px 20px; text-align: center;">
        <div style="display: flex; align-items: center; justify-content: center; gap: 8px; margin-bottom: 20px;">
            <div style="width: 28px; height: 28px; background-color: #1f2328; border-radius: 6px; display: flex; align-items: center; justify-content: center; color: white;">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                    <path d="M7.5 1.5a6 6 0 1 0 0 12 6 6 0 0 0 0-12zm0 10.5a4.5 4.5 0 1 1 0-9 4.5 4.5 0 0 1 0 9z"/>
                </svg>
            </div>
            <span style="font-size: 18px; font-weight: 600; color: #1f2328;">LogInsight</span>
        </div>
        <p style="color: #656d76; font-size: 15px; line-height: 1.6; max-width: 500px; margin: 0 auto;">
            Hello! How can I help you right now?<br><br>
            Ask me about application errors, log analysis, or troubleshooting.
        </p>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------
# CHAT HISTORY RENDER
# -----------------------------
for msg in st.session_state.message_history:
    if msg['role'] == 'user':
        st.markdown(f"""
        <div class="message-row message-row-user">
            <div class="user-message">
                {format_message(msg['content'])}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="message-row message-row-assistant">
            <div class="assistant-container">
                <div class="copilot-badge">
                    <div class="copilot-icon">
                        <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
                            <path d="M7.5 1.5a6 6 0 1 0 0 12 6 6 0 0 0 0-12zm0 10.5a4.5 4.5 0 1 1 0-9 4.5 4.5 0 0 1 0 9z"/>
                        </svg>
                    </div>
                    <span class="copilot-text">LogInsight</span>
                </div>
                <div class="assistant-message">
                    {format_message(msg['content'])}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

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

    # Display user message
    st.markdown(f"""
    <div class="message-row message-row-user">
        <div class="user-message">
            {format_message(user_input)}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    scroll_anchor = st.empty()
    scroll_anchor.markdown("")

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
    with st.spinner("🔍 Analyzing logs and tracing incident flow..."):
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

    # Display assistant message
    st.markdown(f"""
    <div class="message-row message-row-assistant">
        <div class="assistant-container">
            <div class="copilot-badge">
                <div class="copilot-icon">
                    <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
                        <path d="M7.5 1.5a6 6 0 1 0 0 12 6 6 0 0 0 0-12zm0 10.5a4.5 4.5 0 1 1 0-9 4.5 4.5 0 0 1 0 9z"/>
                    </svg>
                </div>
                <span class="copilot-text">LogInsight</span>
            </div>
            <div class="assistant-message">
                {format_message(ai_message)}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
