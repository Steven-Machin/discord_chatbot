import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"{bot.user} is connected and ready!")


@bot.command()
async def hello(ctx):
    await ctx.send("Hey Steven! I'm alive 👋")


if __name__ == "__main__":
    if not token:
        raise ValueError("DISCORD_TOKEN environment variable is not set.")
    bot.run(token)
