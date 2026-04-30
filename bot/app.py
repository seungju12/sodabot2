import asyncio
import logging
import os
import time
from pathlib import Path

import aiohttp
import discord
from discord.ext import commands
from dotenv import load_dotenv

from bot.services.auth_service import AuthService
from bot.services.config_service import ConfigService
from bot.services.db import Database
from bot.services.onboarding_service import OnboardingService
from bot.services.scheduler_service import SchedulerService
from bot.services.voice_owner_service import VoiceOwnerService

BASE_DIR = Path(__file__).resolve().parent.parent
EXTENSIONS = [
    "bot.cogs.warning",
    "bot.cogs.config",
    "bot.cogs.onboarding",
    "bot.cogs.voice",
    "bot.cogs.events",
]


def build_bot() -> commands.Bot:
    intents = discord.Intents.default()
    intents.guilds = True
    intents.members = True
    intents.voice_states = True
    intents.message_content = False

    bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)
    database_target = os.getenv("DATABASE_URL")
    if not database_target:
        raise RuntimeError("DATABASE_URL is not set")
    bot.db = Database(database_target)
    bot.config_service = ConfigService(bot.db, BASE_DIR / "config" / "default_config.json")
    bot.auth_service = AuthService(bot)
    bot.onboarding_service = OnboardingService(bot)
    bot.scheduler_service = SchedulerService(bot)
    bot.voice_owner_service = VoiceOwnerService(bot.db)
    return bot


async def setup_bot(bot: commands.Bot) -> None:
    """봇 초기화 및 검증"""
    await bot.db.init()
    await bot.config_service.init()
    await bot.voice_owner_service.init()

    for ext in EXTENSIONS:
        await bot.load_extension(ext)


async def _sync_application_commands(bot: commands.Bot) -> None:
    logger = logging.getLogger(__name__)

    # Remove previously published global commands to avoid duplicate entries
    # when guild-scoped commands are also synced for faster iteration.
    bot.tree.clear_commands(guild=None)
    await bot.tree.sync()
    for ext in EXTENSIONS:
        await bot.reload_extension(ext)

    for guild in bot.guilds:
        bot.tree.clear_commands(guild=guild)
        bot.tree.copy_global_to(guild=guild)
        guild_commands = await bot.tree.sync(guild=guild)
        logger.info("길드 슬래시 명령 동기화 완료 guild=%s count=%s", guild.id, len(guild_commands))


def _validate_required_configs(config_service, guild: discord.Guild) -> None:
    """필수 설정값이 올바르게 설정되었는지 확인"""
    required_configs = {
        "warning_channel_id": "경고 로그 채널",
        "auth_channel_id": "인증 공지 채널",
        "auth_completed_role_id": "인증 완료 역할",
        "onboarding_channel_id": "권한받기 채널",
    }
    
    logger = logging.getLogger(__name__)
    for key, description in required_configs.items():
        value = int(config_service.get(guild.id, key, "0") or 0)
        if value == 0:
            logger.warning("⚠️  필수 설정 미완료: guild=%s key=%s (%s)", guild.id, key, description)
            logger.warning("   /설정 경고채널, /설정 인증채널, /설정 권한받기채널, /설정 인증완료역할 명령으로 설정해주세요.")


async def runner() -> None:
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN is not set")

    bot = build_bot()
    startup_ready_done = False

    @bot.event
    async def on_ready():
        nonlocal startup_ready_done
        if startup_ready_done:
            return
        for guild in bot.guilds:
            await bot.config_service.ensure_guild_defaults(guild.id)
            await bot.auth_service.sync_existing_auth_role_members(guild)
            _validate_required_configs(bot.config_service, guild)
        await _sync_application_commands(bot)
        await bot.scheduler_service.start()
        startup_ready_done = True
        logging.getLogger(__name__).info("Logged in as %s (%s)", bot.user, bot.user.id)

    async with bot:
        await setup_bot(bot)
        try:
            await bot.start(token)
        finally:
            bot.scheduler_service.stop()
            await bot.db.close()


def run() -> None:
    retry_delay_sec = 10
    while True:
        try:
            asyncio.run(runner())
            return
        except KeyboardInterrupt:
            logging.getLogger(__name__).info("종료 신호를 받아 봇을 종료합니다.")
            return
        except (aiohttp.ClientError, discord.GatewayNotFound) as e:
            logging.getLogger(__name__).warning(
                "네트워크/게이트웨이 연결 오류로 종료되었습니다: %s | %s초 후 재시도합니다.",
                e,
                retry_delay_sec,
            )
            time.sleep(retry_delay_sec)
