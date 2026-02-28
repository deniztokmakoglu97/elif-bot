import ollama
import streamlit as st
from db import save_message
from tools import FUNCTION_MAP, TOOLS, safe_call
from config import SYSTEM_PROMPT
from rag import retrieve

def chat(user_message: str) -> str:
    context = retrieve(user_message)
    augmented_SYSTEM = SYSTEM_PROMPT + f"""
    [Relevant context from Elif and Deniz's chat history:]
    {context}"""
    st.session_state.history.append(
        {"role": "user", "content": user_message}
        )
    save_message(
                session_id=st.session_state.session_id,
                role="user",
                content=user_message
                )   
    
    

    while True:

        response = ollama.chat(
            model="llama3.1",
            messages= [{"role": "system", "content": augmented_SYSTEM}, *st.session_state.history],
            tools=TOOLS
        )

        if response["message"].get("tool_calls", None):
            # if tool call
            tool_calls = response["message"]["tool_calls"]
            print(tool_calls)
            st.session_state.history.append({"role": "assistant", "content": response["message"]["content"]})

            for tool_call in tool_calls:
                fn_name = tool_call["function"]["name"]
                fn_args = tool_call["function"]["arguments"]

                print(f"Calling function: {fn_name} with arguments: {fn_args}")

                fn = FUNCTION_MAP.get(fn_name, None)
                if fn is not None:
                    result = safe_call(fn, fn_args)
                
                st.session_state.history.append({"role": "tool", "content": result})
        
        else:
            reply = response["message"]["content"]
            st.session_state.history.append({"role": "assistant", "content": reply})
            save_message(
                session_id=st.session_state.session_id,
                role="assistant",
                content=reply
                )   
            return reply