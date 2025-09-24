import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "bot.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("bot")

PREFIXES_FILE = Path("prefixes.json")
DEFAULT_PREFIX = "!"


class PrefixManager:
    def __init__(self, path: Path, default: str = DEFAULT_PREFIX) -> None:
        self.path = path
        self._default = default
        self._prefixes = self._load()

    @property
    def default(self) -> str:
        return self._default

    def _load(self) -> Dict[str, str]:
        if not self.path.exists():
            self.path.write_text("{}", encoding="utf-8")
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {str(key): str(value) for key, value in data.items()}
        except json.JSONDecodeError:
            logger.warning("Prefix file corrupt, resetting to defaults.")
        self.path.write_text("{}", encoding="utf-8")
        return {}

    def save(self) -> None:
        self.path.write_text(json.dumps(self._prefixes, indent=2), encoding="utf-8")

    def get(self, guild_id: Optional[int]) -> str:
        if guild_id is None:
            return self.default
        return self._prefixes.get(str(guild_id), self.default)

    def set(self, guild_id: int, prefix: str) -> None:
        self._prefixes[str(guild_id)] = prefix
        self.save()

    def reset(self, guild_id: int) -> None:
        removed = self._prefixes.pop(str(guild_id), None)
        if removed is not None:
            self.save()


prefix_manager = PrefixManager(PREFIXES_FILE, DEFAULT_PREFIX)


def get_command_prefix(bot: commands.Bot, message: discord.Message):
    return prefix_manager.get(message.guild.id if message.guild else None)


intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=get_command_prefix, intents=intents)
bot.prefix_manager = prefix_manager  # type: ignore[attr-defined]


@bot.event
async def on_ready() -> None:
    activity = discord.Game(name="Playing with Steven's code")
    await bot.change_presence(activity=activity, status=discord.Status.online)
    guilds = ", ".join(guild.name for guild in bot.guilds) or "No guilds"
    logger.info("%s is connected and ready in: %s", bot.user, guilds)


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
    if hasattr(ctx.command, "on_error"):
        return

    original_error = getattr(error, "original", error)

    if isinstance(original_error, commands.CommandNotFound):
        return

    if isinstance(original_error, commands.MissingRequiredArgument):
        description = f"Missing argument: `{original_error.param.name}`"
    elif isinstance(original_error, commands.MissingPermissions):
        perms = ", ".join(original_error.missing_permissions)
        description = f"You are missing permissions: `{perms}`"
    elif isinstance(original_error, commands.BotMissingPermissions):
        perms = ", ".join(original_error.missing_permissions)
        description = f"I need these permissions: `{perms}`"
    elif isinstance(original_error, commands.BadArgument):
        description = "Could not understand one of the arguments you provided."
    elif isinstance(original_error, commands.CheckFailure):
        description = "You don't have permission to run that command."
    else:
        description = "An unexpected error occurred while running that command."
        logger.exception(
            "Unexpected error in command %s by %s",
            ctx.command.qualified_name if ctx.command else "<unknown>",
            ctx.author,
        )

    embed = discord.Embed(
        title="Command Error",
        description=description,
        color=discord.Color.red(),
    )
    await ctx.send(embed=embed, delete_after=15)


@bot.listen("on_command_completion")
async def log_command_completion(ctx: commands.Context) -> None:
    guild_info = f"{ctx.guild.name} ({ctx.guild.id})" if ctx.guild else "Direct Message"
    logger.info(
        "Command %s executed by %s (%s) in %s",
        ctx.command.qualified_name if ctx.command else "<unknown>",
        ctx.author,
        ctx.author.id,
        guild_info,
    )


def iter_cogs():
    for path in Path("cogs").glob("*.py"):
        if path.name.startswith("_"):
            continue
        yield f"cogs.{path.stem}"


async def load_cogs() -> None:
    for extension in iter_cogs():
        await bot.load_extension(extension)
        logger.info("Loaded extension %s", extension)


async def main() -> None:
    if not TOKEN:
        raise ValueError("DISCORD_TOKEN environment variable is not set.")

    logger.info("Starting bot")
    try:
        async with bot:
            await load_cogs()
            await bot.start(TOKEN)
    finally:
        logger.info("Bot shutdown")


if __name__ == "__main__":
    asyncio.run(main())
