# PROGRESS.md

## Project Status
Active

## Current Working State
The bot currently:
- starts successfully on Windows
- uses aiogram v3 polling
- connects to local Ollama
- stores group messages in SQLite
- responds to:
  - mentions
  - replies to bot
  - `/ask`
- supports recent-context building
- supports summarization for large context
- includes per-group cooldown

## Confirmed Fixes
- Windows event loop compatibility fix added
- Ollama client lifecycle improved (`start()` / `close()`)
- model name mismatch issue identified and corrected through `.env`
- completed the missing new-user moderation plumbing in the database and handlers so tracked joins are inserted once and only the first 3 messages are stored for later review

## Known Limitations
- bot does not yet perform autonomous moderation
- bot tracks only post-start joins and the first 3 text messages; no spam classification actions are applied yet
- admin reply-based spam labeling is not implemented yet
- spontaneous human-like interjections are not implemented yet
- current bot behavior is mainly triggered-response based

## Last Completed Task
Completed the previously incomplete moderation data-capture step by fixing the required `new_users` database helpers, aligning `new_user_messages` storage with the intended schema, and wiring join/message tracking into the handlers without changing the existing reply flow.

## Next Planned Task
Continue the new-user moderation pipeline:
- classify the stored first 3 messages for spam/promo intent
- escalate warn -> 24h mute -> 30d mute
- preserve moderation audit data in SQLite

## Files Known To Be Stable
- `app.py`
- `bot/config.py`
- `bot/ollama_client.py`

## Files Likely To Change Next
- `bot/database.py`
- `bot/handlers.py`
- `bot/prompts.py`
- `bot/triggers.py`

## Notes
Any future moderation implementation must preserve existing mention/reply functionality.
