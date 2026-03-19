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
- tracks post-start joins and stores the first 3 messages from those new users
- classifies risky-looking first messages from tracked new users with BC2-aware moderation logic
- stores classification decisions in SQLite and can post a short in-group warning for strong spam-like messages

## Confirmed Fixes
- Windows event loop compatibility fix added
- Ollama client lifecycle improved (`start()` / `close()`)
- model name mismatch issue identified and corrected through `.env`
- completed the missing new-user moderation plumbing in the database and handlers so tracked joins are inserted once and only the first 3 messages are stored for later review
- added the first moderation phase: deterministic pre-filtering, Ollama JSON spam classification, audit storage, and short warning replies for strong BC2-off-topic promo/spam signals

## Known Limitations
- bot does not yet mute, restrict, or ban users automatically
- moderation classification currently applies only to tracked post-start new users and only during their first 3 messages
- admin reply-based spam labeling is not implemented yet
- spontaneous human-like interjections are not implemented yet
- current bot behavior is mainly triggered-response based

## Last Completed Task
Completed Task 3 by adding BC2-aware moderation for tracked new users: a lightweight deterministic pre-filter decides which of the first 3 messages need review, Ollama returns strict JSON classifications (`CLEAN` / `SUSPICIOUS` / `SPAM`), those decisions are stored in SQLite, and the bot posts a short warning when a message is confidently spam-like.

## Next Planned Task
Continue the new-user moderation pipeline:
- escalate warn -> 24h mute -> 30d mute
- preserve moderation audit data in SQLite for penalties and future review
- add confidence/logging safeguards around automated penalties

## Files Known To Be Stable
- `app.py`
- `bot/config.py`

## Files Likely To Change Next
- `bot/database.py`
- `bot/handlers.py`
- `bot/triggers.py`

## Notes
Any future moderation implementation must preserve existing mention/reply functionality.
