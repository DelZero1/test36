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
                "CREATE INDEX IF NOT EXISTS idx_messages_group_id_id ON messages(group_id, id)"
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
