from typing import Sequence, cast

import discord
from discord import app_commands
from discord.ext import commands

from core.bot_types import BotWithLogger

POLL_EMOJIS: tuple[str, ...] = ("1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣")


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

    def _build_poll_embed(
        self,
        question: str,
        options: Sequence[str],
        author_display_name: str,
    ) -> discord.Embed:
        description = "\n".join(
            f"{emoji} {option}" for emoji, option in zip(POLL_EMOJIS, options)
        )
        embed = discord.Embed(
            title=question,
            description=description,
            color=discord.Color.blurple(),
        )
        embed.set_footer(text=f"Poll created by {author_display_name}")
        return embed

    def _build_serverinfo_embed(self, guild: discord.Guild) -> discord.Embed:
        member_total = guild.member_count
        if member_total is None:
            member_total = guild.approximate_member_count

        embed = discord.Embed(
            title=f"Server Info — {guild.name}",
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name="Members",
            value=f"{member_total:,}" if member_total is not None else "Unavailable",
            inline=True,
        )
        embed.add_field(name="Roles", value=str(len(guild.roles)), inline=True)
        embed.add_field(
            name="Created",
            value=discord.utils.format_dt(guild.created_at, style="F"),
            inline=False,
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.set_footer(text=f"Server ID: {guild.id}")
        return embed

    @commands.command()
    async def hello(self, ctx: commands.Context) -> None:
        embed = self._build_hello_embed(ctx.author.display_name)
        await ctx.send(embed=embed)

    @commands.command(name="poll")
    async def poll(self, ctx: commands.Context, question: str, *options: str) -> None:
        question_text = question.strip()
        if not question_text:
            await ctx.send("Please provide a question for the poll.")
            return

        cleaned_options = [option.strip() for option in options if option.strip()]

        if len(cleaned_options) < 2:
            await ctx.send(
                "Please provide between 2 and 5 options for the poll. "
                'Example: `!poll "Your question" "Option 1" "Option 2"`'
            )
            return

        if len(cleaned_options) > len(POLL_EMOJIS):
            await ctx.send("Polls can only have up to 5 options.")
            return

        embed = self._build_poll_embed(
            question_text,
            cleaned_options,
            ctx.author.display_name,
        )
        message: discord.Message = await ctx.send(embed=embed)

        for emoji in POLL_EMOJIS[: len(cleaned_options)]:
            try:
                await message.add_reaction(emoji)
            except discord.HTTPException as exc:
                self.bot.logger.warning(
                    "Failed to add poll reaction %s for message %s: %s",
                    emoji,
                    message.id,
                    exc,
                )
                break

    @commands.command(name="serverinfo")
    async def serverinfo(self, ctx: commands.Context) -> None:
        guild = ctx.guild
        if guild is None:
            await ctx.send("This command can only be used in a server.")
            return

        embed = self._build_serverinfo_embed(guild)
        await ctx.send(embed=embed)

    @app_commands.command(
        name="hello", description="Get a friendly hello from the bot."
    )
    async def hello_slash(self, interaction: discord.Interaction) -> None:
        embed = self._build_hello_embed(interaction.user.display_name)
        await interaction.response.send_message(embed=embed)

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
