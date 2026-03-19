# PLAN.md

## Milestone 1 — Stable Group Bot
- [x] Group-only bot
- [x] SQLite message persistence
- [x] Mention/reply/ask triggers
- [x] Ollama integration
- [x] Summarization for large context
- [x] Windows compatibility fixes

## Milestone 2 — Humanized Prompting
- [ ] Improve system prompt for natural non-robotic group behavior
- [ ] Add separate prompt modes:
  - direct reply
  - casual reaction
  - summarization

## Milestone 3 — Moderation System for New Users
- [x] Track only users who joined after bot startup
- [x] Record first 5 messages per tracked new user
- [x] Run spam/promo classification on those messages
- [x] Escalation rules:
  - [x] 1 spam-like message -> warn + mute 24h
  - [x] repeated spam-like message -> mute 30d
- [x] Preserve audit trail in SQLite

## Milestone 4 — Admin Feedback Loop
- [x] Allow admin to reply to a message and mark it as spam
- [x] Store labeled examples in DB
- [ ] Add exportable dataset format for future tuning/training

## Milestone 5 — Safety and Quality
- [x] Confidence thresholds
- [ ] whitelist for admins/trusted users
- [x] anti-false-positive safeguards
- [x] logging for moderation decisions
- [x] Different moderation behavior for groups vs supergroups
- [x] Manual admin mute/unmute/kick commands

## Milestone 6 — Optional Future Work
- [ ] spontaneous group interjections
- [ ] long-term conversation memory
- [ ] analytics dashboard
