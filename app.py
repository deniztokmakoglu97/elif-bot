import streamlit as st
from db import init_db, load_messages
from session import get_or_create_session_id, clear_session_id
from chat import chat


#  ── Streamlit UI ──────────────────────────────────────────────
init_db()
st.title("🤖 Elif")
st.caption("A chatbot with tools")


# Startup — replace the old block
if "session_id" not in st.session_state:
    st.session_state.session_id = get_or_create_session_id()
    st.session_state.history = load_messages(st.session_state.session_id)


for msg in st.session_state.history:
    if msg["role"] == "tool":
        continue
        #with st.chat_message(msg["role"]):
            #st.write(msg["content"])
    if msg["role"] == "assistant" and not msg["content"]:
        continue  # skip empty assistant messages (tool call placeholders)
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Handle new input
user_input = st.chat_input("Ask something...")
if user_input:
    # Show user message immediately
    with st.chat_message("user"):
        st.write(user_input)

    # Get and show response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            reply = chat(user_input)    
        st.write(reply)

with st.sidebar:
    if st.button("Reset chat", type="primary"):
        st.session_state.session_id = clear_session_id()
        st.session_state.history = []
        st.rerun()
    st.subheader("History")
    for msg in st.session_state.history:
        if msg["role"] == "tool":
            with st.expander(f"{msg['role'].capitalize()} used:"):
                st.write(msg["content"])
    num_users = sum(1 for m in st.session_state.history if m["role"] == "user")
    st.metric("Number of chats", num_users, border=True)

        

    

