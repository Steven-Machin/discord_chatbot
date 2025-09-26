from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class BotConfig:
    token: str
    prefix: str
    db_path: Path


def load_config() -> BotConfig:
    """Load configuration values from the .env file."""
    load_dotenv()

    token = os.getenv("TOKEN")
    if not token:
        raise RuntimeError("TOKEN is not set in the environment.")

    prefix = os.getenv("BOT_PREFIX", "!").strip() or "!"
    db_path_value = os.getenv("DB_PATH", "data/bot.db")
    db_path = Path(db_path_value).expanduser().resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    return BotConfig(token=token, prefix=prefix, db_path=db_path)
