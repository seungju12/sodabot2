from __future__ import annotations

import discord

from bot.services.embed_service import EmbedService
from bot.services.warning_service import WarningService
from bot.utils.time_utils import format_kst, get_period_for_date, get_previous_period, now_kst


class AuthService:
    AUTH_STREAK_REWARD_REASON = "2회 연속 기간 인증 보상"

    def __init__(self, bot: discord.ext.commands.Bot) -> None:
        self.bot = bot
        self.db = bot.db
        self.config = bot.config_service
        self.warning_service = WarningService(bot)

    def get_current_period_key(self) -> str:
        return get_period_for_date(now_kst()).key

    async def set_current_period_authenticated(
        self,
        guild_id: int,
        user_discord_id: int,
        is_authenticated: bool,
        updated_by_discord_id: int | None = None,
    ) -> None:
        now = format_kst(now_kst())
        period_key = self.get_current_period_key()
        await self.db.execute(
            """
            INSERT INTO auth_period_status(guild_id, user_discord_id, period_key, is_authenticated, updated_by_discord_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(guild_id, user_discord_id, period_key) DO UPDATE SET
              is_authenticated = excluded.is_authenticated,
              updated_by_discord_id = excluded.updated_by_discord_id,
              updated_at = excluded.updated_at
            """,
            (
                str(guild_id),
                str(user_discord_id),
                period_key,
                1 if is_authenticated else 0,
                str(updated_by_discord_id) if updated_by_discord_id else None,
                now,
                now,
            ),
        )

    async def is_authenticated_for_period(self, guild_id: int, user_discord_id: int, period_key: str) -> bool:
        row = await self.db.fetchone(
            "SELECT is_authenticated FROM auth_period_status WHERE guild_id = ? AND user_discord_id = ? AND period_key = ? LIMIT 1",
            (str(guild_id), str(user_discord_id), period_key),
        )
        return bool(row and int(row["is_authenticated"]) == 1)

    async def is_authenticated_for_current_period(self, guild_id: int, user_discord_id: int) -> bool:
        return await self.is_authenticated_for_period(guild_id, user_discord_id, self.get_current_period_key())

    async def _already_rewarded_for_period(self, guild_id: int, user_discord_id: int, period_key: str) -> bool:
        row = await self.db.fetchone(
            "SELECT 1 FROM warning_history WHERE guild_id = ? AND target_discord_id = ? AND action = 'REMOVE' AND reason = ? AND period_key = ? LIMIT 1",
            (str(guild_id), str(user_discord_id), self.AUTH_STREAK_REWARD_REASON, period_key),
        )
        return row is not None

    async def apply_consecutive_auth_reward(self, member: discord.Member) -> None:
        current_period = get_period_for_date(now_kst())
        previous_period = get_previous_period(now_kst())
        if not await self.is_authenticated_for_period(member.guild.id, member.id, current_period.key):
            return
        if not await self.is_authenticated_for_period(member.guild.id, member.id, previous_period.key):
            return
        if await self._already_rewarded_for_period(member.guild.id, member.id, current_period.key):
            return
        user = await self.warning_service.get_or_create_user(member.guild.id, member.id)
        if int(user["warning_count"]) <= 0:
            return
        result = await self.warning_service.remove_warning(
            member.guild,
            member,
            None,
            self.AUTH_STREAK_REWARD_REASON,
            current_period.key,
        )
        await self._send_warning_log(
            member.guild,
            EmbedService.warning_log(
                "자동 경고 회수",
                "SYSTEM",
                member.mention,
                self.AUTH_STREAK_REWARD_REASON,
                result.warning_count,
                result.created_at,
                result.kicked,
            ),
        )

    async def _send_warning_log(self, guild: discord.Guild, embed: discord.Embed) -> None:
        channel_id = int(self.config.get(guild.id, "warning_channel_id", "0") or 0)
        channel = guild.get_channel(channel_id)
        if channel:
            await channel.send(embed=embed)

    async def restore_auth_role_on_join(self, member: discord.Member) -> None:
        auth_role_id = int(self.config.get(member.guild.id, "auth_completed_role_id", "0") or 0)
        if auth_role_id <= 0:
            return
        auth_role = member.guild.get_role(auth_role_id)
        if auth_role is None:
            return
        if auth_role in member.roles:
            return
        if not await self.is_authenticated_for_current_period(member.guild.id, member.id):
            return
        await member.add_roles(auth_role, reason="현재 기간 인증 완료 상태 복구")

    async def handle_auth_role_change(self, before: discord.Member, after: discord.Member) -> None:
        auth_role_id = int(self.config.get(after.guild.id, "auth_completed_role_id", "0") or 0)
        if auth_role_id <= 0:
            return
        before_has_role = any(role.id == auth_role_id for role in before.roles)
        after_has_role = any(role.id == auth_role_id for role in after.roles)
        if before_has_role == after_has_role:
            return
        await self.set_current_period_authenticated(after.guild.id, after.id, after_has_role)
        if after_has_role:
            await self.apply_consecutive_auth_reward(after)

    async def sync_existing_auth_role_members(self, guild: discord.Guild) -> None:
        auth_role_id = int(self.config.get(guild.id, "auth_completed_role_id", "0") or 0)
        if auth_role_id <= 0:
            return
        auth_role = guild.get_role(auth_role_id)
        if auth_role is None:
            return
        for member in auth_role.members:
            if member.bot:
                continue
            await self.set_current_period_authenticated(guild.id, member.id, True)
            await self.apply_consecutive_auth_reward(member)
