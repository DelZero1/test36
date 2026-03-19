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
- tracks post-start joins and stores the first 5 messages from those new users
- classifies risky-looking first messages from tracked new users with BC2-aware moderation logic
- stores classification decisions in SQLite and now escalates high-confidence spam with message deletion, warning notices, and timed mutes

## Confirmed Fixes
- Windows event loop compatibility fix added
- Ollama client lifecycle improved (`start()` / `close()`)
- model name mismatch issue identified and corrected through `.env`
- completed the missing new-user moderation plumbing in the database and handlers so tracked joins are inserted once and only the first 3 messages are stored for later review
- added the first moderation phase: deterministic pre-filtering, Ollama JSON spam classification, audit storage, and short warning replies for strong BC2-off-topic promo/spam signals
- fixed the spam classification prompt template so literal JSON braces are escaped for Python `.format()`, and added defensive logging/early return if prompt building ever fails again
- expanded new-user moderation to the first 5 messages and added enforcement escalation: delete spam, warn in English, mute 24 hours on the first offense, and mute 30 days on repeated offenses while skipping admins and bots

## Known Limitations
- moderation classification still applies only to tracked post-start new users and only during their first 5 messages
- automated enforcement is currently limited to high-confidence `SPAM` classifications and does not yet escalate beyond a 30-day mute
- admin reply-based spam labeling is not implemented yet
- spontaneous human-like interjections are not implemented yet
- current bot behavior is mainly triggered-response based

## Last Completed Task
Implemented the first enforcement layer for new users: moderation now reviews up to 5 tracked messages, deletes high-confidence spam, warns in English, and escalates mutes from 24 hours to 30 days while preserving audit metadata in SQLite.

## Next Planned Task
Continue the new-user moderation pipeline:
- add admin reply-based spam labeling
- keep enriching moderation audit data for future review and training export
- add more moderation logging and trusted-user safeguards

## Files Known To Be Stable
- `app.py`
- `bot/config.py`

## Files Likely To Change Next
- `bot/database.py`
- `bot/handlers.py`
- `bot/triggers.py`

## Notes
Any future moderation implementation must preserve existing mention/reply functionality.
