import math
from typing import cast

import discord
from discord.ext import commands

from core.bot_types import BotWithLogger


class Utility(commands.Cog):
    def __init__(self, bot: BotWithLogger) -> None:
        self.bot = bot

    def _latency_color(self, latency_ms: float) -> discord.Color:
        if latency_ms < 100:
            return discord.Color.green()
        if latency_ms < 300:
            return discord.Color.yellow()
        return discord.Color.red()

    @commands.command()
    async def ping(self, ctx: commands.Context) -> None:
        raw_latency = self.bot.latency * 1000
        latency_ms = (
            round(raw_latency, 2)
            if not math.isnan(raw_latency)
            else float("nan")
        )
        color = (
            self._latency_color(raw_latency)
            if not math.isnan(raw_latency)
            else discord.Color.red()
        )

        embed = discord.Embed(title="Pong!", color=color)
        embed.add_field(name="Latency", value=f"{latency_ms} ms")

        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Utility(cast(BotWithLogger, bot)))
