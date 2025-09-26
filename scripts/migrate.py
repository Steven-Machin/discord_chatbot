import asyncio

from core.config import load_config
from core.database import DatabaseManager


async def main() -> None:
    config = load_config()
    db = DatabaseManager(config.db_path)
    await db.setup()
    print(f"Database ready at {config.db_path}")


if __name__ == "__main__":
    asyncio.run(main())
