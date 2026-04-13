from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.services.embed_service import EmbedService
from bot.services.warning_service import WarningService
from bot.utils.discord_utils import is_admin
from bot.utils.time_utils import format_kst


class WarningCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.warning_service = WarningService(bot)

    warning = app_commands.Group(name="경고", description="경고 관리")

    async def _send_log(self, guild: discord.Guild, embed: discord.Embed) -> None:
        channel_id = int(self.bot.config_service.get(guild.id, "warning_channel_id", "0") or 0)
        channel = guild.get_channel(channel_id)
        if channel:
            await channel.send(embed=embed)

    @warning.command(name="부여", description="경고를 부여합니다")
    @app_commands.describe(유저="대상 유저", 사유="경고 사유")
    async def add(self, interaction: discord.Interaction, 유저: discord.Member, 사유: str):
        if interaction.guild is None:
            return await interaction.response.send_message("서버에서만 사용할 수 있습니다.", ephemeral=True)
        if not is_admin(interaction.user):
            return await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        result = await self.warning_service.add_warning(interaction.guild, 유저, interaction.user, 사유, "ADD")
        embed = EmbedService.warning_log("경고 부여", interaction.user.mention, 유저.mention, 사유, result.warning_count, result.created_at, result.kicked)
        await self._send_log(interaction.guild, embed)
        await interaction.followup.send(f"{유저.mention}에게 경고를 부여했습니다. 현재 {result.warning_count}회입니다.", ephemeral=True)

    @warning.command(name="회수", description="경고를 회수합니다")
    @app_commands.describe(유저="대상 유저", 사유="회수 사유")
    async def remove(self, interaction: discord.Interaction, 유저: discord.Member, 사유: str):
        if interaction.guild is None:
            return await interaction.response.send_message("서버에서만 사용할 수 있습니다.", ephemeral=True)
        if not is_admin(interaction.user):
            return await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        result = await self.warning_service.remove_warning(interaction.guild, 유저, interaction.user, 사유)
        embed = EmbedService.warning_log("경고 회수", interaction.user.mention, 유저.mention, 사유, result.warning_count, result.created_at, result.kicked)
        await self._send_log(interaction.guild, embed)
        await interaction.followup.send(f"{유저.mention}의 경고를 회수했습니다. 현재 {result.warning_count}회입니다.", ephemeral=True)

    @warning.command(name="조회", description="경고 상태를 조회합니다")
    @app_commands.describe(유저="비워두면 본인 조회")
    async def check(self, interaction: discord.Interaction, 유저: discord.Member | None = None):
        if interaction.guild is None:
            return await interaction.response.send_message("서버에서만 사용할 수 있습니다.", ephemeral=True)
        target = 유저 or interaction.user
        if 유저 is not None and not is_admin(interaction.user):
            return await interaction.response.send_message("타인 조회는 관리자만 가능합니다.", ephemeral=True)
        current_count, history = await self.warning_service.get_warning_summary(interaction.guild.id, target.id)
        lines = [f"현재 경고 횟수: {current_count}", "", "이력:"]
        if not history:
            lines.append("- 이력이 없습니다.")
        else:
            for item in history[:20]:
                actor = f"<@{item['actor_discord_id']}>" if item["actor_discord_id"] else "SYSTEM"
                lines.append(
                    f"- [{item['created_at']}] {item['action']} | 처리자: {actor} | 사유: {item['reason']} | 처리 후 경고: {item['total_warning_count']}"
                )
        await interaction.response.send_message("\n".join(lines), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    """discord.py 2.4.0+ Cog 자동 등록"""
    await bot.add_cog(WarningCog(bot))
