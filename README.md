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
| Add an event (Legacy) | `Add event Team standup | 25-03-2026 09:00` |
| Show all events (Legacy) | `Show events` |
| Delete an event (Legacy) | `Delete event 1` (by event number) |

### 📧 Gmail — Read and Send Emails
With Google OAuth integration, SmolBot can access your Gmail to check, read, and send emails.

| Action | Command |
|---|---|
| Check recent emails | `Check email 5` or `Get emails 10` |
| Read specific email | `Read email <email_id>` |
| Send email | `Send email to@example.com | Subject | Body text` |
| Search emails | `Search email is:unread from:boss@company.com` |

### 📅 Google Calendar — Schedule Events
Create, view, and manage events in your Google Calendar.

| Action | Command |
|---|---|
| List upcoming events | `Show calendar 7` or `List calendar` |
| Create event | `Create event Meeting | 2024-01-15T10:00:00 | 2024-01-15T11:00:00 | Description | Location` |
| Quick add event | `Quick add event Meeting with John tomorrow at 3pm` |
| Update event | `Update event <event_id> | New Title | 2024-01-15T14:00:00` |
| Delete event | `Delete gcal event <event_id>` |

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
| Add event (Legacy) | `Add event <title> \| <DD-MM-YYYY HH:MM>` |
| Show events (Legacy) | `Show events` |
| Delete event (Legacy) | `Delete event <number>` |
| **Check Gmail** | `Check email [count]` or `Get emails [count]` |
| **Read Email** | `Read email <email_id>` |
| **Send Email** | `Send email <to> \| <subject> \| <body>` |
| **Search Email** | `Search email <query>` |
| **Create Calendar Event** | `Create event <title> \| <start> \| <end> \| [desc] \| [location]` |
| **Show Calendar** | `Show calendar [days]` or `List calendar [days]` |
| **Quick Add Event** | `Quick add event <natural language>` |
| **Update Event** | `Update event <event_id> \| [title] \| [start] \| [end]` |
| **Delete Calendar Event** | `Delete gcal event <event_id>` |
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
