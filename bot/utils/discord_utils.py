from __future__ import annotations

import re

import discord


INVALID_CHANNEL_CHARS = re.compile(r"[\\/:*?\"<>|#@]|")


def is_admin(member: discord.abc.User) -> bool:
    if isinstance(member, discord.Member):
        return member.guild_permissions.administrator
    return False



def sanitize_channel_name(name: str) -> str:
    sanitized = re.sub(r"[\\/:*?\"<>|#@]", "", name).strip()
    sanitized = re.sub(r"\s+", "-", sanitized)
    return sanitized[:90] or "voice-channel"



def mention_user(user: discord.abc.User) -> str:
    return f"<@{user.id}>"
