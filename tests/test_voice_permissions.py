"""음성 채널 동작 점검용 유지 테스트.

이 파일은 운영 중 자동 실행되지 않으며,
필요할 때 수동 점검용으로 다시 사용할 수 있다.
"""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord

from bot.cogs.voice import VoiceCog


class BuildVoiceChannelOverwritesTests(unittest.TestCase):
    def test_category_permissions_are_preserved_for_everyone_else(self):
        default_role = object()
        member = object()
        category = SimpleNamespace(
            overwrites={
                default_role: discord.PermissionOverwrite(view_channel=False, connect=False),
            }
        )

        overwrites = VoiceCog._build_channel_overwrites(category, member)

        self.assertFalse(overwrites[default_role].view_channel)
        self.assertFalse(overwrites[default_role].connect)
        self.assertIsNot(overwrites[default_role], category.overwrites[default_role])
        self.assertTrue(overwrites[member].manage_channels)
        self.assertTrue(overwrites[member].move_members)


class VoiceChannelCreationBehaviorTests(unittest.IsolatedAsyncioTestCase):
    """나중에 음성 채널 생성 흐름을 빠르게 점검하기 위한 테스트."""

    async def test_existing_owned_channel_is_not_reused_and_new_channel_is_created(self):
        trigger_channel = SimpleNamespace(id=123)
        category = MagicMock(spec=discord.CategoryChannel)
        category.overwrites = {}
        new_channel = SimpleNamespace(id=777)

        guild = MagicMock()
        guild.id = 1
        guild.create_voice_channel = AsyncMock(return_value=new_channel)
        guild.get_channel.side_effect = lambda channel_id: {
            456: category,
            999: SimpleNamespace(id=999),
        }.get(channel_id)

        member = MagicMock()
        member.guild = guild
        member.display_name = "Tester"
        member.move_to = AsyncMock()
        member.bot = False
        member.id = 42
        after = SimpleNamespace(channel=trigger_channel)

        config_values = {
            "voice_create.enabled": True,
            "voice_create.trigger_channel_id": "123",
            "voice_create.category_id": "456",
        }
        config_service = SimpleNamespace(get=lambda guild_id, key, default=None: config_values.get(key, default))
        voice_owner_service = SimpleNamespace(
            get_owned_channel_id=AsyncMock(return_value=999),
            add=AsyncMock(),
            remove=AsyncMock(),
        )
        bot = SimpleNamespace(config_service=config_service, voice_owner_service=voice_owner_service)

        cog = VoiceCog(bot)
        await cog.handle_create(member, after)

        guild.create_voice_channel.assert_awaited_once()
        member.move_to.assert_awaited_once_with(new_channel)
        voice_owner_service.add.assert_awaited_once_with(member.guild.id, new_channel.id, member.id)


if __name__ == "__main__":
    unittest.main()
