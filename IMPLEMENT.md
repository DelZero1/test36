# IMPLEMENT.md

## Execution Rules
When working on this repository:

1. Read first:
   - `AGENTS.md`
   - `PROGRESS.md`
   - `PLAN.md`
   - `README.md`

2. Treat `PLAN.md` as the roadmap and `PROGRESS.md` as the current state.

3. Work only on the current milestone or explicitly requested task.

4. Keep changes scoped:
   - do not refactor unrelated files
   - do not rename files unless necessary
   - do not move logic between modules without documenting it

5. Before editing:
   - identify touched files
   - explain why those files are the correct place for the change

6. After editing:
   - run validation commands
   - summarize changes
   - update `PROGRESS.md`
   - mark relevant checklist items in `PLAN.md`

## Validation Commands
Run the most relevant commands after each change:

- `python -m compileall .`
- `python app.py`

If startup fails, fix the issue before stopping.

## File Ownership Rules
- startup/bootstrap -> `app.py`
- env/settings -> `bot/config.py`
- DB schema/queries -> `bot/database.py`
- Telegram routing/orchestration -> `bot/handlers.py`
- context/summarization prep -> `bot/memory.py`
- Ollama HTTP client -> `bot/ollama_client.py`
- prompts/templates -> `bot/prompts.py`
- trigger and moderation rules -> `bot/triggers.py`
- helpers -> `bot/utils.py`

## Documentation Discipline
Do not leave docs stale.
If implementation changes behavior, update docs in the same task.

## Current Priority
Implement the moderation architecture for new users without breaking current triggered-response behavior.
