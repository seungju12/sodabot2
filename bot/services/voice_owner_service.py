from __future__ import annotations

from bot.utils.time_utils import format_kst, now_kst


class VoiceOwnerService:
    def __init__(self, db: any) -> None:
        """음성 채널 소유권 추적 서비스"""
        self.db = db

    async def init(self) -> None:
        return None

    async def add(self, guild_id: int, channel_id: int, owner_discord_id: int) -> None:
        await self.db.execute(
                        """
                        INSERT INTO voice_channels(channel_id, guild_id, owner_discord_id, created_at)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(channel_id) DO UPDATE SET
                            guild_id = excluded.guild_id,
                            owner_discord_id = excluded.owner_discord_id,
                            created_at = excluded.created_at
                        """,
            (str(channel_id), str(guild_id), str(owner_discord_id), format_kst(now_kst())),
        )

    async def get_owner(self, guild_id: int, channel_id: int) -> int | None:
        """채널 소유자 ID 반환 (int 또는 None)"""
        row = await self.db.fetchone(
            "SELECT owner_discord_id FROM voice_channels WHERE guild_id = ? AND channel_id = ?",
            (str(guild_id), str(channel_id)),
        )
        return int(row["owner_discord_id"]) if row else None

    async def get_owned_channel_id(self, guild_id: int, owner_discord_id: int) -> int | None:
        row = await self.db.fetchone(
            "SELECT channel_id FROM voice_channels WHERE guild_id = ? AND owner_discord_id = ? ORDER BY created_at DESC LIMIT 1",
            (str(guild_id), str(owner_discord_id)),
        )
        return int(row["channel_id"]) if row else None

    async def remove(self, guild_id: int, channel_id: int) -> None:
        await self.db.execute(
            "DELETE FROM voice_channels WHERE guild_id = ? AND channel_id = ?",
            (str(guild_id), str(channel_id)),
        )
