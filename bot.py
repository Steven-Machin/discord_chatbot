import asyncio
import importlib
import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional

import discord
from discord.ext import commands

from core.config import load_config
from core.database import DatabaseManager

LOG_DIR = Path("logs")
BOT_LOG = LOG_DIR / "bot.log"
ERROR_LOG = LOG_DIR / "errors.log"
COGS_DIR = Path("cogs")
PREFIXES_FILE = Path("prefixes.json")


class PrefixManager:
    def __init__(self, path: Path, default_prefix: str) -> None:
        self.path = path
        self._default = default_prefix
        self._prefixes = self._load()

    @property
    def default(self) -> str:
        return self._default

    def _load(self) -> Dict[str, str]:
        if not self.path.exists():
            self.path.write_text("{}", encoding="utf-8")
            return {}
        try:
            data = self.path.read_text(encoding="utf-8")
            raw_prefixes = json.loads(data)
            if isinstance(raw_prefixes, dict):
                return {str(key): str(value) for key, value in raw_prefixes.items()}
        except json.JSONDecodeError:
            logging.getLogger("bot").warning("Prefix file corrupt, resetting to defaults.")
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
        if str(guild_id) in self._prefixes:
            self._prefixes.pop(str(guild_id))
            self.save()


def configure_logging() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    handlers = [
        logging.FileHandler(BOT_LOG, encoding="utf-8"),
        logging.StreamHandler(),
    ]
    for handler in handlers:
        handler.setFormatter(formatter)

    logging.basicConfig(level=logging.INFO, handlers=handlers, force=True)

    error_handler = logging.FileHandler(ERROR_LOG, encoding="utf-8")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logging.getLogger().addHandler(error_handler)

    return logging.getLogger("bot")


def _dynamic_prefix(bot: commands.Bot, message: discord.Message):
    base_prefix = bot.prefix_manager.get(message.guild.id if message.guild else None)
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
        except Exception as exc:  # noqa: BLE001 - we want to surface all load failures
            print(f"Failed to load cog {extension}: {exc}")
            logger.exception("Failed to load extension %s", extension)
        else:
            print(f"Loaded cog: {extension}")
            logger.info("Loaded extension %s", extension)


async def main() -> None:
    config = load_config()
    logger = configure_logging()

    intents = discord.Intents.default()
    intents.message_content = True

    database = DatabaseManager(config.db_path)

    bot = commands.Bot(command_prefix=_dynamic_prefix, intents=intents)
    bot.config = config  # type: ignore[attr-defined]
    bot.database = database  # type: ignore[attr-defined]
    bot.logger = logger  # type: ignore[attr-defined]
    bot.prefix_manager = PrefixManager(PREFIXES_FILE, config.prefix)  # type: ignore[attr-defined]

    @bot.event
    async def on_ready() -> None:
        print("Bot is online and all cogs are loaded!")

    async with bot:
        await bot.database.setup()  # type: ignore[attr-defined]
        await load_extensions(bot, logger)
        logger.info("Starting bot")
        await bot.start(config.token)


if __name__ == "__main__":
    asyncio.run(main())
