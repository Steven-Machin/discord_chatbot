import asyncio
import sqlite3
from pathlib import Path

import discord
from discord.ext import commands


class Points(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.db_path = Path("points.db")
        self._init_lock = asyncio.Lock()
        self._initialized = False

    async def cog_load(self) -> None:
        await self._ensure_db()

    async def _ensure_db(self) -> None:
        async with self._init_lock:
            if self._initialized:
                return
            await asyncio.to_thread(self._create_tables)
            self._initialized = True

    def _create_tables(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS points (
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    points INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (guild_id, user_id)
                )
                """
            )
            conn.commit()

    async def _get_points(self, guild_id: int, user_id: int) -> int:
        def query() -> int:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT points FROM points WHERE guild_id = ? AND user_id = ?",
                    (guild_id, user_id),
                )
                row = cursor.fetchone()
                return int(row[0]) if row else 0

        return await asyncio.to_thread(query)

    async def _add_points(self, guild_id: int, user_id: int, amount: int) -> int:
        def execute() -> int:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT points FROM points WHERE guild_id = ? AND user_id = ?",
                    (guild_id, user_id),
                )
                row = cursor.fetchone()
                current = int(row[0]) if row else 0
                new_total = current + amount
                conn.execute(
                    "REPLACE INTO points (guild_id, user_id, points) VALUES (?, ?, ?)",
                    (guild_id, user_id, new_total),
                )
                conn.commit()
                return new_total

        return await asyncio.to_thread(execute)

    @commands.command()
    async def points(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            await ctx.send("Points are only tracked inside servers.")
            return

        await self._ensure_db()
        total = await self._get_points(ctx.guild.id, ctx.author.id)
        embed = discord.Embed(
            title="Points",
            description=f"{ctx.author.mention}, you have **{total}** points.",
            color=discord.Color.blue(),
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
        if ctx.guild is None:
            await ctx.send("Points are only tracked inside servers.")
            return

        if amount <= 0:
            await ctx.send("Please provide an amount greater than 0.")
            return

        await self._ensure_db()
        new_total = await self._add_points(ctx.guild.id, member.id, amount)
        embed = discord.Embed(
            title="Points Updated",
            description=f"{member.mention} now has **{new_total}** points.",
            color=discord.Color.dark_gold(),
        )
        embed.set_footer(text=f"Added by {ctx.author.display_name}")
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Points(bot))
