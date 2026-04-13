from __future__ import annotations

import discord

from bot.utils.time_utils import now_kst, format_kst


class EmbedService:
    @staticmethod
    def warning_log(action_label: str, actor_text: str, target_text: str, reason: str, total_warning_count: int, created_at: str, kicked: bool = False) -> discord.Embed:
        description = f"{action_label} 처리되었습니다."
        if kicked:
            description += "\n경고 3회 누적으로 자동 추방이 함께 처리되었습니다."
        embed = discord.Embed(description=description, timestamp=now_kst())
        embed.add_field(name="누적 경고", value=str(total_warning_count), inline=False)
        embed.add_field(name="처리자", value=actor_text, inline=True)
        embed.add_field(name="대상자", value=target_text, inline=True)
        embed.add_field(name="사유", value=reason, inline=False)
        embed.add_field(name="처리 시각", value=created_at, inline=False)
        embed.set_footer(text="소다봇 경고 로그")
        return embed

    @staticmethod
    def config_result(key: str, value: str) -> discord.Embed:
        embed = discord.Embed(description="설정이 변경되었습니다.")
        embed.add_field(name="키", value=key, inline=False)
        embed.add_field(name="값", value=value, inline=False)
        embed.add_field(name="처리 시각", value=format_kst(now_kst()), inline=False)
        return embed
