# Telegram Group AI Bot (Ollama + aiogram v3)

Production-oriented Telegram bot for **group chats only**. It stores all group messages in SQLite and responds only when triggered.

## Features

- Group-only behavior (ignores private chats)
- Persists every group message to SQLite
- Triggered responses only:
  - mention (`@bot_username`)
  - reply to bot
  - `/ask` command
- Context building from recent history
- Summarization when context is large (>30 messages)
- Anti-spam per-group cooldown
- Graceful error handling when Ollama or DB has issues

## Project Structure

```text
.
├── app.py
├── requirements.txt
├── .env.example
├── README.md
└── bot
    ├── __init__.py
    ├── config.py
    ├── database.py
    ├── handlers.py
    ├── memory.py
    ├── ollama_client.py
    ├── prompts.py
    ├── triggers.py
    └── utils.py
```

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Copy environment file:
   ```bash
   cp .env.example .env
   ```
3. Add your Telegram token to `.env` (`TELEGRAM_BOT_TOKEN=...`).
4. Ensure Ollama is running.
5. Pull model:
   ```bash
   ollama pull llama3.1:8b
   ```
6. Run bot:
   ```bash
   python app.py
   ```

## Environment Variables

- `TELEGRAM_BOT_TOKEN`
- `OLLAMA_BASE_URL` (default: `http://localhost:11434`)
- `OLLAMA_MODEL` (default: `llama3.1:8b`)
- `MAX_CONTEXT_MESSAGES` (default: `40`)
- `RESPONSE_COOLDOWN_SECONDS` (default: `10`)
- `OLLAMA_TIMEOUT_SECONDS` (default: `45`)
- `SQLITE_PATH` (default: `bot_memory.db`)
- `MAX_RESPONSE_CHARS` (default: `2000`)
- `LOG_LEVEL` (default: `INFO`)
