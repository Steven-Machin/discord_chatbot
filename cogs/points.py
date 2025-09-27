from __future__ import annotations

import asyncio
import sqlite3
from typing import List, Optional, Tuple

import discord
from discord.ext import commands


class Points(commands.Cog):
    """Track and award user points across servers."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.db_path = bot.config.db_path  # type: ignore[attr-defined]
        self._init_lock = asyncio.Lock()
        self._is_initialised = False

    async def cog_load(self) -> None:
        await self._ensure_database()

    async def _ensure_database(self) -> None:
        async with self._init_lock:
            if self._is_initialised:
                return
            await asyncio.to_thread(self._initialise)
            self._is_initialised = True

    def _initialise(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS points (
                    user_id TEXT PRIMARY KEY,
                    balance INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.commit()

    async def get_balance(self, user_id: int) -> int:
        user_key = str(user_id)

        def query() -> int:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT balance FROM points WHERE user_id = ?",
                    (user_key,),
                )
                row = cursor.fetchone()
                return int(row[0]) if row else 0

        return await asyncio.to_thread(query)

    async def add_points(self, user_id: int, amount: int) -> int:
        user_key = str(user_id)

        def execute() -> int:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT balance FROM points WHERE user_id = ?",
                    (user_key,),
                )
                row = cursor.fetchone()
                current = int(row[0]) if row else 0
                new_total = current + amount
                conn.execute(
                    "INSERT INTO points (user_id, balance) VALUES (?, ?) "
                    "ON CONFLICT(user_id) DO UPDATE SET balance=excluded.balance",
                    (user_key, new_total),
                )
                conn.commit()
                return new_total

        return await asyncio.to_thread(execute)

    async def get_top_users(self, limit: int = 5) -> List[Tuple[str, int]]:
        def query() -> List[Tuple[str, int]]:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT user_id, balance FROM points ORDER BY balance DESC, user_id ASC LIMIT ?",
                    (limit,),
                )
                return [(str(row[0]), int(row[1])) for row in cursor.fetchall()]

        return await asyncio.to_thread(query)

    @commands.command()
    async def points(self, ctx: commands.Context) -> None:
        await self._ensure_database()
        balance = await self.get_balance(ctx.author.id)

        embed = discord.Embed(
            title="Your Points",
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name=ctx.author.display_name,
            value=f"Balance: **{balance}**",
            inline=False,
        )
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_guild=True)
    async def addpoints(
        self,
        ctx: commands.Context,
        member: discord.Member,
        amount: int,
    ) -> None:
        if amount <= 0:
            await ctx.send("Please provide a positive number of points to add.")
            return

        await self._ensure_database()
        new_total = await self.add_points(member.id, amount)

        embed = discord.Embed(title="Points Updated", color=discord.Color.gold())
        embed.add_field(
            name=member.display_name,
            value=f"New balance: **{new_total}** (added {amount})",
            inline=False,
        )
        embed.set_footer(text=f"Awarded by {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @commands.command()
    async def leaderboard(self, ctx: commands.Context) -> None:
        await self._ensure_database()
        top_users = await self.get_top_users(limit=5)

        embed = discord.Embed(title="Top 5 Users", color=discord.Color.purple())

        if not top_users:
            embed.description = "Nobody has any points yet. Start earning points!"
            await ctx.send(embed=embed)
            return

        for index, (user_id, balance) in enumerate(top_users, start=1):
            user_display = await self._resolve_display_name(ctx, user_id)
            embed.add_field(
                name=f"{index}. {user_display}",
                value=f"{balance} points",
                inline=False,
            )

        await ctx.send(embed=embed)

    async def _resolve_display_name(self, ctx: commands.Context, user_id: str) -> str:
        try:
            numeric_id = int(user_id)
        except ValueError:
            return user_id

        user: Optional[discord.abc.User] = (
            ctx.guild.get_member(numeric_id) if ctx.guild else None
        )
        if user is None:
            user = self.bot.get_user(numeric_id)
        if user is None:
            try:
                user = await self.bot.fetch_user(numeric_id)
            except discord.HTTPException:
                return f"User {user_id}"
        return user.display_name if isinstance(user, discord.Member) else user.name

    @addpoints.error
    async def addpoints_error(
        self, ctx: commands.Context, error: commands.CommandError
    ) -> None:
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You need the manage server permission to award points.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(
                "Couldn't understand that command. Use `!addpoints @user <amount>`."
            )
        else:
            raise error

    @points.error
    async def points_error(
        self, ctx: commands.Context, error: commands.CommandError
    ) -> None:
        if isinstance(error, commands.BadArgument):
            await ctx.send(
                "That didn't look right. Try the command again with valid arguments."
            )
        else:
            raise error

    @leaderboard.error
    async def leaderboard_error(
        self, ctx: commands.Context, error: commands.CommandError
    ) -> None:
        if isinstance(error, commands.BadArgument):
            await ctx.send("Please try that again with valid arguments.")
        else:
            raise error


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Points(bot))
