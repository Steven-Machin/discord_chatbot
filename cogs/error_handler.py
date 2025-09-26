from __future__ import annotations

import logging

import discord
from discord.ext import commands


class ErrorHandler(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @property
    def logger(self) -> logging.Logger:
        return self.bot.logger  # type: ignore[attr-defined]

    @commands.Cog.listener()
    async def on_command_error(
        self,
        ctx: commands.Context,
        error: commands.CommandError,
    ) -> None:
        if hasattr(ctx.command, "on_error"):
            return

        original = getattr(error, "original", error)
        if isinstance(original, commands.CommandNotFound):
            return

        if isinstance(original, commands.MissingRequiredArgument):
            description = f"Missing argument: `{original.param.name}`."
        elif isinstance(original, commands.BadArgument):
            description = "I couldn't understand one of the arguments you provided."
        elif isinstance(original, commands.MissingPermissions):
            permissions = ", ".join(original.missing_permissions)
            description = f"You are missing permissions: `{permissions}`."
        elif isinstance(original, commands.BotMissingPermissions):
            permissions = ", ".join(original.missing_permissions)
            description = f"I need these permissions: `{permissions}`."
        elif isinstance(original, commands.CheckFailure):
            description = "You don't have permission to run that command."
        else:
            description = (
                "Something went wrong while running that command. "
                "I've logged the error so the developers can take a look."
            )

        embed = discord.Embed(
            title="Uh oh!",
            description=description,
            color=discord.Color.red(),
        )
        embed.set_footer(text="This message will self-destruct in 20 seconds.")

        try:
            await ctx.send(embed=embed, delete_after=20)
        except discord.HTTPException:
            pass

        self.logger.error(
            "Error in command %s invoked by %s (%s)",
            ctx.command.qualified_name if ctx.command else "<unknown>",
            ctx.author,
            ctx.author.id,
            exc_info=original,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ErrorHandler(bot))
