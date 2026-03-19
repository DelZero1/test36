# AGENTS.md

## Project
Telegram Group AI Bot using:
- Python 3.11+
- aiogram v3
- aiohttp
- python-dotenv
- sqlite3
- local Ollama models

This bot is designed for Telegram group chats only.

## Current Goal
Evolve the existing group bot into a smarter context-aware and moderation-capable system without breaking the current working mention/reply flow.

## Source of Truth
Before changing code, always read:
1. `README.md`
2. `PROGRESS.md`
3. `PLAN.md`
4. `IMPLEMENT.md`

## Architecture Rules
- `app.py` is only for startup, shutdown, dependency wiring, and polling bootstrap.
- `bot/config.py` handles environment loading and settings only.
- `bot/database.py` handles schema creation and database read/write methods only.
- `bot/handlers.py` handles Telegram update routing and orchestration only.
- `bot/memory.py` handles recent context retrieval and summarization preparation.
- `bot/ollama_client.py` handles Ollama HTTP communication only.
- `bot/prompts.py` contains all LLM prompt templates only.
- `bot/triggers.py` contains trigger decisions and moderation decision helpers only.
- `bot/utils.py` contains small reusable helpers.

Do not move responsibilities across files unless explicitly required and documented in `PROGRESS.md`.

## Change Management Rules
- Keep diffs scoped to the active task.
- Do not rewrite unrelated modules.
- Preserve existing working behavior unless the task explicitly changes it.
- Prefer additive changes over destructive refactors.
- If changing architecture, update `README.md`, `PROGRESS.md`, and `PLAN.md`.

## Required Validation After Every Change
Run the relevant checks after making changes:
- syntax/import check
- startup sanity check
- verify bot can still start without crashing
- verify Ollama client lifecycle still works
- verify no environment variables were broken

Suggested commands:
- `python -m compileall .`
- `python app.py`

If a change affects moderation logic, also verify:
- new users are tracked correctly
- penalties escalate correctly
- admin feedback flow still works if implemented

## Documentation Update Rules
After every completed task:
- update `PROGRESS.md`
- mark completed items in `PLAN.md`
- if developer workflow changed, update `README.md`
- if coding rules changed, update `AGENTS.md`

## Implementation Priorities
1. Keep current bot stable
2. Improve prompt quality and context handling
3. Add moderation system for new users
4. Add admin feedback labeling
5. Add future training/export support only after moderation pipeline is stable

## Constraints
- Group-only bot
- Local Ollama only
- SQLite only for now
- No Docker required
- No cloud services
- No private chat features
- Windows compatibility must be preserved

## Output Expectations for Agent Tasks
When completing a task:
1. summarize what changed
2. list touched files
3. list validation commands run
4. update `PROGRESS.md`
