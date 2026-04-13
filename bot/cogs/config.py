from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.services.embed_service import EmbedService
from bot.utils.discord_utils import is_admin


class ConfigCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _ensure_guild_context(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            await interaction.response.send_message("서버에서만 사용할 수 있습니다.", ephemeral=True)
            return False
        return True

    setting = app_commands.Group(name="설정", description="봇 설정")
    voice_group = app_commands.Group(name="음성채널", description="음성 채널 설정", parent=setting)

    @setting.command(name="경고채널", description="경고 로그 채널 설정")
    async def warning_channel(self, interaction: discord.Interaction, 채널: discord.TextChannel):
        if not await self._ensure_guild_context(interaction):
            return
        if not is_admin(interaction.user):
            return await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True)
        await self.bot.config_service.set(interaction.guild.id, "warning_channel_id", str(채널.id), interaction.user.id)
        await interaction.response.send_message(embed=EmbedService.config_result("warning_channel_id", str(채널.id)), ephemeral=True)

    @setting.command(name="인증채널", description="인증 공지 채널 설정")
    async def auth_channel(self, interaction: discord.Interaction, 채널: discord.TextChannel):
        if not await self._ensure_guild_context(interaction):
            return
        if not is_admin(interaction.user):
            return await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True)
        await self.bot.config_service.set(interaction.guild.id, "auth_channel_id", str(채널.id), interaction.user.id)
        await interaction.response.send_message(embed=EmbedService.config_result("auth_channel_id", str(채널.id)), ephemeral=True)

    @setting.command(name="인증완료역할", description="인증 완료 역할 설정")
    async def auth_completed_role(self, interaction: discord.Interaction, 역할: discord.Role):
        if not await self._ensure_guild_context(interaction):
            return
        if not is_admin(interaction.user):
            return await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True)
        await self.bot.config_service.set(interaction.guild.id, "auth_completed_role_id", str(역할.id), interaction.user.id)
        await interaction.response.send_message(embed=EmbedService.config_result("auth_completed_role_id", str(역할.id)), ephemeral=True)

    @setting.command(name="지인역할", description="자동 경고 제외용 지인 역할 설정")
    async def acquaintance_role(self, interaction: discord.Interaction, 역할: discord.Role):
        if not await self._ensure_guild_context(interaction):
            return
        if not is_admin(interaction.user):
            return await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True)
        await self.bot.config_service.set(interaction.guild.id, "acquaintance_role_id", str(역할.id), interaction.user.id)
        await interaction.response.send_message(embed=EmbedService.config_result("acquaintance_role_id", str(역할.id)), ephemeral=True)

    @setting.command(name="봇역할", description="자동 경고 제외용 봇 역할 설정")
    async def bot_role(self, interaction: discord.Interaction, 역할: discord.Role):
        if not await self._ensure_guild_context(interaction):
            return
        if not is_admin(interaction.user):
            return await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True)
        await self.bot.config_service.set(interaction.guild.id, "bot_role_id", str(역할.id), interaction.user.id)
        await interaction.response.send_message(embed=EmbedService.config_result("bot_role_id", str(역할.id)), ephemeral=True)

    @setting.command(name="경고역할1", description="경고 1회 역할 설정")
    async def warning_role_1(self, interaction: discord.Interaction, 역할: discord.Role):
        if not await self._ensure_guild_context(interaction):
            return
        if not is_admin(interaction.user):
            return await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True)
        await self.bot.config_service.set(interaction.guild.id, "warning_role_1_id", str(역할.id), interaction.user.id)
        await interaction.response.send_message(embed=EmbedService.config_result("warning_role_1_id", str(역할.id)), ephemeral=True)

    @setting.command(name="경고역할2", description="경고 2회 역할 설정")
    async def warning_role_2(self, interaction: discord.Interaction, 역할: discord.Role):
        if not await self._ensure_guild_context(interaction):
            return
        if not is_admin(interaction.user):
            return await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True)
        await self.bot.config_service.set(interaction.guild.id, "warning_role_2_id", str(역할.id), interaction.user.id)
        await interaction.response.send_message(embed=EmbedService.config_result("warning_role_2_id", str(역할.id)), ephemeral=True)

    @setting.command(name="경고역할3", description="경고 3회 역할 설정")
    async def warning_role_3(self, interaction: discord.Interaction, 역할: discord.Role):
        if not await self._ensure_guild_context(interaction):
            return
        if not is_admin(interaction.user):
            return await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True)
        await self.bot.config_service.set(interaction.guild.id, "warning_role_3_id", str(역할.id), interaction.user.id)
        await interaction.response.send_message(embed=EmbedService.config_result("warning_role_3_id", str(역할.id)), ephemeral=True)

    @setting.command(name="테스트자동경고", description="현재 서버에서 자동 경고를 즉시 실행")
    async def test_auto_warning(self, interaction: discord.Interaction):
        if not await self._ensure_guild_context(interaction):
            return
        if not is_admin(interaction.user):
            return await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        try:
            await self.bot.scheduler_service.run_auto_warning_for_guild(interaction.guild)
            await interaction.followup.send("현재 서버 자동 경고 테스트 실행이 완료되었습니다.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"자동 경고 테스트 실행 중 오류가 발생했습니다: {e}", ephemeral=True)

    @setting.command(name="테스트안내", description="현재 서버에서 인증 안내 메시지를 즉시 전송")
    async def test_notice(self, interaction: discord.Interaction):
        if not await self._ensure_guild_context(interaction):
            return
        if not is_admin(interaction.user):
            return await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        try:
            await self.bot.scheduler_service.send_notice_for_guild(interaction.guild)
            await interaction.followup.send("현재 서버 인증 안내 테스트 전송이 완료되었습니다.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"인증 안내 테스트 전송 중 오류가 발생했습니다: {e}", ephemeral=True)

    @voice_group.command(name="활성화", description="음성 채널 생성 기능 활성화 여부")
    @app_commands.describe(값="ON 또는 OFF")
    async def voice_enabled(self, interaction: discord.Interaction, 값: str):
        if not await self._ensure_guild_context(interaction):
            return
        if not is_admin(interaction.user):
            return await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True)
        normalized = 값.strip().upper()
        if normalized not in {"ON", "OFF"}:
            return await interaction.response.send_message("ON 또는 OFF만 입력할 수 있습니다.", ephemeral=True)
        value = normalized == "ON"
        await self.bot.config_service.set(interaction.guild.id, "voice_create.enabled", value, interaction.user.id)
        await interaction.response.send_message(embed=EmbedService.config_result("voice_create.enabled", str(value)), ephemeral=True)

    @voice_group.command(name="트리거", description="음성 채널 생성 트리거 채널")
    async def voice_trigger(self, interaction: discord.Interaction, 채널: discord.VoiceChannel):
        if not await self._ensure_guild_context(interaction):
            return
        if not is_admin(interaction.user):
            return await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True)
        await self.bot.config_service.set(interaction.guild.id, "voice_create.trigger_channel_id", str(채널.id), interaction.user.id)
        await interaction.response.send_message(embed=EmbedService.config_result("voice_create.trigger_channel_id", str(채널.id)), ephemeral=True)

    @voice_group.command(name="카테고리", description="음성 채널 생성 카테고리")
    async def voice_category(self, interaction: discord.Interaction, 카테고리: discord.CategoryChannel):
        if not await self._ensure_guild_context(interaction):
            return
        if not is_admin(interaction.user):
            return await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True)
        await self.bot.config_service.set(interaction.guild.id, "voice_create.category_id", str(카테고리.id), interaction.user.id)
        await interaction.response.send_message(embed=EmbedService.config_result("voice_create.category_id", str(카테고리.id)), ephemeral=True)

    @voice_group.command(name="자동삭제", description="자동 삭제 여부")
    @app_commands.describe(값="ON 또는 OFF")
    async def voice_auto_delete(self, interaction: discord.Interaction, 값: str):
        if not await self._ensure_guild_context(interaction):
            return
        if not is_admin(interaction.user):
            return await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True)
        normalized = 값.strip().upper()
        if normalized not in {"ON", "OFF"}:
            return await interaction.response.send_message("ON 또는 OFF만 입력할 수 있습니다.", ephemeral=True)
        value = normalized == "ON"
        await self.bot.config_service.set(interaction.guild.id, "voice_create.auto_delete", value, interaction.user.id)
        await interaction.response.send_message(embed=EmbedService.config_result("voice_create.auto_delete", str(value)), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    """discord.py 2.4.0+ Cog 자동 등록"""
    await bot.add_cog(ConfigCog(bot))
