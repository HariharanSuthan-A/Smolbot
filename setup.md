# 🚀 SmolBot Setup Guide

Follow these steps to get SmolBot running on any Windows/Mac/Linux machine.

## Prerequisites
- **Python 3.10 to 3.13**: Ensure Python is installed.
- **Tavily API Key**: For web search.
- **LLM API Key**: Groq (recommended), OpenAI, Google, or OpenRouter.
- **Telegram Bot Token**: Get one from [@BotFather](https://t.me/BotFather).
- **Ollama**: Required for document RAG (indexing PDF files).
- **Google API Credentials**: For Gmail and Google Calendar integration (optional).

---

## 🛠️ Installation Steps

### 1. Clone or Download the Project
Make sure you have all the files in a folder (e.g., `smolbot/`).

### 2. Create a Virtual Environment
This keeps the project dependencies isolated and prevents "package errors".

```powershell
# In PowerShell / Command Prompt
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup Ollama (For Document Search)
1. Download Ollama from [ollama.com](https://ollama.com).
2. Run the following command in your terminal to download the embedding model:
   ```bash
   ollama pull nomic-embed-text
   ```

### 5. Configure Your Credentials
Create a file named `.env` in the root folder and add your keys:

```text
Bot_token=your_telegram_bot_token_here
TAVILY_API_KEY=your_tavily_key_here
GROQ_API_KEY=your_groq_key_here
# Optional:
OPENAI_API=...
Model=llama3-70b-8192
```

### 6. Setup Google API (Optional - for Gmail and Calendar)
To use Gmail and Google Calendar features:

1. **Go to Google Cloud Console**: https://console.cloud.google.com/
2. **Create a new project** or select an existing one
3. **Enable the APIs**:
   - Go to "APIs & Services" > "Library"
   - Search and enable:
     - Gmail API
     - Google Calendar API
4. **Create OAuth2 credentials**:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Select "Desktop app" as application type
   - Download the JSON file and rename it to `credentials.json`
   - Place it in your smolbot root folder
5. **First run authentication**:
   - On first run, the bot will open a browser for Google authentication
   - Login with your Google account and grant permissions
   - A `token.json` file will be created for future authentication

**Note**: The first time you use Gmail/Calendar features, you'll need to authenticate via browser.

---

## 🏃 Running the Bot

Once everything is set up, start the bot with:
```bash
python telegram_bot.py
```

---

## ⚠️ Common Issues & Troubleshooting

### "Packages Error" or Installation Failure
- **Python 3.13:** Some libraries like `llama-index` might require basic build tools to compile certain components.
- **Check for the error message:** If it says "Microsoft Visual C++ 14.0 or greater is required", you need to install the [C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/).
- **Update pip first:** `python -m pip install --upgrade pip setuptools wheel`.
- **Try specific versions:** If an error persists, you can try pinning versions in `requirements.txt`, such as `llama-index==0.11.0`.
- **Verify activation:** Always ensure you have activated your virtual environment (`venv`).

### Bot Not Responding
- Check if the `.env` file has the correct `Bot_token`.
- Ensure your internet connection is active.
- Check the console/terminal for any error messages in red.
