# 🤖 Elif — A Personal AI Chatbot

Elif is a personal AI chatbot built with [Streamlit](https://streamlit.io/) and a locally-running LLM via [Ollama](https://ollama.com/). It remembers past conversations using a SQLite database and can answer questions about shared memories by retrieving context from an indexed WhatsApp chat history using RAG (Retrieval-Augmented Generation). Elif also has access to real-time tools like weather lookups, web search, and a calculator.

---

## Features

- **Conversational memory** — chat history is persisted in SQLite across sessions
- **WhatsApp RAG** — parses and indexes a WhatsApp chat export, then retrieves relevant context to answer personal questions
- **Enhanced RAG** — uses query expansion and context windowing for more coherent retrieved passages
- **Real-time tools** — weather (OpenWeatherMap), web search (Tavily), calculator, current datetime, and coin flip
- **Multilingual** — responds in Turkish or English depending on how you write
- **Local LLM** — runs on `qwen2.5:14b` via Ollama; no data sent to external AI providers
- **Clean Streamlit UI** — session reset, chat history sidebar, and tool-use log

---

## Project Structure

```
elif-bot/
├── app.py              # Streamlit UI entry point
├── chat.py             # Main chat loop — calls Ollama, handles tool calls
├── config.py           # Model settings, system prompt, API keys
├── db.py               # SQLite helpers (init, save, load messages)
├── session.py          # Session ID management (file-based persistence)
├── tools.py            # Tool definitions and function map
├── rag.py              # Basic WhatsApp parser + day-chunked ChromaDB indexing
├── rag_enhanced.py     # Enhanced parser with message-level indexing + context windowing
├── requirements.txt    # Python dependencies
└── lesson7.py          # (scratch/learning file)
```

---

## Setup

### 1. Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com/) installed and running locally
- The `qwen2.5:14b` model pulled:

```bash
ollama pull qwen2.5:14b
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

The `requirements.txt` lists `ollama` and `streamlit`. You'll also need to install the remaining dependencies used in the project:

```bash
pip install chromadb sentence-transformers tavily-python requests python-dotenv
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
OPENWEATHER_API_KEY=your_openweather_api_key
TAVILY_API_KEY=your_tavily_api_key
```

### 4. Add your WhatsApp chat export (optional)

Export a WhatsApp conversation and save it as `elif_chat.txt` in the project root. The file should be in standard WhatsApp export format:

```
[8.08.2024, 21:10:03] User1: Hey!
[8.08.2024, 21:10:15] User2: Hi! 😊
```

Then index it by running:

```bash
python rag_enhanced.py
```

This creates a persistent ChromaDB vector store at `./chroma_db/`.

### 5. Run the app

```bash
streamlit run app.py
```

---

## How It Works

1. **User sends a message** — the input is embedded and used to retrieve relevant passages from the WhatsApp chat history via ChromaDB.
2. **Context is injected** — the retrieved passages are appended to the system prompt so the model can reference real memories naturally.
3. **Ollama generates a response** — if the model decides to call a tool (e.g. weather or web search), the tool result is fed back in and generation continues.
4. **Response is saved** — the final reply is stored in SQLite under the current session ID.

---

## Available Tools

| Tool | Description |
|---|---|
| `get_datetime` | Returns the current date and time |
| `calculate` | Evaluates a math expression (supports `sqrt`, `sin`, `cos`, etc.) |
| `flip_coin` | Returns Heads or Tails |
| `get_weather` | Gets current weather for a given city via OpenWeatherMap |
| `search_web` | Searches the web via Tavily and returns top results |

---

## Configuration

Key settings live in `config.py`:

| Variable | Default | Description |
|---|---|---|
| `MODEL` | `qwen2.5:14b` | Ollama model to use |
| `EMBEDDING_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | Sentence transformer for RAG |
| `CHROMA_PATH` | `chroma_db` | Path to the ChromaDB vector store |
| `COLLECTION_NAME` | `elif_chats_v2` | ChromaDB collection name |

---

## Notes

- The app uses file-based session tracking (`current_session.txt`). Clicking **Reset chat** generates a new session ID, starting a fresh conversation while preserving history in the database.
- Tool results are shown in the sidebar under **History** as collapsible expanders.
- The RAG enhanced retriever (`rag_enhanced.py`) indexes individual messages and expands each hit with ±8 surrounding messages for conversational context, then returns the top 4 most relevant windows.
