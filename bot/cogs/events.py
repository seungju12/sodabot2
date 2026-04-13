from __future__ import annotations

import discord
from discord.ext import commands

from bot.services.auth_service import AuthService
from bot.services.warning_service import WarningService


class EventCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.auth_service = AuthService(bot)
        self.warning_service = WarningService(bot)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self.warning_service.handle_member_join(member)
        await self.auth_service.restore_auth_role_on_join(member)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        await self.auth_service.handle_auth_role_change(before, after)


async def setup(bot: commands.Bot):
    await bot.add_cog(EventCog(bot))
