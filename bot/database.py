import asyncio
import logging
import sqlite3
import time
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
            self._ensure_new_user_messages_table(conn)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_group_id_id ON messages(group_id, id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_new_user_messages_chat_user ON new_user_messages(chat_id, user_id)"
            )
            conn.commit()

    def _ensure_new_user_messages_table(self, conn: sqlite3.Connection) -> None:
        table_exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'new_user_messages'"
        ).fetchone()
        expected_columns = {"id", "user_id", "chat_id", "message_text", "created_at"}

        if table_exists is None:
            self._create_new_user_messages_table(conn)
            return

        columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(new_user_messages)").fetchall()
        }
        if columns == expected_columns:
            return

        legacy_table_name = "new_user_messages_legacy"
        conn.execute(f"DROP TABLE IF EXISTS {legacy_table_name}")
        conn.execute(f"ALTER TABLE new_user_messages RENAME TO {legacy_table_name}")
        self._create_new_user_messages_table(conn)

        source_message_column = "message_text" if "message_text" in columns else "text" if "text" in columns else None
        source_created_column = "created_at" if "created_at" in columns else "timestamp" if "timestamp" in columns else None

        if {"user_id", "chat_id"}.issubset(columns) and source_message_column and source_created_column:
            conn.execute(
                f"""
                INSERT INTO new_user_messages (user_id, chat_id, message_text, created_at)
                SELECT user_id, chat_id, {source_message_column}, {source_created_column}
                FROM {legacy_table_name}
                """
            )

    def _create_new_user_messages_table(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS new_user_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                chat_id INTEGER,
                message_text TEXT,
                created_at INTEGER
            )
            """
        )

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

    async def add_new_user(self, user_id: int, chat_id: int) -> None:
        await asyncio.to_thread(self._add_new_user_sync, user_id, chat_id, int(time.time()))

    def _add_new_user_sync(self, user_id: int, chat_id: int, joined_at: int) -> None:
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO new_users (user_id, chat_id, joined_at, messages_count, spam_flags)
                    VALUES (?, ?, ?, 0, 0)
                    """,
                    (user_id, chat_id, joined_at),
                )
                conn.commit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to add new user: %s", exc)

    async def is_new_user(self, user_id: int, chat_id: int) -> bool:
        return await asyncio.to_thread(self._is_new_user_sync, user_id, chat_id)

    def _is_new_user_sync(self, user_id: int, chat_id: int) -> bool:
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT 1 FROM new_users WHERE user_id = ? AND chat_id = ?",
                    (user_id, chat_id),
                ).fetchone()
            return row is not None
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to check tracked new user: %s", exc)
            return False

    async def increment_message_count(self, user_id: int, chat_id: int) -> None:
        await asyncio.to_thread(self._increment_message_count_sync, user_id, chat_id)

    def _increment_message_count_sync(self, user_id: int, chat_id: int) -> None:
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    UPDATE new_users
                    SET messages_count = messages_count + 1
                    WHERE user_id = ? AND chat_id = ?
                    """,
                    (user_id, chat_id),
                )
                conn.commit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to increment new-user message count: %s", exc)

    async def get_message_count(self, user_id: int, chat_id: int) -> int:
        return await asyncio.to_thread(self._get_message_count_sync, user_id, chat_id)

    def _get_message_count_sync(self, user_id: int, chat_id: int) -> int:
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT messages_count FROM new_users WHERE user_id = ? AND chat_id = ?",
                    (user_id, chat_id),
                ).fetchone()
            return int(row["messages_count"]) if row is not None else 0
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to fetch new-user message count: %s", exc)
            return 0

    async def track_new_user(self, *, user_id: int, chat_id: int, joined_at: int) -> None:
        await asyncio.to_thread(self._add_new_user_sync, user_id, chat_id, joined_at)

    async def save_new_user_message(
        self,
        *,
        user_id: int,
        chat_id: int,
        text: str,
        created_at: int,
    ) -> None:
        await asyncio.to_thread(self._save_new_user_message_sync, user_id, chat_id, text, created_at)

    def _save_new_user_message_sync(
        self,
        user_id: int,
        chat_id: int,
        text: str,
        created_at: int,
    ) -> None:
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO new_user_messages (user_id, chat_id, message_text, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (user_id, chat_id, text, created_at),
                )
                conn.commit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to save tracked new-user message: %s", exc)

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
