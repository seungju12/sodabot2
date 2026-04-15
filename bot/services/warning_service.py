from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import discord

from bot.utils.time_utils import format_kst, now_kst

ActionType = Literal["ADD", "REMOVE", "AUTO_ADD", "KICK", "RESET"]


@dataclass(slots=True)
class WarningResult:
    user_id: int
    warning_count: int
    action: ActionType
    actor_discord_id: int | None
    target_discord_id: int
    target_display_name: str
    reason: str
    created_at: str
    kicked: bool = False


class WarningService:
    def __init__(self, bot: discord.ext.commands.Bot) -> None:
        """경고 서비스 초기화"""
        self.bot = bot
        self.db = bot.db
        self.config = bot.config_service

    def _user_key(self, guild_id: int, discord_id: int) -> str:
        return f"{guild_id}:{discord_id}"

    async def get_or_create_user(self, guild_id: int, discord_id: int) -> dict:
        user_key = self._user_key(guild_id, discord_id)
        row = await self.db.fetchone(
            "SELECT * FROM users WHERE discord_id = ?",
            (user_key,),
        )
        if row:
            return row
        now = format_kst(now_kst())
        await self.db.execute(
            "INSERT INTO users(discord_id, guild_id, warning_count, created_at, updated_at) VALUES (?, ?, 0, ?, ?)",
            (user_key, str(guild_id), now, now),
        )
        return await self.db.fetchone("SELECT * FROM users WHERE discord_id = ?", (user_key,))

    async def add_warning(self, guild: discord.Guild, target: discord.Member, actor: discord.Member | None, reason: str, action: ActionType, period_key: str | None = None) -> WarningResult:
        user = await self.get_or_create_user(guild.id, target.id)
        new_count = int(user["warning_count"]) + 1
        now = format_kst(now_kst())
        user_key = self._user_key(guild.id, target.id)

        await self.db.execute(
            "UPDATE users SET warning_count = ?, updated_at = ? WHERE discord_id = ?",
            (new_count, now, user_key),
        )
        refreshed = await self.db.fetchone("SELECT id FROM users WHERE discord_id = ?", (user_key,))
        await self.db.execute(
            "INSERT INTO warning_history(user_id, guild_id, action, actor_discord_id, target_discord_id, reason, total_warning_count, period_key, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (refreshed["id"], str(guild.id), action, str(actor.id) if actor else None, str(target.id), reason, new_count, period_key, now),
        )

        await self.sync_warning_roles(guild.id, target, new_count)
        kicked = False
        if new_count >= 3:
            kicked = await self.kick_member(guild.id, guild, target, actor, "경고 3회 누적")
        return WarningResult(target.id, new_count, action, actor.id if actor else None, target.id, target.display_name, reason, now, kicked)

    async def remove_warning(self, guild: discord.Guild, target: discord.Member, actor: discord.Member | None, reason: str, period_key: str | None = None) -> WarningResult:
        user = await self.get_or_create_user(guild.id, target.id)
        new_count = max(int(user["warning_count"]) - 1, 0)
        now = format_kst(now_kst())
        user_key = self._user_key(guild.id, target.id)
        await self.db.execute(
            "UPDATE users SET warning_count = ?, updated_at = ? WHERE discord_id = ?",
            (new_count, now, user_key),
        )
        refreshed = await self.db.fetchone("SELECT id FROM users WHERE discord_id = ?", (user_key,))
        await self.db.execute(
            "INSERT INTO warning_history(user_id, guild_id, action, actor_discord_id, target_discord_id, reason, total_warning_count, period_key, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (refreshed["id"], str(guild.id), "REMOVE", str(actor.id) if actor else None, str(target.id), reason, new_count, period_key, now),
        )
        await self.sync_warning_roles(guild.id, target, new_count)
        return WarningResult(target.id, new_count, "REMOVE", actor.id if actor else None, target.id, target.display_name, reason, now, False)

    async def handle_member_join(self, member: discord.Member) -> None:
        user = await self.get_or_create_user(member.guild.id, member.id)
        latest_action = await self._get_latest_action(member.guild.id, member.id)
        if latest_action == "KICK":
            await self.reset_after_kick_rejoin(member, user)
            return
        await self.sync_warning_roles(member.guild.id, member, int(user["warning_count"]))

    async def reset_after_kick_rejoin(self, member: discord.Member, user: dict | None = None) -> None:
        user = user or await self.get_or_create_user(member.guild.id, member.id)
        now = format_kst(now_kst())
        user_key = self._user_key(member.guild.id, member.id)
        await self.db.execute(
            "UPDATE users SET warning_count = ?, updated_at = ? WHERE discord_id = ?",
            (0, now, user_key),
        )
        await self.db.execute(
            "INSERT INTO warning_history(user_id, guild_id, action, actor_discord_id, target_discord_id, reason, total_warning_count, period_key, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user["id"], str(member.guild.id), "RESET", None, str(member.id), "강퇴 후 재입장으로 인한 경고 초기화", 0, None, now),
        )
        await self.sync_warning_roles(member.guild.id, member, 0)

    async def _get_latest_action(self, guild_id: int, target_discord_id: int) -> str | None:
        row = await self.db.fetchone(
            "SELECT action FROM warning_history WHERE guild_id = ? AND target_discord_id = ? ORDER BY id DESC LIMIT 1",
            (str(guild_id), str(target_discord_id)),
        )
        return str(row["action"]) if row else None

    async def already_auto_warned(self, guild_id: int, target_discord_id: int, period_key: str) -> bool:
        row = await self.db.fetchone(
            "SELECT 1 FROM warning_history WHERE guild_id = ? AND target_discord_id = ? AND action = 'AUTO_ADD' AND period_key = ? LIMIT 1",
            (str(guild_id), str(target_discord_id), period_key),
        )
        return row is not None

    async def get_warning_summary(self, guild_id: int, target_discord_id: int):
        user = await self.get_or_create_user(guild_id, target_discord_id)
        history = await self.db.fetchall(
            "SELECT action, actor_discord_id, target_discord_id, reason, total_warning_count, period_key, created_at FROM warning_history WHERE guild_id = ? AND target_discord_id = ? ORDER BY id DESC",
            (str(guild_id), str(target_discord_id)),
        )
        return int(user["warning_count"]), history

    async def sync_warning_roles(self, guild_id: int, member: discord.Member, warning_count: int) -> None:
        role_ids = {
            1: int(self.config.get(guild_id, "warning_role_1_id", "0") or 0),
            2: int(self.config.get(guild_id, "warning_role_2_id", "0") or 0),
            3: int(self.config.get(guild_id, "warning_role_3_id", "0") or 0),
        }
        managed_roles = [member.guild.get_role(rid) for rid in role_ids.values() if rid]
        managed_roles = [r for r in managed_roles if r]
        if managed_roles:
            await member.remove_roles(*[r for r in managed_roles if r in member.roles], reason="경고 역할 동기화")
        target_role = member.guild.get_role(role_ids.get(min(warning_count, 3), 0)) if warning_count > 0 else None
        if target_role:
            await member.add_roles(target_role, reason="경고 역할 동기화")

    async def kick_member(self, guild_id: int, guild: discord.Guild, target: discord.Member, actor: discord.Member | None, reason: str) -> bool:
        try:
            await guild.kick(target, reason=reason)
            now = format_kst(now_kst())
            user = await self.get_or_create_user(guild_id, target.id)
            await self.db.execute(
                "INSERT INTO warning_history(user_id, guild_id, action, actor_discord_id, target_discord_id, reason, total_warning_count, period_key, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user["id"], str(guild_id), "KICK", str(actor.id) if actor else None, str(target.id), reason, int(user["warning_count"]), None, now),
            )
            return True
        except (discord.Forbidden, discord.HTTPException):
            return False
