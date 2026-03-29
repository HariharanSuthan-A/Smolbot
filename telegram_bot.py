from telegram import Update
import os
from datetime import datetime
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters
)


import json
from smolbot import ask_agent, load_user_document, DOCUMENTS_DIR

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

    await update.message.reply_text("\u23f3 Downloading and processing your document... This may take a moment.")

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

        event = {
            "title": title.strip(),
            "time": event_time.strftime("%d-%m-%Y %H:%M")
        }

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
        await update.message.reply_text(
            "Usage:\n/delete_event <event_number>"
        )
        return

    try:
        index = int(context.args[0]) - 1
        events = load_events()

        removed = events.pop(index)
        save_events(events)

        await update.message.reply_text(
            f"🗑 Deleted event: {removed['title']}"
        )

    except:
        await update.message.reply_text("Invalid event number.")

# -----------------------------
# MAIN
# -----------------------------
def main():

    print("Bot started...")

    app = ApplicationBuilder().token(BOT_TOKEN).connect_timeout(10).read_timeout(30).build()

    # Document upload (PDF)
    app.add_handler(MessageHandler(filters.Document.PDF, handle_document))

    # AI chat
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # filesystem
    app.add_handler(CommandHandler("ls", list_files))

    # calendar
    app.add_handler(CommandHandler("add_event", add_event))
    app.add_handler(CommandHandler("events", list_events))
    app.add_handler(CommandHandler("delete_event", delete_event))

    # run_polling() is synchronous — it manages its own event loop
    app.run_polling()


if __name__ == "__main__":
    main()