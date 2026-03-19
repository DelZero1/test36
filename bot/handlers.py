import logging
import time
from collections import defaultdict
from typing import Any

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatMemberStatus
from aiogram.filters import Command
from aiogram.types import ChatMemberUpdated, Message, User

from bot.config import Settings
from bot.database import Database
from bot.memory import build_raw_context
from bot.ollama_client import OllamaClient
from bot.prompts import SUMMARIZATION_PROMPT_TEMPLATE, SYSTEM_PROMPT
from bot.triggers import should_respond
from bot.utils import build_warning_message, safe_message_text, should_prefilter_classify_message, utc_now_iso

logger = logging.getLogger(__name__)

TRACKED_JOIN_STATUSES = {
    ChatMemberStatus.MEMBER,
    ChatMemberStatus.RESTRICTED,
}
LEFT_MEMBER_STATUSES = {ChatMemberStatus.LEFT, ChatMemberStatus.KICKED}
WARN_CONFIDENCE_THRESHOLD = 0.70


def register_handlers(
    dp: Dispatcher,
    bot: Bot,
    db: Database,
    ollama_client: OllamaClient,
    settings: Settings,
) -> None:
    group_cooldowns: dict[int, float] = defaultdict(lambda: 0.0)
    me_cache: User | None = None

    async def get_me() -> User:
        nonlocal me_cache
        if me_cache is None:
            me_cache = await bot.me()
        return me_cache

    async def summarize_messages(messages: list[dict[str, Any]]) -> str:
        if len(messages) <= 30:
            return build_raw_context(messages)

        older = messages[:-10]
        recent = messages[-10:]

        older_for_summary = older[:20]
        older_text = build_raw_context(older_for_summary)

        prompt = SUMMARIZATION_PROMPT_TEMPLATE.format(chat_lines=older_text)
        summary = await ollama_client.summarize(prompt)

        recent_text = build_raw_context(recent)
        if not summary:
            return recent_text

        return "Summary of earlier messages:\n" f"{summary}\n\nMost recent messages:\n{recent_text}"

    def is_cooldown_active(group_id: int) -> bool:
        now = time.monotonic()
        allowed_at = group_cooldowns[group_id]
        if now < allowed_at:
            return True
        group_cooldowns[group_id] = now + settings.response_cooldown_seconds
        return False

    async def maybe_classify_new_user_message(message: Message, text: str) -> None:
        if not message.from_user or message.from_user.is_bot:
            return

        user_id = message.from_user.id
        chat_id = message.chat.id
        if not await db.is_new_user(user_id, chat_id):
            return

        await db.increment_message_count(user_id, chat_id)
        current_count = await db.get_message_count(user_id, chat_id)
        if current_count > 3:
            return

        await db.save_new_user_message(
            user_id=user_id,
            chat_id=chat_id,
            text=text,
            created_at=int(time.time()),
        )

        if not should_prefilter_classify_message(text):
            return

        classification_result = await ollama_client.classify_message_for_spam(
            system_prompt=SYSTEM_PROMPT,
            message_text=text,
        )
        if not classification_result:
            return

        await db.save_classification(
            user_id=user_id,
            chat_id=chat_id,
            text=text,
            classification=classification_result["classification"],
            confidence=classification_result["confidence"],
            reason=classification_result["reason"],
            should_warn=classification_result["should_warn"],
        )

        confidence = classification_result["confidence"]
        wants_warn = classification_result["should_warn"]
        is_strong_spam = classification_result["classification"] == "SPAM" and confidence >= WARN_CONFIDENCE_THRESHOLD
        if confidence < WARN_CONFIDENCE_THRESHOLD or not (wants_warn or is_strong_spam):
            return

        warning_text = build_warning_message(
            classification_result["reason"],
            classification_result["classification"],
        )
        await message.reply(warning_text)

    async def handle_incoming(message: Message) -> None:
        if message.chat.type not in {"group", "supergroup"}:
            return

        text = safe_message_text(message.text, message.caption)
        if not text:
            return

        username = message.from_user.username if message.from_user else None
        display_name = username or (message.from_user.full_name if message.from_user else "unknown-user")
        timestamp = utc_now_iso()

        await db.save_message(
            group_id=message.chat.id,
            message_id=message.message_id,
            user_id=message.from_user.id if message.from_user else None,
            username=display_name,
            text=text,
            timestamp=timestamp,
            is_bot=bool(message.from_user and message.from_user.is_bot),
        )
        await maybe_classify_new_user_message(message, text)

        me = await get_me()
        if message.from_user and message.from_user.id == me.id:
            return

        if not should_respond(message, me.username or "", me.id):
            return

        if is_cooldown_active(message.chat.id):
            logger.info("Cooldown active for group %s", message.chat.id)
            return

        recent_messages = await db.get_recent_messages(message.chat.id, settings.max_context_messages)
        context = await summarize_messages(recent_messages)

        prompt = (
            "You are responding in a Telegram group chat.\n"
            "Context from recent group messages:\n"
            f"{context}\n\n"
            f"Current request from {display_name}:\n{text}\n"
        )

        reply = await ollama_client.generate_reply(system_prompt=SYSTEM_PROMPT, prompt=prompt)
        if not reply:
            await message.reply("I couldn't reach the local AI model right now. Please try again shortly.")
            return

        trimmed = reply[: settings.max_response_chars].strip()
        sent = await message.reply(trimmed)

        await db.save_message(
            group_id=message.chat.id,
            message_id=sent.message_id,
            user_id=me.id,
            username=me.username or "bot",
            text=trimmed,
            timestamp=utc_now_iso(),
            is_bot=True,
        )

    @dp.chat_member(F.chat.type.in_({"group", "supergroup"}))
    async def track_joined_user(event: ChatMemberUpdated) -> None:
        old_status = event.old_chat_member.status
        new_status = event.new_chat_member.status
        joined_user = event.new_chat_member.user

        if event.chat.type == "private" or joined_user.is_bot:
            return

        if new_status not in TRACKED_JOIN_STATUSES or old_status not in LEFT_MEMBER_STATUSES:
            return

        await db.add_new_user(joined_user.id, event.chat.id)

    @dp.message(Command("ask"), F.chat.type.in_({"group", "supergroup"}))
    async def ask_command(message: Message) -> None:
        await handle_incoming(message)

    @dp.message(F.chat.type.in_({"group", "supergroup"}))
    async def all_group_messages(message: Message) -> None:
        await handle_incoming(message)
