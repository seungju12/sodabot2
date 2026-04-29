import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from bot.services.scheduler_service import SchedulerService


class SchedulerServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_auto_schedule_disabled_skips_auto_warning_and_notice(self):
        guild = SimpleNamespace(id=100)
        bot = SimpleNamespace(
            guilds=[guild],
            config_service=SimpleNamespace(get=lambda guild_id, key, default=None: False if key == "auth_schedule_enabled" else default),
        )
        service = SchedulerService(bot)
        service._run_auto_warning = AsyncMock()
        service._send_notice = AsyncMock()

        await service.run_auto_warning_for_all_guilds()
        await service.send_notice_for_all_guilds()

        service._run_auto_warning.assert_not_awaited()
        service._send_notice.assert_not_awaited()

    async def test_tick_runs_both_tasks_when_schedule_enabled_and_time_matches(self):
        bot = SimpleNamespace(guilds=[], config_service=SimpleNamespace(get=lambda guild_id, key, default=None: default))
        service = SchedulerService(bot)
        service.run_auto_warning_for_all_guilds = AsyncMock()
        service.send_notice_for_all_guilds = AsyncMock()

        with patch("bot.services.scheduler_service.now_kst", return_value=SimpleNamespace(replace=lambda **kwargs: "NOW")), patch(
            "bot.services.scheduler_service.is_auto_warning_run_time", return_value=True
        ), patch("bot.services.scheduler_service.get_notice_target_date", return_value=True):
            await service.tick()

        service.run_auto_warning_for_all_guilds.assert_awaited_once_with()
        service.send_notice_for_all_guilds.assert_awaited_once_with()


if __name__ == "__main__":
    unittest.main()