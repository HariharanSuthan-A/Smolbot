from importlib.resources import path
import os
from dotenv import load_dotenv
from datetime import datetime
import requests
import json
import subprocess
import threading
import time

# Langchain modules
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_tavily import TavilySearch
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import Tool

# Google services and tools
from google_services import check_credentials_exist
from langchain_tools import (
    get_recent_emails_tool,
    get_email_content_tool,
    send_email_tool,
    search_emails_tool,
    create_calendar_event_tool,
    list_calendar_events_tool,
    update_calendar_event_tool,
    delete_calendar_event_tool,
    quick_add_event_tool,
    GMAIL_TOOLS,
    CALENDAR_TOOLS
)

# Llama index modules
from llama_index.llms.ollama import Ollama
from llama_index.llms.groq import Groq
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.core import SimpleDirectoryReader
from llama_index.core import Settings
from llama_index.core import VectorStoreIndex


load_dotenv()

# Global variable to track swarm process
swarm_process = None


def _is_real_key(env_name):
    """Check if an env var has a real API key (not a placeholder)."""
    val = os.getenv(env_name, "").strip().strip("'\"")
    if not val or "paste" in val.lower() or "your" in val.lower():
        return False
    return True


if _is_real_key("GROQ_API_KEY"):
    provider = "Groq"
    api_key = os.getenv("GROQ_API_KEY").strip()
    llm = ChatGroq(
        api_key=api_key,
        model=os.getenv("Model"),
    )
elif _is_real_key("OPENAI_API"):
    provider = "OpenAI"
    api_key = os.getenv("OPENAI_API").strip()
    llm = ChatOpenAI(api_key=api_key, model=os.getenv("Model"))
elif _is_real_key("OPENROUTER_API_KEY"):
    provider = "OpenRouter"
    api_key = os.getenv("OPENROUTER_API_KEY").strip()
    llm = ChatOpenAI(
        api_key=api_key,
        model=os.getenv("Model"),
        base_url="https://openrouter.ai/api/v1",
    )
elif _is_real_key("GOOGLE_API_KEY"):
    provider = "Google"
    api_key = os.getenv("GOOGLE_API_KEY").strip()
    llm = ChatGoogleGenerativeAI(api_key=api_key, model=os.getenv("Model"))
else:
    raise ValueError("No valid API key found. Check your .env file.")

print("Using provider:", provider, "|", "Model:", os.getenv("Model"))

# Agent Swarm Mode Configuration
AGENT_SWARM_ENABLED = os.getenv("AGENT_SWARM_ENABLED", "false").lower() == "true"
AGENT_SWARM_PORT = int(os.getenv("AGENT_SWARM_PORT", 5000))
AGENT_SWARM_HOST = os.getenv("AGENT_SWARM_HOST", "localhost")

calendar_file = "calendar_events.json"


def load_events():
    if not os.path.exists(calendar_file):
        return []
    with open(calendar_file, "r") as f:
        return json.load(f)


def save_events(events):
    with open(calendar_file, "w") as f:
        json.dump(events, f, indent=2)


def start_agent_swarm():
    """Start the Agent Swarm mode web interface"""
    global swarm_process
    if swarm_process is None or swarm_process.poll() is not None:
        try:
            swarm_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_swarm_ui")
            swarm_process = subprocess.Popen(
                ["python", "app.py"],
                cwd=swarm_dir,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
            # Give the process a moment to start
            time.sleep(2)
            return f"✅ Agent Swarm mode started at http://{AGENT_SWARM_HOST}:{AGENT_SWARM_PORT}"
        except Exception as e:
            return f"❌ Failed to start Agent Swarm mode: {str(e)}"
    else:
        return "⚠️ Agent Swarm mode is already running"


def stop_agent_swarm():
    """Stop the Agent Swarm mode web interface"""
    global swarm_process
    if swarm_process is not None and swarm_process.poll() is None:
        try:
            swarm_process.terminate()
            swarm_process.wait(timeout=5)
            swarm_process = None
            return "✅ Agent Swarm mode stopped"
        except Exception as e:
            return f"❌ Failed to stop Agent Swarm mode: {str(e)}"
    else:
        return "ℹ️ Agent Swarm mode is not running"


def toggle_agent_swarm():
    """Toggle Agent Swarm mode on/off"""
    global AGENT_SWARM_ENABLED
    # Note: This only changes the in-memory variable, not the .env file
    # For persistence, you would need to update the .env file
    AGENT_SWARM_ENABLED = not AGENT_SWARM_ENABLED
    
    if AGENT_SWARM_ENABLED:
        return start_agent_swarm()
    else:
        return stop_agent_swarm()




# -------- DOCUMENT RAG SETUP --------
DOCUMENTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "documents")
os.makedirs(DOCUMENTS_DIR, exist_ok=True)

# Per-user document index store: { user_id: VectorStoreIndex }
user_doc_indexes = {}


def load_user_document(user_id, file_path):
    """Load a PDF file, build a vector index, and store it for the user."""
    try:
        # Use pypdf directly to extract text (SimpleDirectoryReader doesn't auto-detect PDF reader)
        from pypdf import PdfReader
        from llama_index.core.schema import Document

        reader = PdfReader(file_path)
        documents = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                documents.append(
                    Document(text=text, metadata={"page": i + 1, "source": file_path})
                )

        if not documents:
            return (
                False,
                "❌ Could not extract any text from this PDF. The file may be image-based or empty.",
            )

        Settings.embed_model = OllamaEmbedding(
            model_name="nomic-embed-text:latest", request_timeout=120
        )
        Settings.llm = Groq(model=os.getenv("Model"), api_key=api_key)
        index = VectorStoreIndex.from_documents(documents)
        user_doc_indexes[user_id] = index
        return (
            True,
            f"✅ Document loaded successfully! ({len(documents)} pages)\n\nYou can now ask questions with:\n`from my document <your question>`",
        )

    except Exception as e:
        return False, f"❌ Failed to load document: {str(e)}"


search = TavilySearch(
    tavily_api_key=os.getenv("tavily_api_key"),
    max_results=2,
    search_depth="basic",
    include_answer=True,
)

url = "https://api.duckduckgo.com/"

SYS = """
You are smolagent and a helpful assistant. Your name is smolagent,
 AI assistant with features like chatting, document question-answering, 
 web searching, and file system operations.

"""

prompt = ChatPromptTemplate.from_messages(
    [("system", SYS), MessagesPlaceholder(variable_name="history"), ("human", "{user}")]
)


# searcher_prompt = ChatPromptTemplate.from_messages([
#     ("system","You are a helpful assistant that can search the web using the Tavily Search API. If the user query starts with 'search:', use the search tool to find relevant information and summarize it into 50 words. If the query does not start with 'search:', respond to the user query directly without using the search tool."),
#     ("human","Summarize in 50 words {result}")
# ])


chain = prompt | llm
memory_store = {}
MAX_HISTORY = 10
BASE_DIR = os.getenv(r"Base_dir")  # Default to Documents folder if not set


def ask_agent(user_id, message):
    # Initialize memory for new user
    if user_id not in memory_store:
        memory_store[user_id] = []

    history = memory_store[user_id]

    # -------- SEARCH PATH --------
    if message.startswith("search:"):
        usearch_query = message[len("search:") :].strip()
        # parameters = {
        #     "q": usearch_query,
        #     "format": "json",
        #     "no_html": "1",
        #     "skip_disambig": "1"
        # }

        # response = requests.get(url, params=parameters)
        # data = response.json()
        # return data.get("AbstractText", "No results found.")

        result = search.invoke({"query": usearch_query})

        reply = result["answer"]

        # -------- Calendar Add event --------

    elif message.startswith("Add event"):
        try:
            data = message[len("Add event") :].strip()

            title, time_str = data.split("|")

            title = title.strip()
            time_str = time_str.strip()

            # Parse user format: DD-MM-YYYY HH:MM
            dt = datetime.strptime(time_str, "%d-%m-%Y %H:%M")

            event = {"title": title, "time": dt.strftime("%d-%m-%Y %H:%M")}

            events = load_events()
            events.append(event)
            save_events(events)

            reply = f"✅ Event added:\n{event['title']} at {event['time']}"

        except:
            reply = "Format: Add event <title> | <DD-MM-YYYY HH:MM>"
    # -------- Calender delete event --------
    elif message.startswith("Delete event"):
        try:
            index = int(message.split("Delete event")[1].strip()) - 1

            events = load_events()

            if index < 0 or index >= len(events):
                reply = "❌ Invalid event number."

            else:
                removed = events.pop(index)
                save_events(events)

                reply = f"🗑 Deleted event:\n{removed['title']} — {removed['time']}"

        except:
            reply = "Format: Delete event <event number>"
        # -------- Calender show events--------
    elif message.startswith("Show events"):
        events = load_events()

        if not events:
            reply = "📅 No events scheduled."

        else:
            lines = []
            for i, e in enumerate(events, 1):
                lines.append(f"{i}. {e['title']} — {e['time']}")

            reply = "📅 Upcoming Events:\n\n" + "\n".join(lines)
    # -------- DOCUMENT RAG PATH --------
    elif message.startswith("from my document"):
        doc_query = message[len("from my document") :].strip()

        if user_id not in user_doc_indexes:
            reply = "📄 No document uploaded yet!\nPlease send a PDF file first, then ask questions with:\n`from my document <your question>`"
        elif not doc_query:
            reply = "Please provide a question after 'from my document'.\nExample: `from my document what is the main topic?`"
        else:
            try:
                index = user_doc_indexes[user_id]
                query_engine = index.as_query_engine()
                res = query_engine.query(doc_query)
                reply = res.response
            except Exception as e:
                reply = f"❌ Error querying document: {str(e)}"

    # -------- EMAIL PATH --------
    elif message.startswith("Check email") or message.startswith("Get emails"):
        try:
            # Extract count if specified: "Check email 10" or "Get emails 5"
            parts = message.split()
            count = 5
            if len(parts) > 2 and parts[-1].isdigit():
                count = int(parts[-1])
            reply = get_recent_emails_tool.invoke({"count": count, "query": ""})
        except Exception as e:
            reply = f"❌ Error: {str(e)}"

    elif message.startswith("Read email"):
        # Format: Read email <email_id>
        try:
            email_id = message[len("Read email"):].strip()
            if email_id:
                reply = get_email_content_tool.invoke({"email_id": email_id})
            else:
                reply = "Usage: Read email <email_id>\nUse 'Check email' to get email IDs."
        except Exception as e:
            reply = f"❌ Error: {str(e)}"

    elif message.startswith("Send email"):
        # Format: Send email <to_email> | <subject> | <body>
        try:
            parts = message[len("Send email"):].strip().split("|")
            if len(parts) >= 3:
                to_email = parts[0].strip()
                subject = parts[1].strip()
                body = "|".join(parts[2:]).strip()
                reply = send_email_tool.invoke({
                    "to": to_email,
                    "subject": subject,
                    "body": body
                })
            else:
                reply = "Usage: Send email <to_email> | <subject> | <body>"
        except Exception as e:
            reply = f"❌ Error sending email: {str(e)}"

    elif message.startswith("Search email"):
        # Format: Search email <query>
        try:
            query = message[len("Search email"):].strip()
            if query:
                reply = search_emails_tool.invoke({"query": query, "max_results": 10})
            else:
                reply = "Usage: Search email <gmail_query>\nExample: Search email is:unread from:boss@company.com"
        except Exception as e:
            reply = f"❌ Error: {str(e)}"

    # -------- GOOGLE CALENDAR PATH --------
    elif message.startswith("Create event"):
        # Format: Create event <title> | <start_time> | <end_time> | [description] | [location]
        # Time format: YYYY-MM-DDTHH:MM:SS (ISO format)
        try:
            parts = message[len("Create event"):].strip().split("|")
            if len(parts) >= 3:
                title = parts[0].strip()
                start_time = parts[1].strip()
                end_time = parts[2].strip()
                description = parts[3].strip() if len(parts) > 3 else ""
                location = parts[4].strip() if len(parts) > 4 else ""

                reply = create_calendar_event_tool.invoke({
                    "summary": title,
                    "start_time": start_time,
                    "end_time": end_time,
                    "description": description,
                    "location": location
                })
            else:
                reply = "Usage: Create event <title> | <start_time> | <end_time> | [description] | [location]\nTime format: YYYY-MM-DDTHH:MM:SS"
        except Exception as e:
            reply = f"❌ Error: {str(e)}"

    elif message.startswith("Show calendar") or message.startswith("List calendar"):
        # Format: Show calendar [days] or List calendar [days]
        try:
            parts = message.split()
            days = 7
            if len(parts) > 2 and parts[-1].isdigit():
                days = int(parts[-1])
            reply = list_calendar_events_tool.invoke({"max_results": 10, "days_ahead": days})
        except Exception as e:
            reply = f"❌ Error: {str(e)}"

    elif message.startswith("Quick add event"):
        # Format: Quick add event <natural language description>
        try:
            text = message[len("Quick add event"):].strip()
            if text:
                reply = quick_add_event_tool.invoke({"text": text})
            else:
                reply = "Usage: Quick add event <natural language description>\nExample: Quick add event Meeting with John tomorrow at 3pm"
        except Exception as e:
            reply = f"❌ Error: {str(e)}"

    elif message.startswith("Update event"):
        # Format: Update event <event_id> | [title] | [start_time] | [end_time]
        try:
            parts = message[len("Update event"):].strip().split("|")
            if len(parts) >= 1:
                event_id = parts[0].strip()
                title = parts[1].strip() if len(parts) > 1 else None
                start_time = parts[2].strip() if len(parts) > 2 else None
                end_time = parts[3].strip() if len(parts) > 3 else None

                params = {"event_id": event_id}
                if title:
                    params["summary"] = title
                if start_time:
                    params["start_time"] = start_time
                if end_time:
                    params["end_time"] = end_time

                reply = update_calendar_event_tool.invoke(params)
            else:
                reply = "Usage: Update event <event_id> | [title] | [start_time] | [end_time]"
        except Exception as e:
            reply = f"❌ Error: {str(e)}"

    elif message.startswith("Delete gcal event"):
        # Format: Delete gcal event <event_id>
        try:
            event_id = message[len("Delete gcal event"):].strip()
            if event_id:
                reply = delete_calendar_event_tool.invoke({"event_id": event_id})
            else:
                reply = "Usage: Delete gcal event <event_id>\nUse 'Show calendar' to get event IDs."
        except Exception as e:
            reply = f"❌ Error: {str(e)}"

    # -------- AGENT SWARM MODE PATH --------
    elif message.startswith("Agent swarm"):
        if message.strip().lower() == "agent swarm on":
            reply = start_agent_swarm()
        elif message.strip().lower() == "agent swarm off":
            reply = stop_agent_swarm()
        elif message.strip().lower() == "agent swarm toggle":
            reply = toggle_agent_swarm()
        else:
            reply = "Usage: Agent swarm [on|off|toggle]"

    # -------- FILE SYSTEM PATH --------
    elif message.startswith("List files in"):
        user_path = message[len("List files in"):].strip()
        # Build path relative to BASE_DIR
        ls_query = os.path.abspath(os.path.join(BASE_DIR, user_path))

        try:
            # Security check: prevent leaving BASE_DIR
            if not ls_query.startswith(os.path.abspath(BASE_DIR)):
                reply = "❌ Access denied. You can only browse inside the Documents folder."
            else:
                items = os.listdir(ls_query)
                folders = []
                files = []

                for item in items:
                    full_path = os.path.join(ls_query, item)
                    if os.path.isdir(full_path):
                        folders.append(f"📁 {item}")
                    else:
                        files.append(f"📄 {item}")

                output = ""
                if folders:
                    output += "Folders:\n" + "\n".join(folders) + "\n\n"
                if files:
                    output += "Files:\n" + "\n".join(files)

                reply = output if items else "Directory is empty."
        except Exception as e:
            reply = f"Error: {str(e)}"

    elif message.startswith("Send file"):
        user_path = message[len("Send file"):].strip()
        file_path = os.path.abspath(os.path.join(BASE_DIR, user_path))

        # security check
        if not file_path.startswith(os.path.abspath(BASE_DIR)):
            reply = "❌ Access denied."
            return {"type": "text", "content": reply}

        if not os.path.exists(file_path):
            return {"type": "text", "content": "❌ File not found."}

        return {"type": "file", "path": file_path}

    # -------- LLM CHAT PATH --------
    else:
        res = chain.invoke({
            "history": history,
            "user": message
        })
        reply = res.content


    # -------- SAVE MEMORY --------
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": reply})

    memory_store[user_id] = history[-MAX_HISTORY:]

    return reply
