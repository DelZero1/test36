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
- Tracks the first 5 messages from newly joined users for moderation review
- Deletes high-confidence spam from tracked new users
- Uses different automatic moderation per chat type:
  - normal groups: delete + English warning
  - supergroups: delete + English warning + escalating mute (24 hours, then 30 days)
- Supports admin reply labeling with `/spam` for missed spam examples
- Supports manual admin moderation commands addressed to the bot:
  - `@bot_username mute`
  - `@bot_username unmute`
  - `@bot_username kick`
  - `@bot_username mute @username`
  - `@bot_username unmute @username`
- Logs moderation actions and admin spam labels to SQLite for later review/export

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

## Moderation Notes

- Automatic spam enforcement only applies to tracked new users during their first 5 messages.
- Manual mute defaults to 1 hour and is available only in supergroups.
- Username-based manual moderation resolves targets from recently stored group messages in SQLite; the bot does not guess identities.
