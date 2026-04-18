from __future__ import annotations

import discord
from discord.ext import commands

from bot.utils.discord_utils import sanitize_channel_name


class VoiceCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @staticmethod
    def _build_channel_overwrites(category: discord.CategoryChannel, member: discord.Member) -> dict:
        """카테고리 권한은 유지하고 소유자에게만 추가 권한을 부여"""
        overwrites = {
            target: discord.PermissionOverwrite.from_pair(*overwrite.pair())
            for target, overwrite in category.overwrites.items()
        }
        owner_overwrite = overwrites.get(member, discord.PermissionOverwrite())
        owner_overwrite.update(
            view_channel=True,
            connect=True,
            manage_channels=True,
            move_members=True,
        )
        overwrites[member] = owner_overwrite
        return overwrites

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return
        await self.handle_create(member, after)
        await self.handle_auto_delete(before)

    async def handle_create(self, member: discord.Member, after: discord.VoiceState) -> None:
        """음성 채널 입장 시 개인 채널 생성 (예외 처리 포함)"""
        if not after.channel:
            return
        guild_id = member.guild.id
        if not self.bot.config_service.get(guild_id, "voice_create.enabled", False):
            return
        trigger_channel_id = int(self.bot.config_service.get(guild_id, "voice_create.trigger_channel_id", "0") or 0)
        category_id = int(self.bot.config_service.get(guild_id, "voice_create.category_id", "0") or 0)
        if after.channel.id != trigger_channel_id:
            return
        category = member.guild.get_channel(category_id)
        if not category or not isinstance(category, discord.CategoryChannel):
            return

        try:
            channel_name = sanitize_channel_name(member.display_name)
            overwrites = self._build_channel_overwrites(category, member)
            new_channel = await member.guild.create_voice_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                reason="LVP 임시 개인 음성 채널 생성",
            )
            await self.bot.voice_owner_service.add(member.guild.id, new_channel.id, member.id)
            await member.move_to(new_channel)
        except discord.Forbidden:
            # 봇 권한 부족
            import logging
            logging.getLogger(__name__).error(f"음성 채널 생성 권한 부족 (길드: {member.guild.id})")
        except Exception as e:
            # 기타 예외
            import logging
            logging.getLogger(__name__).exception(f"음성 채널 생성 중 오류: {e}")

    async def handle_auto_delete(self, before: discord.VoiceState) -> None:
        """빈 임시 채널 자동 삭제 (예외 처리 포함)"""
        if not before.channel:
            return
        guild_id = before.channel.guild.id
        if not self.bot.config_service.get(guild_id, "voice_create.auto_delete", True):
            return
        owner_id = await self.bot.voice_owner_service.get_owner(guild_id, before.channel.id)
        if owner_id is None:  # 소유권 미기록 채널
            return
        non_bot_members = [m for m in before.channel.members if not m.bot]
        if non_bot_members:
            return
        
        try:
            await before.channel.delete(reason="빈 임시 음성 채널 자동 삭제")
            await self.bot.voice_owner_service.remove(guild_id, before.channel.id)
        except discord.NotFound:
            # 채널이 이미 삭제됨
            await self.bot.voice_owner_service.remove(guild_id, before.channel.id)
        except Exception as e:
            # 기타 예외
            import logging
            logging.getLogger(__name__).exception(f"채널 삭제 중 오류: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceCog(bot))
