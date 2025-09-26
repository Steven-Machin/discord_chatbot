import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Optional

import discord
from discord.ext import commands

from core.config import load_config
from core.database import DatabaseManager

LOG_DIR = Path("logs")
BOT_LOG = LOG_DIR / "bot.log"
ERROR_LOG = LOG_DIR / "errors.log"
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


def iter_cogs() -> list[str]:
    return [
        f"cogs.{path.stem}"
        for path in Path("cogs").glob("*.py")
        if not path.name.startswith("_")
    ]


async def load_extensions(bot: commands.Bot, logger: logging.Logger) -> None:
    for extension in iter_cogs():
        await bot.load_extension(extension)
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

    async with bot:
        await bot.database.setup()  # type: ignore[attr-defined]
        await load_extensions(bot, logger)
        logger.info("Starting bot")
        await bot.start(config.token)


if __name__ == "__main__":
    asyncio.run(main())
