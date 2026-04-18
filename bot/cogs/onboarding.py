from __future__ import annotations

import discord
from discord.ext import commands


class GenderOptionButton(discord.ui.Button):
    def __init__(self, option_key: str, label: str) -> None:
        super().__init__(label=label, style=discord.ButtonStyle.primary, row=0)
        self.option_key = option_key

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        if not isinstance(view, OnboardingSelectionView):
            return
        view.selected_gender_key = self.option_key
        view.stage = "game"
        view.selected_game_key = None
        view.refresh_items()
        await interaction.response.edit_message(embed=view.build_embed(interaction.guild), view=view)


class GameOptionButton(discord.ui.Button):
    def __init__(self, option_key: str, label: str, row: int) -> None:
        super().__init__(label=label, style=discord.ButtonStyle.primary, row=row)
        self.option_key = option_key

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        if not isinstance(view, OnboardingSelectionView):
            return
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("서버에서만 사용할 수 있습니다.", ephemeral=True)
        view.selected_game_key = self.option_key
        if view.selected_gender_key is None or view.selected_game_key is None:
            return await interaction.response.send_message("성별과 게임을 모두 선택해주세요.", ephemeral=True)
        try:
            await view.service.assign_general_roles(interaction.user, view.selected_gender_key, view.selected_game_key)
        except ValueError as e:
            return await interaction.response.send_message(str(e), ephemeral=True)
        except discord.HTTPException:
            return await interaction.response.send_message("역할 지급 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.", ephemeral=True)

        await interaction.response.edit_message(
            embed=view.service.build_completion_embed("설정 완료", "성별 역할과 게임 역할이 지급되었습니다."),
            view=None,
        )


class ResetSelectionButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="처음으로", style=discord.ButtonStyle.secondary, row=3)

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        if not isinstance(view, OnboardingSelectionView):
            return
        view.stage = "gender"
        view.selected_gender_key = None
        view.selected_game_key = None
        view.refresh_items()
        await interaction.response.edit_message(embed=view.build_embed(interaction.guild), view=view)


class OnboardingSelectionView(discord.ui.View):
    def __init__(self, bot: commands.Bot, guild_id: int) -> None:
        super().__init__(timeout=600)
        self.bot = bot
        self.service = bot.onboarding_service
        self.guild_id = guild_id
        self.stage: str = "gender"
        self.selected_gender_key: str | None = None
        self.selected_game_key: str | None = None
        self.refresh_items()

    def refresh_items(self) -> None:
        self.clear_items()
        if self.stage == "gender":
            for option in self.service.build_gender_select_options():
                self.add_item(GenderOptionButton(option.value, option.label))
        elif self.stage == "game":
            game_options = self.service.build_game_select_options()
            for index, option in enumerate(game_options):
                row = 0 if index < 2 else 1
                self.add_item(GameOptionButton(option.value, option.label, row))
        self.add_item(ResetSelectionButton())

    def build_embed(self, guild: discord.Guild | None) -> discord.Embed:
        if guild is None:
            return self.service.build_completion_embed("오류", "서버 정보가 없어 진행할 수 없습니다.")
        return self.service.build_progress_embed(guild, self.selected_gender_key, self.selected_game_key)


class OnboardingEntryView(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.service = bot.onboarding_service

    @discord.ui.button(label="일반 입장", style=discord.ButtonStyle.primary, custom_id="onboarding:start_general")
    async def start_general(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("서버에서만 사용할 수 있습니다.", ephemeral=True)
        if not self.service.is_valid_onboarding_nickname(interaction.user.display_name):
            return await interaction.response.send_message(
                self.service.get_nickname_validation_message(interaction.guild.id),
                ephemeral=True,
            )
        view = OnboardingSelectionView(self.bot, interaction.guild.id)
        await interaction.response.send_message(
            embed=view.build_embed(interaction.guild),
            view=view,
            ephemeral=True,
        )

    @discord.ui.button(label="지인으로 입장", style=discord.ButtonStyle.secondary, custom_id="onboarding:start_acquaintance")
    async def start_acquaintance(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("서버에서만 사용할 수 있습니다.", ephemeral=True)
        if not self.service.is_valid_acquaintance_nickname(interaction.user.display_name):
            return await interaction.response.send_message(
                self.service.get_acquaintance_nickname_validation_message(interaction.guild.id),
                ephemeral=True,
            )
        try:
            await self.service.assign_acquaintance_role(interaction.user)
        except ValueError as e:
            return await interaction.response.send_message(str(e), ephemeral=True)
        except discord.HTTPException:
            return await interaction.response.send_message("지인 역할 지급 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.", ephemeral=True)
        await interaction.response.send_message(
            embed=self.service.build_completion_embed("설정 완료", "지인 역할이 지급되었습니다."),
            ephemeral=True,
        )


class OnboardingCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(OnboardingCog(bot))
    bot.create_onboarding_entry_view = lambda: OnboardingEntryView(bot)
    bot.onboarding_entry_view = bot.create_onboarding_entry_view()
    bot.add_view(bot.onboarding_entry_view)