from __future__ import annotations

from datetime import datetime, timezone

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

    @tasks.loop(hours=6)
    async def background_save(self) -> None:
        now = datetime.now(timezone.utc)
        await self.database.record_last_save(now)
        self.logger.info("Recorded scheduled save at %s", now.isoformat())

    @background_save.before_loop
    async def before_background_save(self) -> None:
        await self.bot.wait_until_ready()
        await self.database.setup()

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

    def cog_unload(self) -> None:
        if self.background_save.is_running():
            self.background_save.cancel()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(System(bot))
