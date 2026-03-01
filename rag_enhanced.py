import re
from pathlib import Path
from collections import defaultdict

import chromadb
from chromadb.utils import embedding_functions

from datetime import datetime

from config import EMBEDDING_MODEL, CHROMA_PATH, COLLECTION_NAME

from typing import List, Tuple

import re

_messages = None


LOW_VALUE_EXACT = {
    "ok", "okay", "okey", "tamam", "tm", "tmm", "k", "kk", "👍", "👌",
    "lol", "lmao", "haha", "ahah", "hahaha", "evet", "aynen"
}
ONLY_EMOJI_RE = re.compile(r'^[\W_]+$')

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

def is_low_value(text: str) -> bool:
    s = text.strip().lower()
    if len(s) <= 2:
        return True
    if s in LOW_VALUE_EXACT:
        return True
    if ONLY_EMOJI_RE.match(s) and len(s) <= 6:
        return True
    return False

def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="paraphrase-multilingual-MiniLM-L12-v2"
    )
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef
    )

def index_messages(messages: list[dict], batch_size: int = 5000):
    collection = get_collection()
    n = len(messages)
    print(f"Indexing {n} messages...")
    total_indexed = 0
    for start in range(0, n, batch_size):
        end = min(start + batch_size, n)

        ids = []
        docs = []
        metas = []
        
        end = min(start + batch_size, n)

        for i in range(start, end):
            text = messages[i]["message"]

            # skip low-value messages
            if is_low_value(text):
                continue


            ids.append(f"msg_{i}")  # keep original index
            docs.append(f"{messages[i]['sender']}: {text}")
            metas.append({
                "i": i,  # IMPORTANT: keep original position for expansion
                "date": messages[i]["date"],
                "time": messages[i]["time"],
                "dt": messages[i]["dt"].isoformat(),
                "sender": messages[i]["sender"],
            })

        # upsert is safer than add
        if ids:
            collection.upsert(ids=ids, documents=docs, metadatas=metas)
            total_indexed += len(ids)

        if start == 0 or end == n or (start // batch_size) % 10 == 0:
            print(f"  processed {end}/{n} | indexed so far: {total_indexed}")

    print("Indexing complete.")

def _merge_ranges(ranges: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """Merge overlapping (start,end) inclusive ranges."""
    if not ranges:
        return []
    ranges = sorted(ranges, key=lambda x: x[0])
    merged = [ranges[0]]
    for s, e in ranges[1:]:
        ps, pe = merged[-1]
        if s <= pe + 1:
            merged[-1] = (ps, max(pe, e))
        else:
            merged.append((s, e))
    return merged

def get_messages():
    global _messages
    if _messages is None:
        _messages = parse_whatsapp("elif_chat.txt")
    return _messages

def retrieve_with_expansion(
    query: str,
    top_k: int = 20,
    window: int = 8,        # ±8 messages around each hit
    max_windows: int = 4    # return at most 4 merged blocks
) -> str:
    collection = get_collection()
    messages = get_messages()  
    # Step 1: retrieve top_k hits
    res = collection.query(
        query_texts=[query],
        n_results=top_k
    )

    res = collection.query(
        query_texts=[query],
        n_results=top_k
    )

    hit_metas = res["metadatas"][0]
    hit_idxs = sorted({int(m["i"]) for m in hit_metas})  # unique indices

     # Step 2: expand each hit into a range
    ranges = []
    n = len(messages)
    for i in hit_idxs:
        s = max(0, i - window)
        e = min(n - 1, i + window)
        ranges.append((s, e))

    merged = _merge_ranges(ranges)

     # Step 3: score windows (simple heuristic: how many hits inside)
    hit_set = set(hit_idxs)
    scored = []
    for (s, e) in merged:
        hit_count = sum(1 for j in range(s, e + 1) if j in hit_set)
        length = (e - s + 1)
        scored.append(((hit_count, -length), (s, e)))  # more hits, shorter is better

    scored.sort(reverse=True)
    best = [rng for _, rng in scored[:max_windows]]

    # Step 4: build context text
    blocks = []
    for (s, e) in best:
        start_dt = messages[s]["dt"].strftime("%d.%m.%Y %H:%M:%S")
        end_dt = messages[e]["dt"].strftime("%d.%m.%Y %H:%M:%S")

        lines = []
        for j in range(s, e + 1):
            m = messages[j]
            # include time for readability
            lines.append(f"[{m['date']} {m['time']}] {m['sender']}: {m['message']}")

        blocks.append(
            f"\n--- Context window ({start_dt} → {end_dt}) ---\n" + "\n".join(lines)
        )

    return "\n".join(blocks)


if __name__ == "__main__":
    #messages = parse_whatsapp("elif_chat.txt")
    #index_messages(messages)

    #chunks = chunk_by_day(messages)
    #print(f"Total messages: {len(messages)}")
    #print(f"Total chunks: {len(chunks)}")
    #index_chunks(chunks)
    print(retrieve_with_expansion("deniz elif düğünü ne zaman?"))
