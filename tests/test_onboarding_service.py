import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from bot.cogs.onboarding import OnboardingSelectionView
from bot.services.onboarding_service import OnboardingService


class OnboardingServiceRoleAssignmentTests(unittest.IsolatedAsyncioTestCase):
    def test_nickname_validation_accepts_two_digit_birth_year_and_two_to_four_char_name(self):
        service = OnboardingService(SimpleNamespace(config_service=SimpleNamespace(get=lambda guild_id, key, default=None: default)))

        self.assertTrue(service.is_valid_onboarding_nickname("01 단풍소다"))
        self.assertTrue(service.is_valid_onboarding_nickname("99 소다"))

    def test_nickname_validation_rejects_invalid_format(self):
        service = OnboardingService(SimpleNamespace(config_service=SimpleNamespace(get=lambda guild_id, key, default=None: default)))

        self.assertFalse(service.is_valid_onboarding_nickname("2001 단풍소다"))
        self.assertFalse(service.is_valid_onboarding_nickname("01단풍소다"))
        self.assertFalse(service.is_valid_onboarding_nickname("01 단풍소다봇"))
        self.assertFalse(service.is_valid_onboarding_nickname("일 단풍"))

    def test_acquaintance_nickname_validation_accepts_expected_format(self):
        service = OnboardingService(SimpleNamespace(config_service=SimpleNamespace(get=lambda guild_id, key, default=None: default)))

        self.assertTrue(service.is_valid_acquaintance_nickname("소다_단풍소다지인"))
        self.assertTrue(service.is_valid_acquaintance_nickname("소다_망곰지인"))

    def test_acquaintance_nickname_validation_rejects_invalid_format(self):
        service = OnboardingService(SimpleNamespace(config_service=SimpleNamespace(get=lambda guild_id, key, default=None: default)))

        self.assertFalse(service.is_valid_acquaintance_nickname("김망곰 단풍소다지인"))
        self.assertFalse(service.is_valid_acquaintance_nickname("김망곰_단풍소다"))
        self.assertFalse(service.is_valid_acquaintance_nickname("김망곰_다섯글자닉네임지인"))
        self.assertFalse(service.is_valid_acquaintance_nickname("한글자_A지인"))

    async def test_assign_general_roles_replaces_previous_onboarding_roles(self):
        gender_old = SimpleNamespace(id=1)
        gender_new = SimpleNamespace(id=2)
        game_old = SimpleNamespace(id=3)
        game_new = SimpleNamespace(id=4)
        acquaintance_role = SimpleNamespace(id=6)

        guild = SimpleNamespace(
            id=100,
            get_role=lambda role_id: {
                1: gender_old,
                2: gender_new,
                3: game_old,
                4: game_new,
                6: acquaintance_role,
            }.get(role_id),
        )
        member = SimpleNamespace(
            guild=guild,
            roles=[gender_old, game_old, acquaintance_role],
            remove_roles=AsyncMock(),
            add_roles=AsyncMock(),
        )
        config_values = {
            "onboarding_gender_male_role_id": "2",
            "onboarding_gender_female_role_id": "1",
            "onboarding_game_lol_role_id": "4",
            "onboarding_game_overwatch_role_id": "3",
            "onboarding_game_battlegrounds_role_id": "0",
            "onboarding_game_other_role_id": "0",
            "acquaintance_role_id": "6",
        }
        service = OnboardingService(SimpleNamespace(config_service=SimpleNamespace(get=lambda guild_id, key, default=None: config_values.get(key, default))))

        await service.assign_general_roles(member, "male", "lol")

        member.remove_roles.assert_awaited_once_with(gender_old, game_old, acquaintance_role, reason="온보딩 역할 재설정")
        member.add_roles.assert_awaited_once_with(gender_new, game_new, reason="온보딩 완료")

    async def test_assign_acquaintance_role_removes_general_roles(self):
        gender_role = SimpleNamespace(id=11)
        game_role = SimpleNamespace(id=12)
        acquaintance_role = SimpleNamespace(id=14)

        guild = SimpleNamespace(
            id=200,
            get_role=lambda role_id: {
                11: gender_role,
                12: game_role,
                14: acquaintance_role,
            }.get(role_id),
        )
        member = SimpleNamespace(
            guild=guild,
            roles=[gender_role, game_role],
            remove_roles=AsyncMock(),
            add_roles=AsyncMock(),
        )
        config_values = {
            "onboarding_gender_male_role_id": "11",
            "onboarding_gender_female_role_id": "0",
            "onboarding_game_lol_role_id": "12",
            "onboarding_game_overwatch_role_id": "0",
            "onboarding_game_battlegrounds_role_id": "0",
            "onboarding_game_other_role_id": "0",
            "acquaintance_role_id": "14",
        }
        service = OnboardingService(SimpleNamespace(config_service=SimpleNamespace(get=lambda guild_id, key, default=None: config_values.get(key, default))))

        await service.assign_acquaintance_role(member)

        member.remove_roles.assert_awaited_once_with(gender_role, game_role, reason="온보딩 역할 재설정")
        member.add_roles.assert_awaited_once_with(acquaintance_role, reason="지인 온보딩 완료")

    async def test_assign_acquaintance_role_raises_when_role_is_above_bot(self):
        top_role = SimpleNamespace(position=10)
        acquaintance_role = SimpleNamespace(id=14, position=10)
        guild = SimpleNamespace(
            id=200,
            me=SimpleNamespace(guild_permissions=SimpleNamespace(manage_roles=True), top_role=top_role),
            get_role=lambda role_id: acquaintance_role if role_id == 14 else None,
        )
        member = SimpleNamespace(guild=guild, roles=[])
        config_values = {"acquaintance_role_id": "14"}
        service = OnboardingService(SimpleNamespace(config_service=SimpleNamespace(get=lambda guild_id, key, default=None: config_values.get(key, default))))

        with self.assertRaisesRegex(ValueError, "역할 서열"):
            await service.assign_acquaintance_role(member)


class OnboardingSelectionViewTests(unittest.TestCase):
    def test_initial_view_shows_gender_buttons_only(self):
        service = SimpleNamespace(
            build_gender_select_options=lambda: [
                SimpleNamespace(label="남성", value="male"),
                SimpleNamespace(label="여성", value="female"),
            ],
            build_game_select_options=lambda: [
                SimpleNamespace(label="롤", value="lol"),
                SimpleNamespace(label="오버워치", value="overwatch"),
            ],
            build_progress_embed=lambda guild, gender, game: None,
        )
        bot = SimpleNamespace(onboarding_service=service)

        view = OnboardingSelectionView(bot, 1)

        labels = [item.label for item in view.children if hasattr(item, "label")]
        self.assertEqual(view.stage, "gender")
        self.assertEqual(labels, ["남성", "여성", "처음으로"])

    def test_game_buttons_appear_after_gender_selection(self):
        service = SimpleNamespace(
            build_gender_select_options=lambda: [
                SimpleNamespace(label="남성", value="male"),
                SimpleNamespace(label="여성", value="female"),
            ],
            build_game_select_options=lambda: [
                SimpleNamespace(label="롤", value="lol"),
                SimpleNamespace(label="오버워치", value="overwatch"),
                SimpleNamespace(label="배틀그라운드", value="battlegrounds"),
                SimpleNamespace(label="기타", value="other"),
            ],
            build_progress_embed=lambda guild, gender, game: None,
        )
        bot = SimpleNamespace(onboarding_service=service)

        view = OnboardingSelectionView(bot, 1)
        view.selected_gender_key = "male"
        view.stage = "game"
        view.refresh_items()

        labels = [item.label for item in view.children if hasattr(item, "label")]
        self.assertEqual(labels, ["롤", "오버워치", "배틀그라운드", "기타", "처음으로"])


if __name__ == "__main__":
    unittest.main()