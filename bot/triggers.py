from aiogram.types import Message

TRACKED_NEW_USER_MESSAGE_LIMIT = 5
MODERATION_CONFIDENCE_THRESHOLD = 0.70
FIRST_MUTE_SECONDS = 24 * 60 * 60
SECOND_MUTE_SECONDS = 30 * 24 * 60 * 60


def is_bot_mentioned(message: Message, bot_username: str) -> bool:
    text = message.text or message.caption or ""
    return f"@{bot_username.lower()}" in text.lower()


def is_reply_to_bot(message: Message, bot_user_id: int) -> bool:
    if not message.reply_to_message or not message.reply_to_message.from_user:
        return False
    return message.reply_to_message.from_user.id == bot_user_id


def is_ask_command(message: Message) -> bool:
    if not message.text:
        return False
    return message.text.strip().lower().startswith("/ask")


def should_respond(message: Message, bot_username: str, bot_user_id: int) -> bool:
    return (
        is_bot_mentioned(message, bot_username)
        or is_reply_to_bot(message, bot_user_id)
        or is_ask_command(message)
    )


def should_classify_tracked_message(message_count: int) -> bool:
    return message_count <= TRACKED_NEW_USER_MESSAGE_LIMIT


def should_apply_spam_penalty(classification: str | None, confidence: float | None) -> bool:
    if classification is None or confidence is None:
        return False
    return classification == "SPAM" and confidence >= MODERATION_CONFIDENCE_THRESHOLD


def get_mute_seconds_for_warning_count(warnings_count: int) -> int:
    if warnings_count <= 0:
        return FIRST_MUTE_SECONDS
    return SECOND_MUTE_SECONDS


def build_escalation_warning(username: str, reason: str, warnings_count: int) -> str:
    short_reason = " ".join(reason.split()).strip(" .,!?")
    if not short_reason:
        short_reason = "it looks like spam or off-topic promotion"

    if warnings_count <= 0:
        return (
            f"⚠️ {username} your message was removed — {short_reason}. "
            "You have been muted for 24 hours."
        )

    return (
        f"🚫 {username} repeated spam detected — {short_reason}. "
        "You are now muted for 30 days."
    )
