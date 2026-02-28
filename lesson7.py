import sqlite3
import streamlit as st
import ollama
import math
from datetime import datetime
import random
import json, inspect
import uuid

SESSION_FILE = "current_session.txt"

## 0A. DB initization ##

def init_db():
    with sqlite3.connect('lesson7.db') as conn:
        c = conn.cursor()
        c.execute("""
                CREATE TABLE IF NOT EXISTS elif_chat_history (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
        
        # Create index for faster session retrieval
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_timestamp
            ON elif_chat_history(session_id, timestamp ASC)
        """)
        conn.commit()
        print("Initial table created successfully")
        

def save_message(session_id: str, role: str, content: str, conn=None):
    if conn is None:
        with sqlite3.connect('lesson7.db') as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO elif_chat_history (session_id, role, content)
                VALUES (?, ?, ?)
            """, (session_id, role, content))
            conn.commit()
            print(f"Message saved: {role} - {content}")
    else:
        c = conn.cursor()
        c.execute("""
            INSERT INTO elif_chat_history (session_id, role, content)
            VALUES (?, ?, ?)
        """, (session_id, role, content))
        conn.commit()
        print(f"Message saved: {role} - {content}")
        conn.close()

def load_messages(session_id: str, conn = None):
    if conn is None:
        with sqlite3.connect('lesson7.db') as conn:
            c = conn.cursor()
            c.execute("""
                SELECT role, content FROM elif_chat_history
                WHERE session_id = ?
                ORDER BY timestamp ASC
            """, (session_id,))
            messages = [{"role": row[0], "content": row[1]} for row in c.fetchall()]
            print("Loaded messages:", messages)
            return messages
    else:
        c = conn.cursor()
        c.execute("""
            SELECT role, content FROM elif_chat_history
            WHERE session_id = ?
            ORDER BY timestamp ASC
        """, (session_id,))
        messages = [{"role": row[0], "content": row[1]} for row in c.fetchall()]
        conn.close()
        return messages
    
## 0B. Remember the session ##

def get_or_create_session_id() -> str:
    try:
        with open(SESSION_FILE, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        session_id = str(uuid.uuid4())
        with open(SESSION_FILE, "w") as f:
            f.write(session_id)
        return session_id

def clear_session_id():
    session_id = str(uuid.uuid4())
    with open(SESSION_FILE, "w") as f:
        f.write(session_id)
    return session_id

#### 1. TOOLS FUNCTIONS ###

def get_datetime() -> str:
    return datetime.now().strftime("%d:%m:%Y %H:%M:%S")

def calculate(expression: str) -> str:
    try:
        result = eval(expression, {"__builtins__": {}}, vars(math))
        return str(result)
    except Exception as e:
        return f"Error: {e}"

def flip_coin() -> str:
    return random.choice(["Heads", "Tails"])

def safe_call(fn, fn_args):
    if fn_args is None:
        fn_args = {}
    if isinstance(fn_args, str):
        fn_args = json.loads(fn_args)

    sig = inspect.signature(fn)
    allowed = set(sig.parameters.keys())
    cleaned = {k: v for k, v in fn_args.items() if k in allowed}

    return fn(**cleaned) if cleaned else fn()

#### 2. FUNCTION MAP ###
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_datetime",
            "description": "Get the current time in DD:MM:YY format.",
            "parameters": {"type": "object", "properties": {}, "required": [],   "additionalProperties": False}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluates a math expression. Supports sqrt, sin, cos, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Math expression to evaluate"}
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "flip_coin",
            "description": "Flip a random coin and return Heads or Tails.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    }
]

FUNCTION_MAP = {"get_datetime": get_datetime, "calculate": calculate, "flip_coin": flip_coin}

SYSTEM_PROMPT = f"""You are a chatbot named Elif with access to {list(FUNCTION_MAP.keys())} tools. Only use
the tools when you are explicityly asked to or when the user's question genuinely requires it. Never say you don't have access to something if you have a tool for it.
Always answer the questions in a nice and friendly manner. If a tool is used, use the exact tool result. Don't tell me which tool you used. Don't ever pass an expression to a tool
which it cannot accept."""

def chat(user_message: str) -> str:
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
            messages= [{"role": "system", "content": SYSTEM_PROMPT}, *st.session_state.history],
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
        
# ── Streamlit UI ──────────────────────────────────────────────
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

        

    

