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
- [ ] Track only users who joined after bot startup
- [ ] Record first 3 messages per tracked new user
- [ ] Run spam/promo classification on those messages
- [ ] Escalation rules:
  - 1 spam-like message -> warn
  - 2 spam-like messages -> mute 24h
  - 3 spam-like messages -> mute 30d
- [ ] Preserve audit trail in SQLite

## Milestone 4 — Admin Feedback Loop
- [ ] Allow admin to reply to a message and mark it as spam
- [ ] Store labeled examples in DB
- [ ] Add exportable dataset format for future tuning/training

## Milestone 5 — Safety and Quality
- [ ] Confidence thresholds
- [ ] whitelist for admins/trusted users
- [ ] anti-false-positive safeguards
- [ ] logging for moderation decisions

## Milestone 6 — Optional Future Work
- [ ] spontaneous group interjections
- [ ] long-term conversation memory
- [ ] analytics dashboard
