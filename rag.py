import re
from pathlib import Path
from collections import defaultdict

import chromadb
from chromadb.utils import embedding_functions

from config import EMBEDDING_MODEL, CHROMA_PATH, COLLECTION_NAME

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
    Parses WhatsApp export into list of:
    {"date": "8.08.2024", "sender": "xx", "message": "xx"}
    """
    sender1, sender2 = get_senders(filepath)
    messages = []
    pattern = re.compile(r'^\[(\d{1,2}\.\d{2}\.\d{4}), \d{2}:\d{2}:\d{2}\] (.+?): (.+)$')
    
    skip_phrases = ["image omitted", "video omitted", "audio omitted", 
                    "sticker omitted", "GIF omitted", "document omitted",
                    "end-to-end encrypted"]
    
    current = None
    
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            match = pattern.match(line)
            
            if match:
                date, sender, message = match.groups()
                
                # Skip system messages and media
                if any(phrase in message for phrase in skip_phrases):
                    continue
                
                # Normalize sender name
                if sender1 in sender:
                    sender = sender1
                else:
                    sender = sender2
                
                current = {"date": date, "sender": sender, "message": message}
                messages.append(current)
            
            elif current and line:
                # Continuation of previous message
                current["message"] += " " + line
    
    return messages

def chunk_by_day(messages: list[dict]) -> list[dict]:
    """
    Groups messages by date into chunks.
    Returns list of {"date": "8.08.2024", "text": "Sender1: message\\Sender2: message..."}
    """

    days = defaultdict(list)
    
    for msg in messages:
        days[msg["date"]].append(f"{msg['sender']}: {msg['message']}")
    
    chunks = []
    for date, lines in days.items():
        chunks.append({
            "date": date,
            "text": "\n".join(lines)
        })
    
    return chunks

def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="paraphrase-multilingual-MiniLM-L12-v2"
    )
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef
    )

def index_chunks(chunks: list[dict]):
    collection = get_collection()
    
    # Skip if already indexed
    if collection.count() > 0:
        print(f"Already indexed {collection.count()} chunks. Skipping.")
        return
    
    print(f"Indexing {len(chunks)} chunks...")
    
    collection.add(
        ids=[f"day_{i}" for i in range(len(chunks))],
        documents=[c["text"] for c in chunks],
        metadatas=[{"date": c["date"]} for c in chunks]
    )
    
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
