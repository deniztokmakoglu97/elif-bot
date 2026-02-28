import re
from pathlib import Path
from collections import defaultdict

import chromadb
from chromadb.utils import embedding_functions

from datetime import datetime

from config import EMBEDDING_MODEL, CHROMA_PATH, COLLECTION_NAME

from typing import List, Tuple

LINE_RE = re.compile(
    r'^\[(\d{1,2}\.\d{2}\.\d{4}), (\d{2}:\d{2}:\d{2})\] (.+?): (.+)$'
)
SKIP_PHRASES = ["image omitted", "video omitted", "audio omitted", 
                    "sticker omitted", "GIF omitted", "document omitted",
                    "end-to-end encrypted"]

def get_senders(filepath: str) -> tuple[str, str]:
    """Returns the two sender names found in the chat."""
    pattern = re.compile(r'^\[(\d{1,2}\.\d{2}\.\d{4}), \d{2}:\d{2}:\d{2}\] (.+?): (.+)$')
    senders = []

    with open(filepath, encoding="utf-8") as f:
        for line in f:
            match = pattern.match(line.strip())
            if match:
                sender = match.group(2)
                if sender not in senders and "end-to-end" not in match.group(3):
                    senders.append(sender)
            if len(senders) == 2:
                break

    return senders[0], senders[1]

def parse_whatsapp(filepath: str) -> list[dict]:
    """
    Returns list of:
        {
        "dt": datetime,
        "date": "8.08.2024",
        "time": "21:10:03",
        "sender": "xx",
        "message": "..."
        }
    """
    sender1, sender2 = get_senders(filepath)
    messages = []
    current = None    

    with open(filepath, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            m = LINE_RE.match(line)

            
            if m:
                date_str, time_str, sender, message = m.groups()
                low = message.lower()
                # Skip system messages and media
                if any(phrase in low for phrase in SKIP_PHRASES):
                    continue

                dt = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M:%S")
                # Normalize sender name
                if sender1 in sender.strip():
                    sender = sender1
                else:
                    sender = sender2
                
                current = {
                    "dt": dt,
                    "date": date_str,
                    "time": time_str,
                    "sender": sender,
                    "message": message.strip(),
                }
                messages.append(current)
            
            elif current and line:
                # Continuation of previous message
                current["message"] += " " + line

    # Ensure chronological
    messages.sort(key=lambda x: x["dt"])
    return messages

def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="paraphrase-multilingual-MiniLM-L12-v2"
    )
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef
    )

def index_messages(messages: list[dict]):
    collection = get_collection()

    
    # Skip if already indexed
    if collection.count() > 0:
        print(f"Already indexed {collection.count()} chunks. Skipping.")
        return
    
    ids = []
    docs = []
    metas = []

    for i, msg in enumerate(messages):
        # Make the doc text small and explicit
        doc = f"{msg['sender']}: {msg['message']}"
        ids.append(f"msg_{i}")
        docs.append(doc)
        metas.append({
            "i": i,
            "date": msg["date"],
            "time": msg["time"],
            "dt": msg["dt"].isoformat(),
            "sender": msg["sender"],
        })

    print(f"Indexing {len(ids)} messages...")
    collection.add(ids=ids, documents=docs, metadatas=metas)
    print("Indexing complete.")

def retrieve(query: str, n_results: int = 3) -> str:
    """
    Finds the most relevant chat chunks for a given query.
    Returns them as a single string to inject into the prompt.
    """
    collection = get_collection()
    
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    
    chunks = results["documents"][0]
    dates = [m["date"] for m in results["metadatas"][0]]
    
    context = ""
    for date, chunk in zip(dates, chunks):
        context += f"\n--- {date} ---\n{chunk}\n"
    
    return context


if __name__ == "__main__":
    #messages = parse_whatsapp("elif_chat.txt")
    #chunks = chunk_by_day(messages)
    #print(f"Total messages: {len(messages)}")
    #print(f"Total chunks: {len(chunks)}")
    #index_chunks(chunks)
    print(retrieve("deniz elif düğünü ne zaman?"))
