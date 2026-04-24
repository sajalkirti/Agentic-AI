import streamlit as st
# import nbimporter as st
#import self_rag_step7   # imports functions/classes from the notebook
from self_rag_step7  import app
from langchain_core.messages import HumanMessage

# st.session_state -> dict -> 
CONFIG = {'configurable': {'thread_id': 'thread-1'}}

if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

# loading the conversation history
for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.text(message['content'])

#{'role': 'user', 'content': 'Hi'}
#{'role': 'assistant', 'content': 'Hi=ello'}

user_input = st.chat_input('Type here')

if user_input:

    # first add the message to message_history
    st.session_state['message_history'].append({'role': 'user', 'content': user_input})
    with st.chat_message('user'):
        st.text(user_input)
    
    scroll_anchor = st.empty()
    scroll_anchor.markdown("")
    
    initial_state = {
        "question": user_input,
        "retrieval_query": user_input,  # ✅ important
        "rewrite_tries": 0,                                        # ✅ important
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
    with st.spinner("Preparing response..."):
        result = app.invoke(
        initial_state,
        config={"recursion_limit": 80},  # allow revise → verify loops
        )

    ai_message = result.get("answer")
    # first add the message to message_history
    st.session_state['message_history'].append({'role': 'assistant', 'content': ai_message})
    with st.chat_message('assistant'):
        st.text(ai_message)

# # Stream the answer instead of invoking once
#     # Stream directly into the assistant chat bubble
#     with st.chat_message("assistant"):
#         ai_message = st.write_stream(
#             # generator expression: yield only the "answer" strings
#             item["generate_direct"]["answer"]
#             for item in app.stream(
#                 initial_state,
#                 config={"recursion_limit": 80}
#             )
#             if "generate_direct" in item and "answer" in item["generate_direct"]
#         )
    
#     # Save the final concatenated answer into history
#     st.session_state['message_history'].append({
#         "role": "assistant",
#         "content": ai_message
#     })