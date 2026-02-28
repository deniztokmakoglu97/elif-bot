import sqlite3

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