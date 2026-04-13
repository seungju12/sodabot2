from __future__ import annotations

from pathlib import Path
from typing import Any

import aiosqlite


class Database:
    def __init__(self, db_path: Path):
        self.db_path = str(db_path)
        self._db: aiosqlite.Connection | None = None

    async def init(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        await self._db.executescript(
            """
                PRAGMA foreign_keys = ON;

                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    discord_id TEXT NOT NULL UNIQUE,
                    guild_id TEXT NOT NULL DEFAULT '0',
                    warning_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS warning_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    guild_id TEXT NOT NULL DEFAULT '0',
                    action TEXT NOT NULL,
                    actor_discord_id TEXT,
                    target_discord_id TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    total_warning_count INTEGER NOT NULL,
                    period_key TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL UNIQUE,
                    guild_id TEXT NOT NULL DEFAULT '0',
                    value TEXT NOT NULL,
                    value_type TEXT NOT NULL,
                    updated_by_discord_id TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS voice_channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id TEXT NOT NULL UNIQUE,
                    guild_id TEXT NOT NULL DEFAULT '0',
                    owner_discord_id TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS auth_period_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT NOT NULL DEFAULT '0',
                    user_discord_id TEXT NOT NULL,
                    period_key TEXT NOT NULL,
                    is_authenticated INTEGER NOT NULL DEFAULT 0,
                    updated_by_discord_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(guild_id, user_discord_id, period_key)
                );
            """
        )

        # Legacy DB compatibility: add missing guild_id columns for existing tables.
        await self._ensure_column("users", "guild_id", "TEXT NOT NULL DEFAULT '0'")
        await self._ensure_column("warning_history", "guild_id", "TEXT NOT NULL DEFAULT '0'")
        await self._ensure_column("config", "guild_id", "TEXT NOT NULL DEFAULT '0'")
        await self._ensure_column("voice_channels", "guild_id", "TEXT NOT NULL DEFAULT '0'")

        await self._db.executescript(
            """
                CREATE INDEX IF NOT EXISTS idx_warning_history_target_created
                ON warning_history(target_discord_id, created_at DESC);

                CREATE INDEX IF NOT EXISTS idx_warning_history_period_action
                ON warning_history(period_key, action, target_discord_id);

                CREATE INDEX IF NOT EXISTS idx_users_guild_discord
                ON users(guild_id, discord_id);

                CREATE INDEX IF NOT EXISTS idx_warning_history_guild_target_period
                ON warning_history(guild_id, target_discord_id, period_key);

                CREATE INDEX IF NOT EXISTS idx_config_guild
                ON config(guild_id);

                CREATE INDEX IF NOT EXISTS idx_voice_channels_guild_channel
                ON voice_channels(guild_id, channel_id);

                CREATE INDEX IF NOT EXISTS idx_auth_period_status_lookup
                ON auth_period_status(guild_id, user_discord_id, period_key);
            """
        )

        await self._db.commit()

    async def _ensure_column(self, table: str, column: str, column_def: str) -> None:
        if not self._db:
            raise RuntimeError("Database not initialized. Call init() first.")
        cur = await self._db.execute(f"PRAGMA table_info({table})")
        rows = await cur.fetchall()
        await cur.close()
        column_names = {row[1] for row in rows}
        if column in column_names:
            return
        await self._db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_def}")

    async def execute(self, query: str, params: tuple[Any, ...] = ()) -> None:
        """풀 연결 사용으로 성능 향상"""
        if not self._db:
            raise RuntimeError("Database not initialized. Call init() first.")
        await self._db.execute(query, params)
        await self._db.commit()

    async def fetchone(self, query: str, params: tuple[Any, ...] = ()):
        """풀 연결 사용으로 성능 향상"""
        if not self._db:
            raise RuntimeError("Database not initialized. Call init() first.")
        self._db.row_factory = aiosqlite.Row
        cur = await self._db.execute(query, params)
        row = await cur.fetchone()
        await cur.close()
        return row

    async def fetchall(self, query: str, params: tuple[Any, ...] = ()):
        """풀 연결 사용으로 성능 향상"""
        if not self._db:
            raise RuntimeError("Database not initialized. Call init() first.")
        self._db.row_factory = aiosqlite.Row
        cur = await self._db.execute(query, params)
        rows = await cur.fetchall()
        await cur.close()
        return rows

    async def execute_fetchone(self, query: str, params: tuple[Any, ...] = ()):
        """풀 연결 사용으로 성능 향상"""
        if not self._db:
            raise RuntimeError("Database not initialized. Call init() first.")
        self._db.row_factory = aiosqlite.Row
        cur = await self._db.execute(query, params)
        row = await cur.fetchone()
        await self._db.commit()
        await cur.close()
        return row

    async def close(self) -> None:
        """연결 종료"""
        if self._db:
            await self._db.close()
            self._db = None
