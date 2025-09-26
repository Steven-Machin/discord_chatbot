from __future__ import annotations

from typing import Optional

import discord
from discord.ext import commands

from core.database import DatabaseManager


class Points(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @property
    def database(self) -> DatabaseManager:
        return self.bot.database  # type: ignore[attr-defined]

    async def cog_load(self) -> None:
        await self.database.setup()

    @commands.command()
    async def points(self, ctx: commands.Context) -> None:
        """Display the caller's point balance."""
        balance = await self.database.get_balance(ctx.author.id)
        embed = discord.Embed(
            title="Your Points",
            description=f"{ctx.author.mention}, you have **{balance}** points.",
            color=discord.Color.blurple(),
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_guild=True)
    async def addpoints(
        self,
        ctx: commands.Context,
        member: discord.Member,
        amount: int,
    ) -> None:
        """Add points to a member. Requires manage_guild permissions."""
        if amount <= 0:
            await ctx.send("Please provide an amount greater than zero.")
            return

        new_total = await self.database.add_balance(member.id, amount)
        embed = discord.Embed(
            title="Points Updated",
            description=(
                f"{member.mention} now sits at **{new_total}** points "
                f"(+{amount} added by {ctx.author.mention})."
            ),
            color=discord.Color.gold(),
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def leaderboard(self, ctx: commands.Context) -> None:
        """Show the top five users by point balance."""
        results = await self.database.leaderboard(limit=5)
        embed = discord.Embed(
            title="Points Leaderboard",
            color=discord.Color.purple(),
        )

        if not results:
            embed.description = "No one has earned any points yet. Be the first!"
            await ctx.send(embed=embed)
            return

        lines = []
        for index, (user_id, balance) in enumerate(results, start=1):
            display_name = await self._resolve_display_name(ctx, user_id)
            lines.append(f"**{index}.** {display_name} - **{balance}** points")

        embed.description = "\n".join(lines)
        await ctx.send(embed=embed)

    async def _resolve_display_name(self, ctx: commands.Context, user_id: int) -> str:
        member: Optional[discord.abc.User] = None
        if isinstance(ctx.channel, discord.abc.GuildChannel):
            member = ctx.guild.get_member(user_id) if ctx.guild else None
        if member is None:
            member = ctx.bot.get_user(user_id)
        if member is None:
            try:
                member = await ctx.bot.fetch_user(user_id)
            except discord.DiscordException:
                return f"User {user_id}"
        return member.mention if isinstance(member, discord.Member) else member.name


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Points(bot))
