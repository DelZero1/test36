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
- stores classification decisions in SQLite and now enforces high-confidence spam with chat-type-aware deletion, English warning notices, and timed mutes in supergroups
- lets admins reply with `/spam` to save missed spam labels for future review/training
- supports manual admin moderation commands for mute, unmute, and kick actions
- logs moderation actions and admin spam labels in SQLite

## Confirmed Fixes
- Windows event loop compatibility fix added
- Ollama client lifecycle improved (`start()` / `close()`)
- model name mismatch issue identified and corrected through `.env`
- completed the missing new-user moderation plumbing in the database and handlers so tracked joins are inserted once and only the first 5 messages are stored for later review
- added the first moderation phase: deterministic pre-filtering, Ollama JSON spam classification, audit storage, and short warning replies for strong BC2-off-topic promo/spam signals
- fixed the spam classification prompt template so literal JSON braces are escaped for Python `.format()`, and added defensive logging/early return if prompt building ever fails again
- expanded new-user moderation to the first 5 messages and added enforcement escalation: delete spam, warn in English, mute 24 hours on the first offense, and mute 30 days on repeated offenses while skipping admins and bots
- split automatic enforcement by chat type so normal groups delete + warn without mute, while supergroups keep escalating mutes
- added `/spam` admin reply labeling, username-based admin moderation commands, and moderation action logging tables

## Known Limitations
- moderation classification still applies only to tracked post-start new users and only during their first 5 messages
- automated enforcement is currently limited to high-confidence `SPAM` classifications and does not yet escalate beyond a 30-day mute
- username-based admin commands only resolve users already seen in recent/stored group message history
- spontaneous human-like interjections are not implemented yet
- current bot behavior is mainly triggered-response based

## Last Completed Task
Implemented chat-type-aware moderation and manual admin controls: automatic spam handling now skips mute attempts in normal groups, `/spam` reply labels are persisted, manual mute/unmute/kick commands are supported, and moderation actions are logged in SQLite.

## Next Planned Task
Continue the new-user moderation pipeline:
- add exportable dataset tooling for saved admin spam labels
- keep enriching moderation audit data for future review and training export
- add trusted-user safeguards / whitelist support

## Files Known To Be Stable
- `app.py`
- `bot/config.py`

## Files Likely To Change Next
- `bot/database.py`
- `bot/handlers.py`
- `bot/triggers.py`
- `bot/utils.py`

## Notes
Any future moderation implementation must preserve existing mention/reply functionality.
