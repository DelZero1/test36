from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


def safe_message_text(text: str | None, caption: str | None) -> str:
    value = text or caption or ""
    return value.strip()
