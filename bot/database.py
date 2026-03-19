import asyncio
import logging
import sqlite3
from typing import Any

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, path: str):
        self.path = path

    async def init(self) -> None:
        await asyncio.to_thread(self._init_sync)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_sync(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    user_id INTEGER,
                    username TEXT,
                    text TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    is_bot INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS new_users (
                    user_id INTEGER,
                    chat_id INTEGER,
                    joined_at INTEGER,
                    messages_count INTEGER DEFAULT 0,
                    spam_flags INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, chat_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS new_user_messages (
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    PRIMARY KEY (user_id, chat_id, message_id)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_group_id_id ON messages(group_id, id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_new_user_messages_chat_user ON new_user_messages(chat_id, user_id)"
            )
            conn.commit()

    async def save_message(
        self,
        *,
        group_id: int,
        message_id: int,
        user_id: int | None,
        username: str,
        text: str,
        timestamp: str,
        is_bot: bool,
    ) -> None:
        await asyncio.to_thread(
            self._save_message_sync,
            group_id,
            message_id,
            user_id,
            username,
            text,
            timestamp,
            int(is_bot),
        )

    def _save_message_sync(
        self,
        group_id: int,
        message_id: int,
        user_id: int | None,
        username: str,
        text: str,
        timestamp: str,
        is_bot: int,
    ) -> None:
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO messages (group_id, message_id, user_id, username, text, timestamp, is_bot)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (group_id, message_id, user_id, username, text, timestamp, is_bot),
                )
                conn.commit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to save message: %s", exc)

    async def track_new_user(self, *, user_id: int, chat_id: int, joined_at: int) -> None:
        await asyncio.to_thread(self._track_new_user_sync, user_id, chat_id, joined_at)

    def _track_new_user_sync(self, user_id: int, chat_id: int, joined_at: int) -> None:
        try:
            with self._connect() as conn:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute(
                    "DELETE FROM new_user_messages WHERE user_id = ? AND chat_id = ?",
                    (user_id, chat_id),
                )
                conn.execute(
                    """
                    INSERT OR REPLACE INTO new_users (user_id, chat_id, joined_at, messages_count, spam_flags)
                    VALUES (?, ?, ?, 0, 0)
                    """,
                    (user_id, chat_id, joined_at),
                )
                conn.commit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to track new user: %s", exc)

    async def save_new_user_message(
        self,
        *,
        user_id: int,
        chat_id: int,
        message_id: int,
        text: str,
        timestamp: str,
        min_joined_at: int,
    ) -> bool:
        return await asyncio.to_thread(
            self._save_new_user_message_sync,
            user_id,
            chat_id,
            message_id,
            text,
            timestamp,
            min_joined_at,
        )

    def _save_new_user_message_sync(
        self,
        user_id: int,
        chat_id: int,
        message_id: int,
        text: str,
        timestamp: str,
        min_joined_at: int,
    ) -> bool:
        try:
            with self._connect() as conn:
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute(
                    """
                    SELECT messages_count
                    FROM new_users
                    WHERE user_id = ? AND chat_id = ? AND joined_at >= ?
                    """,
                    (user_id, chat_id, min_joined_at),
                ).fetchone()
                if row is None or row["messages_count"] >= 3:
                    return False

                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO new_user_messages (user_id, chat_id, message_id, text, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (user_id, chat_id, message_id, text, timestamp),
                )
                if cursor.rowcount == 0:
                    return False

                conn.execute(
                    """
                    UPDATE new_users
                    SET messages_count = messages_count + 1
                    WHERE user_id = ? AND chat_id = ? AND joined_at >= ?
                    """,
                    (user_id, chat_id, min_joined_at),
                )
                conn.commit()
                return True
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to save tracked new-user message: %s", exc)
            return False

    async def get_recent_messages(self, group_id: int, limit: int) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._get_recent_messages_sync, group_id, limit)

    def _get_recent_messages_sync(self, group_id: int, limit: int) -> list[dict[str, Any]]:
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT group_id, message_id, user_id, username, text, timestamp, is_bot
                    FROM messages
                    WHERE group_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (group_id, limit),
                ).fetchall()
            return [dict(row) for row in reversed(rows)]
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to fetch recent messages: %s", exc)
            return []
