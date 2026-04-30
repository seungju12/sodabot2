from __future__ import annotations

import asyncio
from typing import Any

import psycopg
from psycopg.rows import dict_row

if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class Database:
    POSTGRES_SCHEMA = """
        CREATE TABLE IF NOT EXISTS users (
            id BIGSERIAL PRIMARY KEY,
            discord_id TEXT NOT NULL UNIQUE,
            guild_id TEXT NOT NULL DEFAULT '0',
            warning_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS warning_history (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(id),
            guild_id TEXT NOT NULL DEFAULT '0',
            action TEXT NOT NULL,
            actor_discord_id TEXT,
            target_discord_id TEXT NOT NULL,
            reason TEXT NOT NULL,
            total_warning_count INTEGER NOT NULL,
            period_key TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS config (
            id BIGSERIAL PRIMARY KEY,
            key TEXT NOT NULL UNIQUE,
            guild_id TEXT NOT NULL DEFAULT '0',
            value TEXT NOT NULL,
            value_type TEXT NOT NULL,
            updated_by_discord_id TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS voice_channels (
            id BIGSERIAL PRIMARY KEY,
            channel_id TEXT NOT NULL UNIQUE,
            guild_id TEXT NOT NULL DEFAULT '0',
            owner_discord_id TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS auth_period_status (
            id BIGSERIAL PRIMARY KEY,
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

    INDEX_STATEMENTS = """
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

    def __init__(self, database_target: str):
        self.database_target = str(database_target)
        self._pg_db: psycopg.AsyncConnection | None = None

    async def init(self) -> None:
        await self._init_postgres()

    async def _init_postgres(self) -> None:
        self._pg_db = await psycopg.AsyncConnection.connect(self.database_target, row_factory=dict_row)
        await self._execute_postgres_script(self.POSTGRES_SCHEMA)
        await self._execute_postgres_script(self.INDEX_STATEMENTS)

    async def _execute_postgres_script(self, script: str) -> None:
        if not self._pg_db:
            raise RuntimeError("Database not initialized. Call init() first.")
        async with self._pg_db.cursor() as cur:
            for statement in self._split_statements(script):
                await cur.execute(statement)
        await self._pg_db.commit()

    async def execute(self, query: str, params: tuple[Any, ...] = ()) -> None:
        await self._pg_execute(query, params)

    async def fetchone(self, query: str, params: tuple[Any, ...] = ()):
        return await self._pg_fetchone(query, params)

    async def fetchall(self, query: str, params: tuple[Any, ...] = ()):
        return await self._pg_fetchall(query, params)

    async def execute_fetchone(self, query: str, params: tuple[Any, ...] = ()):
        if not self._pg_db:
            raise RuntimeError("Database not initialized. Call init() first.")
        async with self._pg_db.cursor() as cur:
            await cur.execute(self._adapt_query(query), params)
            row = await cur.fetchone()
        await self._pg_db.commit()
        return row

    async def _pg_execute(self, query: str, params: tuple[Any, ...]) -> None:
        if not self._pg_db:
            raise RuntimeError("Database not initialized. Call init() first.")
        async with self._pg_db.cursor() as cur:
            await cur.execute(self._adapt_query(query), params)
        await self._pg_db.commit()

    async def _pg_fetchone(self, query: str, params: tuple[Any, ...]):
        if not self._pg_db:
            raise RuntimeError("Database not initialized. Call init() first.")
        async with self._pg_db.cursor() as cur:
            await cur.execute(self._adapt_query(query), params)
            return await cur.fetchone()

    async def _pg_fetchall(self, query: str, params: tuple[Any, ...]):
        if not self._pg_db:
            raise RuntimeError("Database not initialized. Call init() first.")
        async with self._pg_db.cursor() as cur:
            await cur.execute(self._adapt_query(query), params)
            return await cur.fetchall()

    def _adapt_query(self, query: str) -> str:
        return query.replace("?", "%s")

    def _split_statements(self, script: str) -> list[str]:
        return [statement.strip() for statement in script.split(";") if statement.strip()]

    async def close(self) -> None:
        if self._pg_db:
            await self._pg_db.close()
            self._pg_db = None
