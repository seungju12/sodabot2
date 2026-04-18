import unittest
from types import SimpleNamespace

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


if __name__ == "__main__":
    unittest.main()
