import uuid

SESSION_FILE = "current_session.txt"

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