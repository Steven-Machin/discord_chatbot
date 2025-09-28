import asyncio
import importlib
import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, cast

import discord
from discord.ext import commands

from core.config import load_config
from core.database import DatabaseManager
from core.bot_types import BotWithLogger

LOGS_DIR = Path("logs")
COMMANDS_LOG = LOGS_DIR / "commands.log"
ERRORS_LOG = LOGS_DIR / "errors.log"
ACTIVITY_LOG = LOGS_DIR / "activity.log"
COGS_DIR = Path("cogs")


def configure_logging() -> tuple[logging.Logger, logging.Logger, logging.Logger]:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    COMMANDS_LOG.touch(exist_ok=True)
    ERRORS_LOG.touch(exist_ok=True)
    ACTIVITY_LOG.touch(exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    bot_logger = logging.getLogger("bot")
    bot_logger.setLevel(logging.INFO)
    if not bot_logger.handlers:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        bot_logger.addHandler(stream_handler)

    command_logger = logging.getLogger("CommandLogger")
    command_logger.setLevel(logging.INFO)
    if not command_logger.handlers:
        command_handler = RotatingFileHandler(
            COMMANDS_LOG,
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        command_handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
        command_logger.addHandler(command_handler)

    error_logger = logging.getLogger("ErrorLogger")
    error_logger.setLevel(logging.ERROR)
    if not error_logger.handlers:
        error_handler = RotatingFileHandler(
            ERRORS_LOG,
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        error_handler.setFormatter(formatter)
        error_logger.addHandler(error_handler)

    return bot_logger, command_logger, error_logger


async def _dynamic_prefix(bot: commands.Bot, message: discord.Message):
    guild_id: Optional[int] = message.guild.id if message.guild else None
    base_prefix = await bot.database.get_prefix(guild_id)  # type: ignore[attr-defined]
    return commands.when_mentioned_or(base_prefix)(bot, message)


def discover_cogs() -> list[str]:
    importlib.invalidate_caches()
    if not COGS_DIR.exists():
        return []

    extensions: list[str] = []
    for filename in os.listdir(COGS_DIR):
        if not filename.endswith(".py") or filename == "__init__.py":
            continue
        extensions.append(f"{COGS_DIR.name}.{Path(filename).stem}")

    return sorted(extensions)


async def load_extensions(bot: commands.Bot, logger: logging.Logger) -> None:
    for extension in discover_cogs():
        try:
            await bot.load_extension(extension)
        except Exception as exc:  # noqa: BLE001 - surface all load failures
            print(f"Failed to load cog {extension}: {exc}")
            logger.exception("Failed to load extension %s", extension)
        else:
            print(f"Loaded cog: {extension}")
            logger.info("Loaded extension %s", extension)


def _format_location(ctx: commands.Context) -> tuple[str, str]:
    if ctx.guild:
        guild = f"{ctx.guild.name} ({ctx.guild.id})"
        channel = (
            f"{ctx.channel.name} ({ctx.channel.id})"
            if isinstance(ctx.channel, discord.abc.GuildChannel)
            else str(ctx.channel)
        )
    else:
        guild = "Direct Message"
        channel = str(ctx.channel)
    return guild, channel


async def main() -> None:
    config = load_config()
    bot_logger, command_logger, error_logger = configure_logging()

    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    database = DatabaseManager(config.db_path, config.prefix)

    base_bot = commands.Bot(command_prefix=_dynamic_prefix, intents=intents)
    bot = cast(BotWithLogger, base_bot)
    bot.config = config  # type: ignore[attr-defined]
    bot.database = database  # type: ignore[attr-defined]
    bot.logger = bot_logger
    bot.command_logger = command_logger
    bot.error_logger = error_logger
    bot.activity_log_path = ACTIVITY_LOG  # type: ignore[attr-defined]
    bot.launch_time = datetime.now(timezone.utc)  # type: ignore[attr-defined]
    bot._slash_synced = False  # type: ignore[attr-defined]  # noqa: SLF001

    @bot.listen("on_command")
    async def log_command(ctx: commands.Context) -> None:
        if ctx.command is None:
            return
        guild, channel = _format_location(ctx)
        bot.command_logger.info(
            "user=%s (%s) | guild=%s | channel=%s | command=%s | content=%s",
            ctx.author,
            ctx.author.id,
            guild,
            channel,
            ctx.command.qualified_name,
            ctx.message.content,
        )

    @bot.event
    async def on_command_error(
        ctx: commands.Context, error: commands.CommandError
    ) -> None:
        if hasattr(ctx.command, "on_error"):
            return

        original = getattr(error, "original", error)
        if isinstance(original, commands.CommandNotFound):
            return

        if isinstance(original, commands.MissingRequiredArgument):
            description = f"Missing argument: `{original.param.name}`."
        elif isinstance(original, commands.BadArgument):
            description = "I couldn't understand one of the arguments you provided."
        elif isinstance(original, commands.MissingPermissions):
            permissions = ", ".join(original.missing_permissions)
            description = f"You are missing permissions: `{permissions}`."
        elif isinstance(original, commands.BotMissingPermissions):
            permissions = ", ".join(original.missing_permissions)
            description = f"I need these permissions: `{permissions}`."
        elif isinstance(original, commands.CheckFailure):
            description = "You don't have permission to run that command."
        else:
            description = (
                "Something went wrong while running that command. "
                "I've logged the error so the developers can take a look."
            )

        embed = discord.Embed(
            title="Uh oh!",
            description=description,
            color=discord.Color.red(),
        )
        embed.set_footer(text="This message will self-destruct in 20 seconds.")

        try:
            await ctx.send(embed=embed, delete_after=20)
        except discord.HTTPException:
            pass

        guild, channel = _format_location(ctx)
        bot.error_logger.error(
            "command=%s | user=%s (%s) | guild=%s | channel=%s | content=%s",
            ctx.command.qualified_name if ctx.command else "<unknown>",
            ctx.author,
            ctx.author.id,
            guild,
            channel,
            ctx.message.content,
            exc_info=original,
        )

    @bot.event
    async def on_ready() -> None:
        print("Bot is online and all cogs are loaded!")
        bot.logger.info("%s connected", bot.user)
        if not getattr(bot, "_slash_synced", False):  # type: ignore[attr-defined]
            try:
                synced = await bot.tree.sync()
            except Exception:
                bot.logger.exception("Failed to sync application commands")
            else:
                bot.logger.info("Synced %s application commands", len(synced))
            finally:
                bot._slash_synced = True  # type: ignore[attr-defined]

    async with base_bot:
        await bot.database.setup()  # type: ignore[attr-defined]
        await load_extensions(base_bot, bot_logger)
        bot_logger.info("Starting bot")
        await base_bot.start(config.token)


if __name__ == "__main__":
    asyncio.run(main())
