from __future__ import annotations

from typing import cast

from discord.ext import commands

from core.bot_types import BotWithLogger


class ErrorHandler(commands.Cog):
    """A cog for handling errors globally."""

    def __init__(self, bot: BotWithLogger) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(
        self,
        ctx: commands.Context,
        error: commands.CommandError,
    ) -> None:
        """Handle errors from commands globally."""
        if isinstance(error, commands.CommandNotFound):
            # ignore unknown commands
            return

        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You don’t have permission to use this command.")
            return

        if isinstance(error, commands.BotMissingPermissions):
            await ctx.send("I don’t have the required permissions to do that.")
            return

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing argument: `{error.param.name}`")
            return

        # fallback: log + notify
        await ctx.send("An unexpected error occurred. Please try again later.")
        if hasattr(self.bot, "logger"):
            self.bot.logger.exception("Unhandled command error", exc_info=error)


async def setup(bot: commands.Bot) -> None:
    """Load the cog."""
    await bot.add_cog(ErrorHandler(cast(BotWithLogger, bot)))
