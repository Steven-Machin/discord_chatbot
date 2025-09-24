import discord
from discord.ext import commands


class General(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command()
    async def hello(self, ctx: commands.Context) -> None:
        embed = discord.Embed(
            title="Hello!",
            description="Hey Steven! I'm alive and ready to help.",
            color=discord.Color.blurple(),
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @commands.command()
    async def ping(self, ctx: commands.Context) -> None:
        latency_ms = round(self.bot.latency * 1000)
        embed = discord.Embed(
            title="Pong!",
            description=f"Latency: `{latency_ms}ms`",
            color=discord.Color.green(),
        )
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_guild=True)
    async def prefix(self, ctx: commands.Context, new_prefix: str) -> None:
        if ctx.guild is None:
            await ctx.send("Prefixes can't be changed in DMs.")
            return

        if not new_prefix.strip():
            await ctx.send("Please provide a non-empty prefix.")
            return

        if len(new_prefix) > 5:
            await ctx.send("Prefixes should be 5 characters or fewer.")
            return

        ctx.bot.prefix_manager.set(ctx.guild.id, new_prefix)
        embed = discord.Embed(
            title="Prefix Updated",
            description=f"New prefix for **{ctx.guild.name}** is `{new_prefix}`",
            color=discord.Color.gold(),
        )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(General(bot))
