import math
from datetime import datetime, timedelta, timezone
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

    def _format_uptime(self, delta: timedelta) -> str:
        total_seconds = max(int(delta.total_seconds()), 0)
        days, remainder = divmod(total_seconds, 86_400)
        hours, remainder = divmod(remainder, 3_600)
        minutes, seconds = divmod(remainder, 60)

        parts: list[str] = []
        if days:
            parts.append(f"{days}d")
        if days or hours:
            parts.append(f"{hours}h")
        if days or hours or minutes:
            parts.append(f"{minutes}m")
        parts.append(f"{seconds}s")
        return " ".join(parts)

    @commands.command()
    async def ping(self, ctx: commands.Context) -> None:
        raw_latency = self.bot.latency * 1000
        latency_ms = (
            round(raw_latency, 2) if not math.isnan(raw_latency) else float("nan")
        )
        color = (
            self._latency_color(raw_latency)
            if not math.isnan(raw_latency)
            else discord.Color.red()
        )

        embed = discord.Embed(title="Pong!", color=color)
        embed.add_field(name="Latency", value=f"{latency_ms} ms")

        await ctx.send(embed=embed)

    @commands.command()
    async def uptime(self, ctx: commands.Context) -> None:
        launch_time: datetime | None = getattr(self.bot, "launch_time", None)
        if launch_time is None:
            uptime_display = "Unknown"
        else:
            delta = datetime.now(timezone.utc) - launch_time
            uptime_display = self._format_uptime(delta)

        embed = discord.Embed(title="Uptime", color=discord.Color.blue())
        embed.add_field(name="Running For", value=uptime_display)

        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Utility(cast(BotWithLogger, bot)))
