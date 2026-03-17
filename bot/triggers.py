from aiogram.types import Message


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
