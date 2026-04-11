from telegram import Update
import os
from datetime import datetime
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)
import json

from smolbot import ask_agent, load_user_document, DOCUMENTS_DIR
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
    quick_add_event_tool
)

BOT_TOKEN = os.getenv("Bot_token")

print("Starting Telegram bot...")

# -----------------------------
# CALENDAR STORAGE
# -----------------------------
CALENDAR_FILE = "calendar_events.json"


def load_events():
    if not os.path.exists(CALENDAR_FILE):
        return []
    with open(CALENDAR_FILE, "r") as f:
        return json.load(f)


def save_events(events):
    with open(CALENDAR_FILE, "w") as f:
        json.dump(events, f, indent=2)


# -----------------------------
# DOCUMENT UPLOAD HANDLER
# -----------------------------
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle PDF files uploaded by the user."""
    document = update.message.document
    user_id = update.message.from_user.id

    # Only accept PDF files
    if not document.file_name.lower().endswith(".pdf"):
        await update.message.reply_text(
            "\u274c Only PDF files are supported.\nPlease send a .pdf file."
        )
        return

    await update.message.reply_text(
        "\u23f3 Downloading and processing your document... This may take a moment."
    )

    try:
        # Download the file from Telegram
        file = await context.bot.get_file(document.file_id)
        file_path = os.path.join(DOCUMENTS_DIR, f"{user_id}_{document.file_name}")
        await file.download_to_drive(file_path)

        # Index the document for RAG
        success, message = load_user_document(user_id, file_path)
        await update.message.reply_text(message)

    except Exception as e:
        await update.message.reply_text(f"\u274c Error processing document: {str(e)}")


# -----------------------------
# AI CHAT HANDLER
# -----------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    user_id = update.message.from_user.id

    result = ask_agent(user_id, user_message)

    if isinstance(result, dict) and result.get("type") == "file":
        file_path = result["path"]

        with open(file_path, "rb") as f:
            await update.message.reply_document(document=f)

    else:
        await update.message.reply_text(result)


# -----------------------------
# LIST FILES COMMAND
# -----------------------------
async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage:\n/ls <directory_path>\nExample:\n/ls C:\\Users\\Hari\\Documents"
        )
        return

    directory = " ".join(context.args)

    try:
        items = os.listdir(directory)

        folders = []
        files = []

        for item in items:
            full_path = os.path.join(directory, item)

            if os.path.isdir(full_path):
                folders.append(f"📁 {item}")
            else:
                files.append(f"📄 {item}")

        output = f"📂 Directory: {directory}\n\n"

        if folders:
            output += "Folders:\n" + "\n".join(folders) + "\n\n"

        if files:
            output += "Files:\n" + "\n".join(files)

        if not items:
            output += "Directory is empty."

        if len(output) > 4000:
            output = output[:4000]

        await update.message.reply_text(output)

    except Exception as e:
        await update.message.reply_text(f"Error:\n{str(e)}")


# -----------------------------
# ADD CALENDAR EVENT
# -----------------------------


async def add_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.replace("Add event", "").strip()

    try:
        title, time_str = text.split("|")

        # Parse date in DD-MM-YYYY HH:MM format
        event_time = datetime.strptime(time_str.strip(), "%d-%m-%Y %H:%M")

        event = {"title": title.strip(), "time": event_time.strftime("%d-%m-%Y %H:%M")}

        events = load_events()
        events.append(event)
        save_events(events)

        await update.message.reply_text(
            f"✅ Event added:\n{event['title']} at {event['time']}"
        )

    except Exception as e:
        await update.message.reply_text(
            "Usage:\n/add_event <title> | <DD-MM-YYYY HH:MM>\n\nExample:\n/add_event Team meeting | 23-10-2026 10:00"
        )


# -----------------------------
# LIST EVENTS
# -----------------------------
async def list_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    events = load_events()

    if not events:
        await update.message.reply_text("📅 No events scheduled.")
        return

    msg = "📅 Upcoming Events\n\n"

    for i, e in enumerate(events, 1):
        msg += f"{i}. {e['title']} — {e['time']}\n"

    await update.message.reply_text(msg)


# -----------------------------
# DELETE EVENT
# -----------------------------
async def delete_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage:\n/delete_event <event_number>")
        return

    try:
        index = int(context.args[0]) - 1
        events = load_events()

        removed = events.pop(index)
        save_events(events)

        await update.message.reply_text(f"🗑 Deleted event: {removed['title']}")

    except:
        await update.message.reply_text("Invalid event number.")


# -----------------------------
# GOOGLE CALENDAR COMMANDS
# -----------------------------
async def gcal_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List upcoming Google Calendar events."""
    if not check_credentials_exist():
        await update.message.reply_text(
            "❌ Google credentials not configured.\n"
            "Please set up credentials.json file."
        )
        return

    try:
        days = 7
        if context.args:
            try:
                days = int(context.args[0])
            except ValueError:
                pass

        result = list_calendar_events_tool.invoke({
            "max_results": 10,
            "days_ahead": days
        })
        await update.message.reply_text(result)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def gcal_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a new Google Calendar event."""
    if not check_credentials_exist():
        await update.message.reply_text(
            "❌ Google credentials not configured.\n"
            "Please set up credentials.json file."
        )
        return

    if not context.args:
        await update.message.reply_text(
            "Usage:\n"
            "/gcal_create <title> | <start_time> | <end_time> | [description] | [location]\n\n"
            "Time format: YYYY-MM-DDTHH:MM:SS\n\n"
            "Example:\n"
            "/gcal_create Team Meeting | 2024-01-15T10:00:00 | 2024-01-15T11:00:00 | Weekly sync | Conference Room A"
        )
        return

    try:
        text = " ".join(context.args)
        parts = text.split("|")

        if len(parts) < 3:
            await update.message.reply_text("❌ Please provide at least title, start time, and end time separated by |")
            return

        title = parts[0].strip()
        start_time = parts[1].strip()
        end_time = parts[2].strip()
        description = parts[3].strip() if len(parts) > 3 else ""
        location = parts[4].strip() if len(parts) > 4 else ""

        result = create_calendar_event_tool.invoke({
            "summary": title,
            "start_time": start_time,
            "end_time": end_time,
            "description": description,
            "location": location
        })
        await update.message.reply_text(result)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def gcal_quickadd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick add event using natural language."""
    if not check_credentials_exist():
        await update.message.reply_text(
            "❌ Google credentials not configured.\n"
            "Please set up credentials.json file."
        )
        return

    if not context.args:
        await update.message.reply_text(
            "Usage:\n"
            "/gcal_quickadd <natural language description>\n\n"
            "Example:\n"
            "/gcal_quickadd Meeting with John tomorrow at 3pm\n"
            "/gcal_quickadd Lunch next Friday at noon"
        )
        return

    try:
        text = " ".join(context.args)
        result = quick_add_event_tool.invoke({"text": text})
        await update.message.reply_text(result)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def gcal_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a Google Calendar event."""
    if not check_credentials_exist():
        await update.message.reply_text(
            "❌ Google credentials not configured.\n"
            "Please set up credentials.json file."
        )
        return

    if not context.args:
        await update.message.reply_text(
            "Usage:\n"
            "/gcal_delete <event_id>\n\n"
            "Use /gcal_list to get event IDs."
        )
        return

    try:
        event_id = context.args[0]
        result = delete_calendar_event_tool.invoke({"event_id": event_id})
        await update.message.reply_text(result)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


# -----------------------------
# GMAIL COMMANDS
# -----------------------------
async def gmail_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check recent emails."""
    if not check_credentials_exist():
        await update.message.reply_text(
            "❌ Google credentials not configured.\n"
            "Please set up credentials.json file."
        )
        return

    try:
        count = 5
        if context.args:
            try:
                count = int(context.args[0])
            except ValueError:
                pass

        result = get_recent_emails_tool.invoke({
            "count": count,
            "query": ""
        })
        await update.message.reply_text(result)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def gmail_read(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Read a specific email."""
    if not check_credentials_exist():
        await update.message.reply_text(
            "❌ Google credentials not configured.\n"
            "Please set up credentials.json file."
        )
        return

    if not context.args:
        await update.message.reply_text(
            "Usage:\n"
            "/gmail_read <email_id>\n\n"
            "Use /gmail_check to get email IDs."
        )
        return

    try:
        email_id = context.args[0]
        result = get_email_content_tool.invoke({"email_id": email_id})
        await update.message.reply_text(result)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def gmail_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send an email."""
    if not check_credentials_exist():
        await update.message.reply_text(
            "❌ Google credentials not configured.\n"
            "Please set up credentials.json file."
        )
        return

    if not context.args:
        await update.message.reply_text(
            "Usage:\n"
            "/gmail_send <to_email> | <subject> | <body>\n\n"
            "Example:\n"
            "/gmail_send john@example.com | Hello | This is a test email."
        )
        return

    try:
        text = " ".join(context.args)
        parts = text.split("|")

        if len(parts) < 3:
            await update.message.reply_text("❌ Please provide to_email, subject, and body separated by |")
            return

        to_email = parts[0].strip()
        subject = parts[1].strip()
        body = "|".join(parts[2:]).strip()

        result = send_email_tool.invoke({
            "to": to_email,
            "subject": subject,
            "body": body
        })
        await update.message.reply_text(result)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def gmail_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search emails."""
    if not check_credentials_exist():
        await update.message.reply_text(
            "❌ Google credentials not configured.\n"
            "Please set up credentials.json file."
        )
        return

    if not context.args:
        await update.message.reply_text(
            "Usage:\n"
            "/gmail_search <gmail_query>\n\n"
            "Examples:\n"
            "/gmail_search is:unread\n"
            "/gmail_search from:boss@company.com\n"
            "/gmail_search subject:meeting"
        )
        return

    try:
        query = " ".join(context.args)
        result = search_emails_tool.invoke({
            "query": query,
            "max_results": 10
        })
        await update.message.reply_text(result)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


# -----------------------------
# MAIN
# -----------------------------
def main():
    print("Bot started...")

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .connect_timeout(30)
        .read_timeout(60)
        .write_timeout(60)
        .build()
    )

    # Document upload (PDF)
    app.add_handler(MessageHandler(filters.Document.PDF, handle_document))

    # AI chat
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # filesystem
    app.add_handler(CommandHandler("ls", list_files))

    # calendar (legacy JSON-based)
    app.add_handler(CommandHandler("add_event", add_event))
    app.add_handler(CommandHandler("events", list_events))
    app.add_handler(CommandHandler("delete_event", delete_event))

    # Google Calendar
    app.add_handler(CommandHandler("gcal_list", gcal_list))
    app.add_handler(CommandHandler("gcal_create", gcal_create))
    app.add_handler(CommandHandler("gcal_quickadd", gcal_quickadd))
    app.add_handler(CommandHandler("gcal_delete", gcal_delete))

    # Gmail
    app.add_handler(CommandHandler("gmail_check", gmail_check))
    app.add_handler(CommandHandler("gmail_read", gmail_read))
    app.add_handler(CommandHandler("gmail_send", gmail_send))
    app.add_handler(CommandHandler("gmail_search", gmail_search))

    # run_polling() is synchronous — it manages its own event loop
    app.run_polling()


if __name__ == "__main__":
    main()
