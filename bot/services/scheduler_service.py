from __future__ import annotations

import logging
from datetime import datetime, timedelta

import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bot.services.warning_service import WarningResult, WarningService
from bot.utils.time_utils import KST, get_notice_target_date, get_previous_period, is_auto_warning_run_time, now_kst

logger = logging.getLogger(__name__)


class SchedulerService:
    def __init__(self, bot: discord.ext.commands.Bot) -> None:
        """스케줄러 서비스 초기화"""
        self.bot = bot
        self.scheduler = AsyncIOScheduler(timezone=KST)

    def is_auth_schedule_enabled(self, guild_id: int) -> bool:
        return bool(self.bot.config_service.get(guild_id, "auth_schedule_enabled", True))

    def _build_auto_warning_summary_embed(
        self,
        period_key: str,
        results: list[WarningResult],
    ) -> discord.Embed:
        embed = discord.Embed(
            description=f"{period_key} 자동 경고 집계가 완료되었습니다.",
            timestamp=now_kst(),
        )
        if not results:
            embed.add_field(name="처리 결과", value="이번 자동 경고 대상이 없습니다.", inline=False)
            embed.set_footer(text="소다봇 자동 경고 요약")
            return embed

        warning_1: list[str] = []
        warning_2: list[str] = []
        warning_3: list[str] = []

        for result in results:
            entry = f"{result.target_display_name} (ID: {result.target_discord_id})"
            if result.warning_count == 1:
                warning_1.append(entry)
            elif result.warning_count == 2:
                warning_2.append(entry)
            else:
                status = "추방 완료" if result.kicked else "추방 시도 필요"
                warning_3.append(f"{entry} ({status})")

        embed.add_field(name="경고 1회", value="\n".join(warning_1) if warning_1 else "-", inline=False)
        embed.add_field(name="경고 2회", value="\n".join(warning_2) if warning_2 else "-", inline=False)
        embed.add_field(name="경고 3회(추방자)", value="\n".join(warning_3) if warning_3 else "-", inline=False)
        embed.set_footer(text="소다봇 자동 경고 요약")
        return embed

    async def start(self) -> None:
        """APScheduler 시작 (매분 실행)"""
        self.scheduler.add_job(self.tick, CronTrigger(minute="*"))
        self.scheduler.start()
        logger.info("✅ 스케줄러 시작됨")

    def stop(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("🛑 스케줄러 종료됨")

    async def tick(self) -> None:
        now = now_kst().replace(second=0, microsecond=0)
        if is_auto_warning_run_time(now):
            await self.run_auto_warning_for_all_guilds()
        if get_notice_target_date(now):
            await self.send_notice_for_all_guilds()

    async def run_auto_warning_for_all_guilds(self) -> None:
        for guild in self.bot.guilds:
            if not self.is_auth_schedule_enabled(guild.id):
                logger.info("auto warning skipped guild=%s reason=auth_schedule_disabled", guild.id)
                continue
            try:
                await self._run_auto_warning(guild)
            except Exception as e:
                logger.exception("auto warning failed for guild=%s type=%s", guild.id, type(e).__name__)

    async def run_auto_warning_for_guild(self, guild: discord.Guild) -> None:
        await self._run_auto_warning(guild)

    async def send_notice_for_all_guilds(self) -> None:
        for guild in self.bot.guilds:
            if not self.is_auth_schedule_enabled(guild.id):
                logger.info("notice skipped guild=%s reason=auth_schedule_disabled", guild.id)
                continue
            try:
                await self._send_notice(guild)
            except Exception as e:
                logger.exception("notice failed for guild=%s type=%s", guild.id, type(e).__name__)

    async def send_notice_for_guild(self, guild: discord.Guild) -> None:
        await self._send_notice(guild)

    async def _run_auto_warning(self, guild: discord.Guild) -> None:
        warning_service = WarningService(self.bot)
        now = now_kst()
        previous_period = get_previous_period(now)
        join_exempt_before = now - timedelta(days=7)
        auth_role_id = int(self.bot.config_service.get(guild.id, "auth_completed_role_id", "0") or 0)
        acquaintance_role_id = int(self.bot.config_service.get(guild.id, "acquaintance_role_id", "0") or 0)
        bot_role_id = int(self.bot.config_service.get(guild.id, "bot_role_id", "0") or 0)
        warning_channel_id = int(self.bot.config_service.get(guild.id, "warning_channel_id", "0") or 0)
        warning_channel = guild.get_channel(warning_channel_id)

        if auth_role_id <= 0:
            logger.warning("auto warning skipped guild=%s reason=missing auth_completed_role_id", guild.id)
            return
        if guild.get_role(auth_role_id) is None:
            logger.warning("auto warning skipped guild=%s reason=auth_completed_role_not_found id=%s", guild.id, auth_role_id)
            return
        if warning_channel_id <= 0:
            logger.warning("warning channel is not configured guild=%s; auto warning continues without log embed", guild.id)
        elif warning_channel is None:
            logger.warning("warning channel not found guild=%s channel_id=%s; auto warning continues without log embed", guild.id, warning_channel_id)

        processed_results: list[WarningResult] = []

        for member in guild.members:
            if member.bot:
                continue
            if member.joined_at and member.joined_at.astimezone(KST) > join_exempt_before:
                continue
            role_ids = {role.id for role in member.roles}
            if auth_role_id and auth_role_id in role_ids:
                continue
            if acquaintance_role_id and acquaintance_role_id in role_ids:
                continue
            if bot_role_id and bot_role_id in role_ids:
                continue
            if await warning_service.already_auto_warned(guild.id, member.id, previous_period.key):
                continue
            result = await warning_service.add_warning(
                guild,
                member,
                None,
                f"{previous_period.key} 인증 미완료",
                "AUTO_ADD",
                previous_period.key,
            )
            processed_results.append(result)
            if warning_channel:
                from bot.services.embed_service import EmbedService
                await warning_channel.send(embed=EmbedService.warning_log("자동 경고", "SYSTEM", member.mention, result.reason, result.warning_count, result.created_at, result.kicked))

        await self._clear_auth_role(guild, auth_role_id)

        earlier_reference = datetime(
            previous_period.year,
            previous_period.month,
            previous_period.start_day,
            12,
            0,
            tzinfo=KST,
        )
        earlier_period = get_previous_period(earlier_reference)
        for member in guild.members:
            if member.bot:
                continue
            await self.bot.auth_service.apply_consecutive_auth_reward(
                member,
                previous_period.key,
                earlier_period.key,
            )

        if warning_channel:
            await warning_channel.send(embed=self._build_auto_warning_summary_embed(previous_period.key, processed_results))

    async def _clear_auth_role(self, guild: discord.Guild, auth_role_id: int) -> None:
        if not auth_role_id:
            return
        role = guild.get_role(auth_role_id)
        if not role:
            return
        for member in list(role.members):
            await member.remove_roles(role, reason="인증 기간 초기화")

    async def _send_notice(self, guild: discord.Guild) -> None:
        auth_channel_id = int(self.bot.config_service.get(guild.id, "auth_channel_id", "0") or 0)
        if auth_channel_id <= 0:
            logger.warning("notice skipped guild=%s reason=missing auth_channel_id", guild.id)
            return
        channel = guild.get_channel(auth_channel_id)
        if not channel:
            logger.warning("notice skipped guild=%s reason=auth_channel_not_found id=%s", guild.id, auth_channel_id)
            return
        await channel.send("@everyone 인증 기간 종료 3일 전입니다. 기간 내 인증을 완료해주세요.")
