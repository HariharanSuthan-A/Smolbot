# 🤖 SmolBot

**Your compact, multi-talented AI assistant — right inside Telegram.**

SmolBot is a personal AI assistant that lives in your Telegram chats. It's designed to be small in name but big in what it can do. Think of it as that one friend who's always ready to help — whether you need a quick answer, want to look something up on the web, or need to dig through a PDF without opening it yourself.

---

## What Can SmolBot Do?

### 💬 Chat with AI
Just send a normal text message — no commands, no prefixes needed. SmolBot will respond naturally, powered by your choice of LLM provider. It remembers your recent conversation so the chat flows without losing context.

### 🔍 Web Search
Need to find something online? Start your message with `search:` followed by your query, and SmolBot will search the web using Tavily and bring back a concise answer.

**Example:** `search: latest news on AI regulations`

### 📄 Document Q&A (RAG)
Send a PDF file directly in Telegram, and SmolBot will read, understand, and index it. Then ask questions about it naturally.

- **Upload:** Attach a PDF file into the chat.
- **Ask:** Type `from my document` followed by your question.

**Example:** `from my document what are the key findings?`

### 📅 Calendar — Manage Events
SmolBot can keep track of your events — a simple, no-fuss personal calendar.

| Action | Command |
|---|---|
| Add an event | `Add event Team standup | 25-03-2026 09:00` |
| Show all events | `Show events` |
| Delete an event | `Delete event 1` (by event number) |

### 📂 File System
SmolBot can browse directories and send files to you over Telegram.

| Action | Command |
|---|---|
| Browse files | `List files in <folder>` |
| Download a file | `Send file <file>` |

---

## Quick Reference

| Capability | Command |
|---|---|
| Web search | `search: <query>` |
| Document Q&A | `from my document <question>` |
| Browse files | `List files in <folder>` |
| Download file | `Send file <file>` |
| Add event | `Add event <title> \| <DD-MM-YYYY HH:MM>` |
| Show events | `Show events` |
| Delete event | `Delete event <number>` |
| Chat | Just type normally |

---

## Supported File Types via Telegram

SmolBot can send you almost any file type through Telegram:

- 📄 PDF
- 📝 TXT
- 🖼️ Images
- 📦 ZIP
- 💻 Code files
- 📊 CSV
- 📋 JSON

**Max upload size:** 50 MB

---

## Supported LLM Providers

Set your API key in the `.env` file and SmolBot automatically picks the right one:

| Provider | Env Variable |
|---|---|
| **Groq** | `GROQ_API_KEY` |
| **OpenAI** | `OPENAI_API` |
| **OpenRouter** | `OPENROUTER_API_KEY` |
| **Google** | `GOOGLE_API_KEY` |

The model is set via the `Model` variable in `.env`.

---

## Tech Under the Hood

- **LangChain** — orchestrates the LLM chat pipeline with conversation memory
- **LlamaIndex** — powers the document RAG (indexing, embedding, querying)
- **Ollama** — runs local embeddings (`nomic-embed-text`) for document indexing
- **Tavily** — provides web search results
- **pypdf** — extracts text content from uploaded PDFs
- **python-telegram-bot** — connects everything to Telegram

---

*SmolBot — lightweight, focused, and genuinely useful. No bloat, just the tools you need, one Telegram message away.* ✨
