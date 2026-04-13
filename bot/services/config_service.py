from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bot.services.db import Database
from bot.utils.time_utils import format_kst, now_kst


class ConfigService:
    def __init__(self, db: Database, default_config_path: Path) -> None:
        self.db = db
        self.default_config_path = default_config_path
        self.cache: dict[int, dict[str, Any]] = {}
        self.defaults: dict[str, Any] = {}

    async def init(self) -> None:
        self.defaults = json.loads(self.default_config_path.read_text(encoding="utf-8"))
        await self.reload_cache()

    async def reload_cache(self) -> None:
        rows = await self.db.fetchall("SELECT key, value, value_type FROM config")
        new_cache: dict[int, dict[str, Any]] = {}
        for row in rows:
            key = row["key"]
            parsed = self._parse_scoped_key(key)
            if not parsed:
                continue
            guild_id, inner_key = parsed
            guild_cache = new_cache.setdefault(guild_id, {})
            guild_cache[inner_key] = self._decode(row["value"], row["value_type"])
        self.cache = new_cache

    async def ensure_guild_defaults(self, guild_id: int) -> None:
        guild_cache = self.cache.setdefault(guild_id, {})
        now = format_kst(now_kst())
        for key, value in self.defaults.items():
            if key in guild_cache:
                continue
            value_type = self._type_name(value)
            scoped_key = self._scoped_key(guild_id, key)
            await self.db.execute(
                """
                INSERT INTO config(key, guild_id, value, value_type, updated_by_discord_id, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(key) DO NOTHING
                """,
                (scoped_key, str(guild_id), json.dumps(value), value_type, None, now),
            )
            guild_cache[key] = value

    def get(self, guild_id: int, key: str, default: Any = None) -> Any:
        guild_cache = self.cache.get(guild_id, {})
        if key in guild_cache:
            return guild_cache[key]
        if key in self.defaults:
            return self.defaults[key]
        return default

    async def set(self, guild_id: int, key: str, value: Any, updated_by_discord_id: int | None) -> None:
        value_type = self._type_name(value)
        scoped_key = self._scoped_key(guild_id, key)
        await self.db.execute(
            """
            INSERT INTO config(key, guild_id, value, value_type, updated_by_discord_id, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
              guild_id = excluded.guild_id,
              value = excluded.value,
              value_type = excluded.value_type,
              updated_by_discord_id = excluded.updated_by_discord_id,
              updated_at = excluded.updated_at
            """,
            (scoped_key, str(guild_id), json.dumps(value), value_type, str(updated_by_discord_id) if updated_by_discord_id else None, format_kst(now_kst())),
        )
        guild_cache = self.cache.setdefault(guild_id, {})
        guild_cache[key] = value

    def _scoped_key(self, guild_id: int, key: str) -> str:
        return f"g:{guild_id}:{key}"

    def _parse_scoped_key(self, key: str) -> tuple[int, str] | None:
        # Expected: g:<guild_id>:<key>
        if not key.startswith("g:"):
            return None
        parts = key.split(":", 2)
        if len(parts) != 3:
            return None
        prefix, guild_id_text, inner_key = parts
        if prefix != "g":
            return None
        try:
            return int(guild_id_text), inner_key
        except ValueError:
            return None

    def _type_name(self, value: Any) -> str:
        if isinstance(value, bool):
            return "bool"
        if isinstance(value, int):
            return "int"
        return "str"

    def _decode(self, raw: str, value_type: str) -> Any:
        value = json.loads(raw)
        if value_type == "bool":
            return bool(value)
        if value_type == "int":
            return int(value)
        return value
