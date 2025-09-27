from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import discord
from discord.ext import commands, tasks


class System(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.background_save.start()

    @property
    def database(self):
        return self.bot.database  # type: ignore[attr-defined]

    @property
    def logger(self):
        return self.bot.logger  # type: ignore[attr-defined]

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        activity = discord.Game(name="Operation Full Stack")
        await self.bot.change_presence(activity=activity, status=discord.Status.online)
        guilds = ", ".join(guild.name for guild in self.bot.guilds) or "No guilds"
        self.logger.info("%s is connected and ready in: %s", self.bot.user, guilds)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if member.guild is None:
            return

        channel = await self._resolve_welcome_channel(member.guild)
        if channel is None:
            return

        embed = discord.Embed(
            title="Welcome!",
            description=(
                f"Hey {member.mention}, welcome to **{member.guild.name}**! "
                "We're glad to have you here."
            ),
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
        embed.add_field(
            name="Member Count",
            value=str(member.guild.member_count),
            inline=False,
        )

        try:
            await channel.send(embed=embed)
        except discord.HTTPException:
            self.logger.warning("Failed to send welcome message in %s", channel.mention)

    @commands.Cog.listener()
    async def on_message_edit(
        self,
        before: discord.Message,
        after: discord.Message,
    ) -> None:
        if before.author.bot or before.guild is None:
            return
        if before.content == after.content:
            return

        log_path: Path = self.bot.activity_log_path  # type: ignore[attr-defined]
        log_path.parent.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).isoformat()
        old_content = before.content.replace("\n", "\\n")
        new_content = after.content.replace("\n", "\\n")

        log_line = (
            f"{timestamp} | guild={before.guild.id} | channel={before.channel.id} | "
            f"user={before.author.id} | before={old_content} | after={new_content}\n"
        )
        try:
            with log_path.open("a", encoding="utf-8") as fp:
                fp.write(log_line)
        except OSError:
            self.logger.exception("Failed to write activity log")

    @tasks.loop(hours=6)
    async def background_save(self) -> None:
        now = datetime.now(timezone.utc)
        await self.database.record_last_save(now)
        self.logger.info("Recorded scheduled save at %s", now.isoformat())

    @background_save.before_loop
    async def before_background_save(self) -> None:
        await self.bot.wait_until_ready()
        await self.database.setup()

    @commands.command(name="setwelcome")
    @commands.has_permissions(manage_guild=True)
    async def setwelcome(
        self,
        ctx: commands.Context,
        channel: Optional[discord.TextChannel] = None,
    ) -> None:
        if ctx.guild is None:
            await ctx.send("This command can only be used in a server.")
            return

        target_channel = channel or (
            ctx.channel
            if isinstance(ctx.channel, discord.TextChannel)
            else ctx.guild.system_channel
        )

        if target_channel is None:
            await ctx.send("Please specify a text channel I can access.")
            return

        permissions = target_channel.permissions_for(ctx.guild.me)
        if not permissions.send_messages:
            await ctx.send("I need permission to send messages in that channel.")
            return

        await self.database.set_welcome_channel(ctx.guild.id, target_channel.id)
        embed = discord.Embed(
            title="Welcome Channel Updated",
            description=f"I'll welcome new members in {target_channel.mention}.",
            color=discord.Color.teal(),
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def lastsave(self, ctx: commands.Context) -> None:
        last_save = await self.database.get_last_save()
        embed = discord.Embed(title="Last Save", color=discord.Color.blue())
        if last_save is None:
            embed.description = "The scheduled save has not run yet."
        else:
            embed.description = (
                "The last background save ran at "
                f"**{discord.utils.format_dt(last_save, style='F')}** "
                f"({discord.utils.format_dt(last_save, style='R')})."
            )
        await ctx.send(embed=embed)

    async def _resolve_welcome_channel(
        self,
        guild: discord.Guild,
    ) -> Optional[discord.TextChannel]:
        channel_id = await self.database.get_welcome_channel_id(guild.id)
        channel: Optional[discord.TextChannel] = None
        if channel_id:
            potential = guild.get_channel(channel_id)
            if isinstance(potential, discord.TextChannel):
                channel = potential
            else:
                await self.database.set_welcome_channel(guild.id, None)

        if channel is None:
            channel = discord.utils.get(guild.text_channels, name="general")
        if channel is None:
            channel = guild.system_channel

        if channel and not channel.permissions_for(guild.me).send_messages:
            return None
        return channel

    def cog_unload(self) -> None:
        if self.background_save.is_running():
            self.background_save.cancel()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(System(bot))
