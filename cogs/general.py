from typing import cast

import discord
from discord import app_commands
from discord.ext import commands

from core.bot_types import BotWithLogger


class General(commands.Cog):
    def __init__(self, bot: BotWithLogger) -> None:
        self.bot = bot

    def _build_hello_embed(self, display_name: str) -> discord.Embed:
        embed = discord.Embed(
            title="Hello!",
            description="Hey there! I'm alive and ready to help.",
            color=discord.Color.blurple(),
        )
        embed.set_footer(text=f"Requested by {display_name}")
        return embed

    @commands.command()
    async def hello(self, ctx: commands.Context) -> None:
        embed = self._build_hello_embed(ctx.author.display_name)
        await ctx.send(embed=embed)

    @app_commands.command(
        name="hello", description="Get a friendly hello from the bot."
    )
    async def hello_slash(self, interaction: discord.Interaction) -> None:
        embed = self._build_hello_embed(interaction.user.display_name)
        await interaction.response.send_message(embed=embed)

    @commands.command()
    async def ping(self, ctx: commands.Context) -> None:
        latency_ms = round(self.bot.latency * 1000)
        embed = discord.Embed(
            title="Pong!",
            description=f"Latency: `{latency_ms}ms`",
            color=discord.Color.green(),
        )
        await ctx.send(embed=embed)

    @commands.command(name="setprefix", aliases=["prefix"])
    @commands.has_permissions(manage_guild=True)
    async def setprefix(self, ctx: commands.Context, new_prefix: str) -> None:
        if ctx.guild is None:
            await ctx.send("Prefixes can't be changed in DMs.")
            return

        trimmed = new_prefix.strip()
        if not trimmed:
            await ctx.send("Please provide a non-empty prefix.")
            return

        if len(trimmed) > 5:
            await ctx.send("Prefixes should be 5 characters or fewer.")
            return

        await self.bot.database.set_guild_prefix(ctx.guild.id, trimmed)  # type: ignore[attr-defined]
        embed = discord.Embed(
            title="Prefix Updated",
            description=f"New prefix for **{ctx.guild.name}** is `{trimmed}`",
            color=discord.Color.gold(),
        )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(General(cast(BotWithLogger, bot)))
