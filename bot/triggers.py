import re

from aiogram.types import Message

TRACKED_NEW_USER_MESSAGE_LIMIT = 5
MODERATION_CONFIDENCE_THRESHOLD = 0.70
FIRST_MUTE_SECONDS = 24 * 60 * 60
SECOND_MUTE_SECONDS = 30 * 24 * 60 * 60
MANUAL_MUTE_SECONDS = 60 * 60

USERNAME_PATTERN = re.compile(r"(?<!\w)@([a-z0-9_]{3,32})", re.IGNORECASE)
MANUAL_ACTION_PATTERNS = (
    ("unmute", ("unmute this user", "unmute", "odmutiraj korisnika", "odmutiraj ovog korisnika", "odmutiraj")),
    ("mute", ("mute this user", "mute", "mutiraj ovog korisnika", "mutiraj korisnika", "mutiraj")),
    ("kick", ("kick this user", "kickaj korisnika", "kickaj ovog korisnika", "kickaj", "kick", "ban")),
)


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


def build_escalation_warning(
    username: str,
    reason: str,
    warnings_count: int,
    *,
    enforcement_mode: str,
) -> str:
    short_reason = " ".join(reason.split()).strip(" .,!?")
    if not short_reason:
        short_reason = "it looks like spam or off-topic promotion"

    if enforcement_mode != "supergroup_mute":
        if warnings_count <= 0:
            return f"⚠️ {username} your message was removed because it looks like spam or unrelated promotion."
        return f"⚠️ {username} your message was removed for repeated off-topic promotion."

    if warnings_count <= 0:
        return (
            f"⚠️ {username} your message was removed — {short_reason}. "
            "You have been muted for 24 hours."
        )

    return (
        f"🚫 {username} repeated spam detected — {short_reason}. "
        "You are now muted for 30 days."
    )


def parse_manual_moderation_command(text: str, bot_username: str | None) -> dict[str, str | None] | None:
    if not text or not bot_username:
        return None

    normalized = " ".join(text.lower().split())
    mention = f"@{bot_username.lower()}"
    if mention not in normalized:
        return None

    command_text = normalized.replace(mention, " ", 1).strip(" ,.:;!-")
    if not command_text:
        return None

    usernames = USERNAME_PATTERN.findall(command_text)
    target_username = usernames[0].lower() if usernames else None
    command_without_target = USERNAME_PATTERN.sub(" ", command_text)
    command_without_target = " ".join(command_without_target.split()).strip(" ,.:;!-")

    for action, phrases in MANUAL_ACTION_PATTERNS:
        for phrase in phrases:
            if command_without_target == phrase:
                return {"action": action, "target_username": target_username}
    return None
