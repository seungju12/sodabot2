from __future__ import annotations

import re

import discord


class OnboardingService:
    BRAND_COLOR = 0x5CA9FF
    SUCCESS_COLOR = 0x43B581
    ERROR_COLOR = 0xED4245
    NICKNAME_FORMAT_TEXT = "년생 닉네임 (예시: 01 단풍소다)"
    ACQUAINTANCE_NICKNAME_FORMAT_TEXT = "닉네임_OO지인 (예시: 소다_단풍소다지인)"
    NICKNAME_PATTERN = re.compile(r"^\d{2} [^\s]{2,4}$")
    ACQUAINTANCE_NICKNAME_PATTERN = re.compile(r"^[^\s_]{2,4}_[^\s_]{2,4}지인$")
    GENDER_OPTIONS = {
        "male": ("남성", "onboarding_gender_male_role_id"),
        "female": ("여성", "onboarding_gender_female_role_id"),
    }
    GAME_OPTIONS = {
        "lol": ("롤", "onboarding_game_lol_role_id"),
        "overwatch": ("오버워치", "onboarding_game_overwatch_role_id"),
        "battlegrounds": ("배틀그라운드", "onboarding_game_battlegrounds_role_id"),
        "other": ("기타", "onboarding_game_other_role_id"),
    }

    def __init__(self, bot: discord.ext.commands.Bot) -> None:
        self.bot = bot
        self.config = bot.config_service

    def get_onboarding_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        channel_id = int(self.config.get(guild.id, "onboarding_channel_id", "0") or 0)
        if channel_id <= 0:
            return None
        channel = guild.get_channel(channel_id)
        return channel if isinstance(channel, discord.TextChannel) else None

    def is_valid_onboarding_nickname(self, nickname: str) -> bool:
        return bool(self.NICKNAME_PATTERN.fullmatch(nickname.strip()))

    def is_valid_acquaintance_nickname(self, nickname: str) -> bool:
        return bool(self.ACQUAINTANCE_NICKNAME_PATTERN.fullmatch(nickname.strip()))

    def get_nickname_validation_message(self, guild_id: int) -> str:
        return (
            "일반 입장은 일반 닉네임 양식을 맞춘 뒤 진행할 수 있습니다.\n"
            f"형식: `{self.NICKNAME_FORMAT_TEXT}`\n"
            "예시: `01 단풍소다`\n"
            "닉네임 부분은 2~4글자여야 합니다."
        )

    def get_acquaintance_nickname_validation_message(self, guild_id: int) -> str:
        return (
            "지인 입장은 지인 전용 닉네임 양식을 맞춘 뒤 진행할 수 있습니다.\n"
            f"형식: `{self.ACQUAINTANCE_NICKNAME_FORMAT_TEXT}`\n"
            "예시: `소다_단풍소다지인`\n"
            "앞/뒤 닉네임 부분은 각각 2~4글자여야 합니다."
        )

    def build_gender_select_options(self) -> list[discord.SelectOption]:
        return [
            discord.SelectOption(label=label, value=option_key)
            for option_key, (label, _) in self.GENDER_OPTIONS.items()
        ]

    def build_game_select_options(self) -> list[discord.SelectOption]:
        return [
            discord.SelectOption(label=label, value=option_key)
            for option_key, (label, _) in self.GAME_OPTIONS.items()
        ]

    def build_onboarding_entry_embed(self, guild: discord.Guild) -> discord.Embed:
        embed = discord.Embed(
            title="✨ 권한 받기",
            description=(
                "새로 들어온 분들은 아래 순서대로 진행해주세요."
            ),
            color=self.BRAND_COLOR,
        )
        embed.add_field(
            name="🪪 STEP 1 · 닉네임 변경",
            value=(
                f"일반 입장\n> `{self.NICKNAME_FORMAT_TEXT}`\n\n"
                f"지인 입장\n> `{self.ACQUAINTANCE_NICKNAME_FORMAT_TEXT}`"
            ),
            inline=False,
        )
        embed.add_field(
            name="🎮 STEP 2-1 · 일반 입장",
            value=(
                "아래 일반 입장 버튼을 누른 뒤\n"
                "성별과 자주 하는 게임 1개를 선택해주세요."
            ),
            inline=False,
        )
        embed.add_field(
            name="🤝 STEP 2-2 · 지인 입장",
            value=(
                "지인으로 들어온 경우 닉네임 변경 후\n"
                "지인으로 입장 버튼을 눌러주세요."
            ),
            inline=False,
        )
        embed.add_field(
            name="💡 안내",
            value="잘못 선택했으면 다시 진행하면 기존 역할이 새 선택으로 바뀝니다.",
            inline=False,
        )
        return embed

    def build_progress_embed(
        self,
        guild: discord.Guild,
        selected_gender_key: str | None,
        selected_game_key: str | None,
    ) -> discord.Embed:
        gender_text = self._resolve_option_status(guild, selected_gender_key, self.GENDER_OPTIONS) if selected_gender_key else ""
        game_text = self._resolve_option_status(guild, selected_game_key, self.GAME_OPTIONS) if selected_game_key else ""
        done_count = int(selected_gender_key is not None) + int(selected_game_key is not None)
        current_step = "STEP 1 · 성별 선택" if selected_gender_key is None else "STEP 2 · 자주하는 게임 선택"
        guide_text = "성별 버튼을 누르면 다음 단계로 넘어갑니다." if selected_gender_key is None else "게임 버튼을 누르면 즉시 역할이 지급됩니다."
        selected_lines: list[str] = []
        if gender_text:
            selected_lines.append(f"성별: {gender_text}")
        if game_text:
            selected_lines.append(f"게임: {game_text}")
        if not selected_lines:
            selected_lines.append("아직 선택한 항목이 없습니다.")
        embed = discord.Embed(
            title=f"🧭 초기 설정 진행 {done_count}/2",
            color=self.BRAND_COLOR,
        )
        embed.add_field(name="현재 단계", value=f"`{current_step}`", inline=False)
        embed.add_field(
            name="선택 현황",
            value="\n".join(selected_lines),
            inline=False,
        )
        embed.add_field(name="닉네임 양식", value=f"> `{self.NICKNAME_FORMAT_TEXT}`", inline=False)
        embed.set_footer(text=f"{guide_text} 처음으로 버튼으로 다시 시작할 수 있습니다.")
        return embed

    def build_completion_embed(self, title: str, description: str) -> discord.Embed:
        color = self.ERROR_COLOR if title == "오류" else self.SUCCESS_COLOR
        title_text = f"⚠️ {title}" if title == "오류" else f"✅ {title}"
        return discord.Embed(title=title_text, description=description, color=color)

    def get_missing_option_labels(self, guild: discord.Guild) -> list[str]:
        missing_labels: list[str] = []
        for label, key in self._iter_required_role_mappings():
            role_id = int(self.config.get(guild.id, key, "0") or 0)
            if role_id <= 0 or guild.get_role(role_id) is None:
                missing_labels.append(label)
        return missing_labels

    async def assign_general_roles(self, member: discord.Member, gender_key: str, game_key: str) -> None:
        gender_role = self._get_role_for_option(member.guild, gender_key, self.GENDER_OPTIONS)
        game_role = self._get_role_for_option(member.guild, game_key, self.GAME_OPTIONS)
        self._ensure_manageable_role(member.guild, gender_role, "성별 역할")
        self._ensure_manageable_role(member.guild, game_role, "게임 역할")

        removable_roles = self._get_managed_roles(member.guild)
        current_roles = [role for role in removable_roles if role in member.roles and role.id not in {gender_role.id, game_role.id}]
        if current_roles:
            await member.remove_roles(*current_roles, reason="온보딩 역할 재설정")

        await member.add_roles(gender_role, game_role, reason="온보딩 완료")

    async def assign_acquaintance_role(self, member: discord.Member) -> None:
        acquaintance_role_id = int(self.config.get(member.guild.id, "acquaintance_role_id", "0") or 0)
        acquaintance_role = member.guild.get_role(acquaintance_role_id)
        if acquaintance_role is None:
            raise ValueError("지인 역할이 설정되지 않았습니다. 관리자에게 문의해주세요.")
        self._ensure_manageable_role(member.guild, acquaintance_role, "지인 역할")

        removable_roles = self._get_managed_roles(member.guild)
        current_roles = [role for role in removable_roles if role in member.roles and role.id != acquaintance_role.id]
        if current_roles:
            await member.remove_roles(*current_roles, reason="온보딩 역할 재설정")

        if acquaintance_role not in member.roles:
            await member.add_roles(acquaintance_role, reason="지인 온보딩 완료")

    def _ensure_manageable_role(self, guild: discord.Guild, role: discord.Role, role_label: str) -> None:
        bot_member = getattr(guild, "me", None)
        if bot_member is None:
            return
        if not bot_member.guild_permissions.manage_roles:
            raise ValueError("봇에 역할 관리 권한이 없습니다. 관리자에게 문의해주세요.")
        top_role = getattr(bot_member, "top_role", None)
        role_position = getattr(role, "position", None)
        top_role_position = getattr(top_role, "position", None)
        if role_position is not None and top_role_position is not None and role_position >= top_role_position:
            raise ValueError(f"{role_label}이 봇 역할보다 높거나 같아서 지급할 수 없습니다. 역할 서열을 확인해주세요.")

    def _resolve_option_status(self, guild: discord.Guild, option_key: str, options: dict[str, tuple[str, str]]) -> str:
        label, _ = options[option_key]
        return label

    def _get_role_for_option(self, guild: discord.Guild, option_key: str, options: dict[str, tuple[str, str]]) -> discord.Role:
        if option_key not in options:
            raise ValueError("허용되지 않은 역할 선택입니다. 다시 진행해주세요.")
        _, config_key = options[option_key]
        role_id = int(self.config.get(guild.id, config_key, "0") or 0)
        role = guild.get_role(role_id)
        if role is None:
            raise ValueError("선택한 역할을 찾을 수 없습니다. 관리자에게 문의해주세요.")
        return role

    def _get_managed_roles(self, guild: discord.Guild) -> list[discord.Role]:
        role_ids: set[int] = set()
        for _, config_key in self.GENDER_OPTIONS.values():
            role_ids.add(int(self.config.get(guild.id, config_key, "0") or 0))
        for _, config_key in self.GAME_OPTIONS.values():
            role_ids.add(int(self.config.get(guild.id, config_key, "0") or 0))
        role_ids.add(int(self.config.get(guild.id, "acquaintance_role_id", "0") or 0))
        roles: list[discord.Role] = []
        for role_id in role_ids:
            if role_id <= 0:
                continue
            role = guild.get_role(role_id)
            if role is not None:
                roles.append(role)
        return roles

    def _iter_required_role_mappings(self) -> list[tuple[str, str]]:
        return [
            ("남성 역할", "onboarding_gender_male_role_id"),
            ("여성 역할", "onboarding_gender_female_role_id"),
            ("롤 역할", "onboarding_game_lol_role_id"),
            ("오버워치 역할", "onboarding_game_overwatch_role_id"),
            ("배틀그라운드 역할", "onboarding_game_battlegrounds_role_id"),
            ("기타 게임 역할", "onboarding_game_other_role_id"),
        ]