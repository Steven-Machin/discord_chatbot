from __future__ import annotations

from typing import Optional

import discord
from discord.ext import commands


class ErrorHandler(commands.Cog):
    """Supplemental logging hooks for command completion."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: commands.Context) -> None:
        if ctx.command is None:
            return
        guild = f"{ctx.guild.name} ({ctx.guild.id})" if ctx.guild else "Direct Message"
        channel = (
            f"{ctx.channel.name} ({ctx.channel.id})"
            if isinstance(ctx.channel, discord.abc.GuildChannel)
            else str(ctx.channel)
        )
        self.bot.logger.info(
            "Command completed | command=%s | user=%s (%s) | guild=%s | channel=%s",
            ctx.command.qualified_name,
            ctx.author,
            ctx.author.id,
            guild,
            channel,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ErrorHandler(bot))
