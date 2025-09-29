from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, cast

import logging
import discord
from discord.ext import commands

from core.bot_types import BotWithLogger
from core.database import DatabaseManager

DAILY_REWARD = 100
METADATA_KEY_PREFIX = "daily_claim:"


class Points(commands.Cog):
    """Expose commands for checking balances and awarding daily points."""

    def __init__(self, bot: BotWithLogger) -> None:
        self.bot = bot

    @property
    def database(self) -> DatabaseManager:
        return cast(DatabaseManager, self.bot.database)  # type: ignore[attr-defined]

    @property
    def logger(self) -> logging.Logger:
        return self.bot.logger  # type: ignore[attr-defined]

    @commands.command(name="balance")
    async def balance(
        self, ctx: commands.Context, member: Optional[discord.Member] = None
    ) -> None:
        target = member or ctx.author
        try:
            balance = await self.database.get_balance(target.id)
        except Exception:
            self.logger.exception("Failed to fetch balance for %s", target.id)
            await self._send_error(ctx)
            return

        name = getattr(target, "display_name", getattr(target, "name", str(target.id)))
        embed = discord.Embed(title="Balance", color=discord.Color.blurple())
        embed.add_field(name=name, value=f"Balance: **{balance}**", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="daily")
    async def daily(self, ctx: commands.Context) -> None:
        now = datetime.now(timezone.utc)
        metadata_key = f"{METADATA_KEY_PREFIX}{ctx.author.id}"
        try:
            last_claim_raw = await self.database.get_metadata_value(metadata_key)
        except Exception:
            self.logger.exception(
                "Failed to fetch daily metadata for %s", ctx.author.id
            )
            await self._send_error(ctx)
            return

        last_claim = self._parse_timestamp(last_claim_raw)
        if last_claim and last_claim.date() == now.date():
            next_claim = last_claim + timedelta(days=1)
            embed = discord.Embed(
                title="Daily Reward",
                description=(
                    "You already claimed your reward today. "
                    f"Come back {discord.utils.format_dt(next_claim, style='R')}!"
                ),
                color=discord.Color.orange(),
            )
            await ctx.send(embed=embed)
            return

        try:
            new_total = await self.database.add_balance(ctx.author.id, DAILY_REWARD)
            await self.database.set_metadata_value(metadata_key, now.isoformat())
        except Exception:
            self.logger.exception("Failed to apply daily reward for %s", ctx.author.id)
            await self._send_error(ctx)
            return

        embed = discord.Embed(
            title="Daily Reward",
            description="You received 100 points!",
            color=discord.Color.green(),
        )
        embed.add_field(
            name=getattr(ctx.author, "display_name", ctx.author.name),
            value=f"New balance: **{new_total}**",
            inline=False,
        )
        await ctx.send(embed=embed)

    @commands.command(name="leaderboard")
    async def leaderboard(self, ctx: commands.Context) -> None:
        try:
            top_users = await self.database.leaderboard(limit=5)
        except Exception:
            self.logger.exception("Failed to fetch leaderboard")
            await self._send_error(ctx)
            return

        embed = discord.Embed(title="Leaderboard", color=discord.Color.gold())
        if not top_users:
            embed.description = "No one has any points yet."
            await ctx.send(embed=embed)
            return

        lines = []
        for index, (user_id, balance) in enumerate(top_users, start=1):
            display_name = await self._resolve_display_name(ctx, user_id)
            lines.append(f"{index}. {display_name} - {balance} points")
        embed.description = "\n".join(lines)
        await ctx.send(embed=embed)

    async def _resolve_display_name(self, ctx: commands.Context, user_id: int) -> str:
        user: Optional[discord.abc.User] = None
        if ctx.guild is not None:
            user = ctx.guild.get_member(user_id)
        if user is None:
            user = self.bot.get_user(user_id)
        if user is None and hasattr(self.bot, "fetch_user"):
            try:
                user = await self.bot.fetch_user(user_id)
            except (discord.NotFound, discord.HTTPException):
                user = None
        if user is None:
            return f"User {user_id}"
        return getattr(user, "display_name", getattr(user, "name", str(user_id)))

    async def _send_error(self, ctx: commands.Context) -> None:
        embed = discord.Embed(
            title="Error",
            description="Error: Could not fetch data",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)

    def _parse_timestamp(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Points(cast(BotWithLogger, bot)))
