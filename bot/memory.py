from typing import Any


def format_message_line(message: dict[str, Any]) -> str:
    timestamp = message.get("timestamp", "unknown-time")
    username = message.get("username") or "unknown-user"
    text = message.get("text") or ""
    return f"[{timestamp}] {username}: {text}".strip()


def build_raw_context(messages: list[dict[str, Any]]) -> str:
    return "\n".join(format_message_line(msg) for msg in messages if msg.get("text"))
