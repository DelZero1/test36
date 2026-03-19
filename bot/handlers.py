import logging
import time
from collections import defaultdict
from typing import Any

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatMemberStatus
from aiogram.filters import Command
from aiogram.types import ChatMemberUpdated, ChatPermissions, Message, User

from bot.config import Settings
from bot.database import Database
from bot.memory import build_raw_context
from bot.ollama_client import OllamaClient
from bot.prompts import SUMMARIZATION_PROMPT_TEMPLATE, SYSTEM_PROMPT
from bot.triggers import (
    MANUAL_MUTE_SECONDS,
    build_escalation_warning,
    get_mute_seconds_for_warning_count,
    parse_manual_moderation_command,
    should_apply_spam_penalty,
    should_classify_tracked_message,
    should_respond,
)
from bot.utils import (
    format_user_label,
    normalize_username,
    safe_message_text,
    should_prefilter_classify_message,
    utc_now_iso,
)

logger = logging.getLogger(__name__)

TRACKED_JOIN_STATUSES = {
    ChatMemberStatus.MEMBER,
    ChatMemberStatus.RESTRICTED,
}
LEFT_MEMBER_STATUSES = {ChatMemberStatus.LEFT, ChatMemberStatus.KICKED}
MODERATION_EXEMPT_STATUSES = {ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR}
FULL_SEND_PERMISSIONS = ChatPermissions(
    can_send_messages=True,
    can_send_audios=True,
    can_send_documents=True,
    can_send_photos=True,
    can_send_videos=True,
    can_send_video_notes=True,
    can_send_voice_notes=True,
    can_send_polls=True,
    can_send_other_messages=True,
    can_add_web_page_previews=True,
)


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

    async def log_action(
        *,
        chat_id: int,
        target_user: User | None,
        actor_user: User | None,
        action: str,
        reason: str,
        duration_seconds: int | None,
        source: str,
        target_username_override: str | None = None,
    ) -> None:
        await db.log_moderation_action(
            chat_id=chat_id,
            target_user_id=target_user.id if target_user else None,
            target_username=target_username_override or (target_user.username if target_user else None),
            actor_user_id=actor_user.id if actor_user else None,
            actor_username=actor_user.username if actor_user else None,
            action=action,
            reason=reason,
            duration_seconds=duration_seconds,
            source=source,
        )

    async def delete_message_safe(message: Message, *, reason: str, actor_user: User | None, source: str) -> bool:
        try:
            await message.delete()
            await log_action(
                chat_id=message.chat.id,
                target_user=message.from_user,
                actor_user=actor_user,
                action="DELETE_MESSAGE",
                reason=reason,
                duration_seconds=None,
                source=source,
            )
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Failed to delete spam message %s in chat %s: %s",
                message.message_id,
                message.chat.id,
                exc,
            )
            return False

    async def send_moderation_notice(
        chat_id: int,
        text: str,
        *,
        target_user: User | None,
        actor_user: User | None,
        reason: str,
        source: str,
    ) -> None:
        try:
            await bot.send_message(chat_id, text)
            await log_action(
                chat_id=chat_id,
                target_user=target_user,
                actor_user=actor_user,
                action="WARN",
                reason=reason,
                duration_seconds=None,
                source=source,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Failed to send moderation notice for user %s in chat %s: %s",
                target_user.id if target_user else None,
                chat_id,
                exc,
            )

    async def mute_user(
        chat_id: int,
        user_id: int,
        seconds: int,
        *,
        target_user: User | None,
        actor_user: User | None,
        reason: str,
        source: str,
    ) -> int | None:
        mute_until = int(time.time()) + seconds
        try:
            await bot.restrict_chat_member(
                chat_id,
                user_id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=mute_until,
            )
            action_name = "MUTE_1H" if seconds == MANUAL_MUTE_SECONDS else "MUTE_24H" if seconds == 24 * 60 * 60 else "MUTE_30D"
            await log_action(
                chat_id=chat_id,
                target_user=target_user,
                actor_user=actor_user,
                action=action_name,
                reason=reason,
                duration_seconds=seconds,
                source=source,
            )
            return mute_until
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Failed to mute user %s in chat %s for %s seconds: %s",
                user_id,
                chat_id,
                seconds,
                exc,
            )
            return None

    async def unmute_user(
        chat_id: int,
        user_id: int,
        *,
        target_user: User | None,
        actor_user: User | None,
        reason: str,
        source: str,
    ) -> bool:
        try:
            await bot.restrict_chat_member(
                chat_id,
                user_id,
                permissions=FULL_SEND_PERMISSIONS,
                until_date=0,
            )
            await log_action(
                chat_id=chat_id,
                target_user=target_user,
                actor_user=actor_user,
                action="UNMUTE",
                reason=reason,
                duration_seconds=None,
                source=source,
            )
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to unmute user %s in chat %s: %s", user_id, chat_id, exc)
            return False

    async def kick_user(
        chat_id: int,
        user_id: int,
        *,
        target_user: User | None,
        actor_user: User | None,
        reason: str,
        source: str,
    ) -> bool:
        try:
            await bot.ban_chat_member(chat_id, user_id, revoke_messages=False)
            await bot.unban_chat_member(chat_id, user_id, only_if_banned=True)
            await log_action(
                chat_id=chat_id,
                target_user=target_user,
                actor_user=actor_user,
                action="KICK",
                reason=reason,
                duration_seconds=None,
                source=source,
            )
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to kick user %s in chat %s: %s", user_id, chat_id, exc)
            return False

    async def is_admin(chat_id: int, user_id: int) -> bool:
        try:
            member = await bot.get_chat_member(chat_id, user_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to fetch admin status for user %s in chat %s: %s", user_id, chat_id, exc)
            return False
        return member.status in MODERATION_EXEMPT_STATUSES

    async def is_moderation_exempt(message: Message) -> bool:
        if not message.from_user:
            return True

        if message.from_user.is_bot:
            return True

        return await is_admin(message.chat.id, message.from_user.id)

    async def get_resolved_target_user(message: Message, target_username: str | None) -> User | None:
        if message.reply_to_message and message.reply_to_message.from_user:
            return message.reply_to_message.from_user

        normalized = normalize_username(target_username)
        if not normalized:
            return None

        record = await db.resolve_user_by_username(message.chat.id, normalized)
        if not record or record.get("user_id") is None:
            return None

        resolved_username = record.get("username")
        return User(
            id=int(record["user_id"]),
            is_bot=bool(record.get("is_bot")),
            first_name=resolved_username or normalized,
            username=normalize_username(resolved_username),
        )

    async def validate_manual_target(message: Message, target_user: User | None) -> bool:
        me = await get_me()
        if target_user is None:
            return False
        if target_user.is_bot or target_user.id == me.id:
            await bot.send_message(message.chat.id, "I can't moderate bots with this command.")
            return False
        if await is_admin(message.chat.id, target_user.id):
            await bot.send_message(message.chat.id, "I won't apply moderation actions to admins.")
            return False
        return True

    async def maybe_enforce_spam_penalty(message: Message, classification_result: dict[str, Any]) -> None:
        if not message.from_user:
            return

        if await is_moderation_exempt(message):
            return

        prior_warnings = await db.get_warning_count(message.from_user.id, message.chat.id)
        mute_seconds = get_mute_seconds_for_warning_count(prior_warnings)
        warning_text = build_escalation_warning(
            format_user_label(message.from_user),
            classification_result["reason"],
            prior_warnings,
            enforcement_mode="supergroup_mute" if message.chat.type == "supergroup" else "group_warn_only",
        )
        enforcement_mode = "supergroup_mute" if message.chat.type == "supergroup" else "group_warn_only"
        logger.info(
            "Applying spam enforcement mode=%s for user %s in chat %s",
            enforcement_mode,
            message.from_user.id,
            message.chat.id,
        )

        await db.increment_warning(message.from_user.id, message.chat.id)
        await delete_message_safe(
            message,
            reason=classification_result["reason"],
            actor_user=None,
            source="AUTO_SPAM_RULE",
        )

        if message.chat.type == "supergroup":
            mute_until = await mute_user(
                message.chat.id,
                message.from_user.id,
                mute_seconds,
                target_user=message.from_user,
                actor_user=None,
                reason=classification_result["reason"],
                source="AUTO_SPAM_RULE",
            )
            if mute_until is not None:
                await db.update_last_mute_until(message.from_user.id, message.chat.id, mute_until)
        else:
            await db.log_moderation_action(
                chat_id=message.chat.id,
                target_user_id=message.from_user.id,
                target_username=message.from_user.username,
                actor_user_id=None,
                actor_username=None,
                action="MUTE_UNAVAILABLE",
                reason=f"{classification_result['reason']} | enforcement_mode={enforcement_mode}",
                duration_seconds=None,
                source="AUTO_SPAM_RULE",
            )

        await send_moderation_notice(
            message.chat.id,
            warning_text,
            target_user=message.from_user,
            actor_user=None,
            reason=f"{classification_result['reason']} | enforcement_mode={enforcement_mode}",
            source="AUTO_SPAM_RULE",
        )

    async def maybe_classify_new_user_message(message: Message, text: str) -> bool:
        if not message.from_user or message.from_user.is_bot:
            return False

        user_id = message.from_user.id
        chat_id = message.chat.id
        if not await db.is_new_user(user_id, chat_id):
            return False

        await db.increment_message_count(user_id, chat_id)
        current_count = await db.get_message_count(user_id, chat_id)
        if not should_classify_tracked_message(current_count):
            return False

        await db.save_new_user_message(
            user_id=user_id,
            chat_id=chat_id,
            text=text,
            created_at=int(time.time()),
        )

        if not should_prefilter_classify_message(text):
            return False

        classification_result = await ollama_client.classify_message_for_spam(
            system_prompt=SYSTEM_PROMPT,
            message_text=text,
        )
        if not classification_result:
            return False

        await db.save_classification(
            user_id=user_id,
            chat_id=chat_id,
            text=text,
            classification=classification_result["classification"],
            confidence=classification_result["confidence"],
            reason=classification_result["reason"],
            should_warn=classification_result["should_warn"],
        )

        if not should_apply_spam_penalty(
            classification_result.get("classification"),
            classification_result.get("confidence"),
        ):
            return False

        await maybe_enforce_spam_penalty(message, classification_result)
        return True

    async def maybe_handle_spam_label_command(message: Message) -> bool:
        if not message.from_user or not message.text:
            return False

        command_token = message.text.strip().split(maxsplit=1)[0].lower()
        if command_token not in {"/spam", f"/spam@{((await get_me()).username or '').lower()}"}:
            return False

        if not await is_admin(message.chat.id, message.from_user.id):
            return True

        target_message = message.reply_to_message
        if not target_message or not target_message.from_user:
            await bot.send_message(message.chat.id, "Please reply to the spam message you want me to label.")
            return True

        target_text = safe_message_text(target_message.text, target_message.caption)
        if not target_text:
            await bot.send_message(message.chat.id, "I can only label messages that contain text.")
            return True

        target_username = target_message.from_user.username or target_message.from_user.full_name
        created_at = int(message.date.timestamp())

        await db.save_admin_spam_label(
            chat_id=message.chat.id,
            target_user_id=target_message.from_user.id,
            target_username=target_username,
            labeled_by_admin_id=message.from_user.id,
            message_text=target_text,
            label="SPAM",
            created_at=created_at,
        )
        await log_action(
            chat_id=message.chat.id,
            target_user=target_message.from_user,
            actor_user=message.from_user,
            action="ADMIN_LABEL_SPAM",
            reason="Admin labeled a missed spam message.",
            duration_seconds=None,
            source="ADMIN_REPLY_LABEL",
            target_username_override=target_username,
        )
        await delete_message_safe(
            target_message,
            reason="Admin labeled the message as spam.",
            actor_user=message.from_user,
            source="ADMIN_REPLY_LABEL",
        )
        await bot.send_message(message.chat.id, f"✅ Saved a spam label for {format_user_label(target_message.from_user)}.")
        return True

    async def maybe_handle_manual_moderation_command(message: Message) -> bool:
        if not message.from_user:
            return False

        command = parse_manual_moderation_command(safe_message_text(message.text, message.caption), (await get_me()).username)
        if not command:
            return False

        if not await is_admin(message.chat.id, message.from_user.id):
            return True

        target_user = await get_resolved_target_user(message, command["target_username"])
        if target_user is None:
            if message.reply_to_message:
                await bot.send_message(message.chat.id, "I couldn't resolve that user from recent group context.")
            else:
                await bot.send_message(
                    message.chat.id,
                    "Please reply to a user's message or mention @username so I know who to moderate.",
                )
            return True

        if not await validate_manual_target(message, target_user):
            return True

        action = command["action"]
        if action == "mute":
            if message.chat.type != "supergroup":
                await db.log_moderation_action(
                    chat_id=message.chat.id,
                    target_user_id=target_user.id,
                    target_username=target_user.username,
                    actor_user_id=message.from_user.id,
                    actor_username=message.from_user.username,
                    action="MUTE_UNAVAILABLE",
                    reason="Manual mute requested in a normal group.",
                    duration_seconds=MANUAL_MUTE_SECONDS,
                    source="MANUAL_ADMIN_COMMAND",
                )
                await bot.send_message(message.chat.id, "⚠️ Mute is not available in normal groups.")
                return True

            mute_until = await mute_user(
                message.chat.id,
                target_user.id,
                MANUAL_MUTE_SECONDS,
                target_user=target_user,
                actor_user=message.from_user,
                reason="Manual admin mute.",
                source="MANUAL_ADMIN_COMMAND",
            )
            if mute_until is None:
                await bot.send_message(message.chat.id, "⚠️ I couldn't mute that user. Please check my admin rights.")
                return True
            await bot.send_message(message.chat.id, f"✅ {format_user_label(target_user)} has been muted for 1 hour.")
            return True

        if action == "unmute":
            success = await unmute_user(
                message.chat.id,
                target_user.id,
                target_user=target_user,
                actor_user=message.from_user,
                reason="Manual admin unmute.",
                source="MANUAL_ADMIN_COMMAND",
            )
            if not success:
                await bot.send_message(message.chat.id, "⚠️ I couldn't unmute that user. Please check my admin rights.")
                return True
            await bot.send_message(message.chat.id, f"✅ {format_user_label(target_user)} has been unmuted.")
            return True

        if action == "kick":
            success = await kick_user(
                message.chat.id,
                target_user.id,
                target_user=target_user,
                actor_user=message.from_user,
                reason="Manual admin removal.",
                source="MANUAL_ADMIN_COMMAND",
            )
            if not success:
                await bot.send_message(message.chat.id, "⚠️ I couldn't remove that user. Please check my admin rights.")
                return True
            await bot.send_message(message.chat.id, f"✅ {format_user_label(target_user)} has been removed from the group.")
            return True

        return False

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

        if await maybe_handle_spam_label_command(message):
            return

        if await maybe_handle_manual_moderation_command(message):
            return

        moderation_action_taken = await maybe_classify_new_user_message(message, text)
        if moderation_action_taken:
            return

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
