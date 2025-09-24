import random

import discord
from discord.ext import commands


EIGHTBALL_RESPONSES = [
    "It is certain.",
    "Without a doubt.",
    "You may rely on it.",
    "Yes, definitely.",
    "It is decidedly so.",
    "As I see it, yes.",
    "Most likely.",
    "Outlook good.",
    "Yes.",
    "Signs point to yes.",
    "Reply hazy, try again.",
    "Ask again later.",
    "Better not tell you now.",
    "Cannot predict now.",
    "Concentrate and ask again.",
    "Don't count on it.",
    "My reply is no.",
    "My sources say no.",
    "Outlook not so good.",
    "Very doubtful.",
]


class Fun(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command()
    async def roll(self, ctx: commands.Context, sides: int = 6) -> None:
        if sides < 2:
            await ctx.send("Please provide a number greater than 1 for the sides.")
            return

        result = random.randint(1, sides)
        embed = discord.Embed(
            title="Dice Roll",
            description=f"You rolled a `{result}` on a `{sides}`-sided die!",
            color=discord.Color.purple(),
        )
        await ctx.send(embed=embed)

    @commands.command(name="8ball")
    async def eight_ball(self, ctx: commands.Context, *, question: str) -> None:
        response = random.choice(EIGHTBALL_RESPONSES)
        embed = discord.Embed(title="Magic 8-Ball", color=discord.Color.dark_teal())
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=response, inline=False)
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Fun(bot))
