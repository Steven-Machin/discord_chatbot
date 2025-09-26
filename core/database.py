import asyncio
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple


class DatabaseManager:
    """Lightweight async wrapper around sqlite3 for the bot."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._setup_lock = asyncio.Lock()
        self._is_setup = False

    async def setup(self) -> None:
        async with self._setup_lock:
            if self._is_setup:
                return
            await asyncio.to_thread(self._initialise)
            self._is_setup = True

    def _initialise(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS points (
                    user_id INTEGER PRIMARY KEY,
                    balance INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            conn.commit()

    async def get_balance(self, user_id: int) -> int:
        await self.setup()

        def query() -> int:
            with sqlite3.connect(self.path) as conn:
                conn.row_factory = sqlite3.Row  # type: ignore[attr-defined]
                cursor = conn.execute(
                    "SELECT balance FROM points WHERE user_id = ?",
                    (user_id,),
                )
                row = cursor.fetchone()
                return int(row["balance"]) if row else 0

        return await asyncio.to_thread(query)

    async def add_balance(self, user_id: int, amount: int) -> int:
        await self.setup()

        def execute() -> int:
            with sqlite3.connect(self.path) as conn:
                conn.execute("BEGIN")
                conn.row_factory = sqlite3.Row  # type: ignore[attr-defined]
                current_row = conn.execute(
                    "SELECT balance FROM points WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
                current_balance = int(current_row["balance"]) if current_row else 0
                new_balance = current_balance + amount
                conn.execute(
                    "INSERT INTO points (user_id, balance) VALUES (?, ?) "
                    "ON CONFLICT(user_id) DO UPDATE SET balance=excluded.balance",
                    (user_id, new_balance),
                )
                conn.commit()
                return new_balance

        return await asyncio.to_thread(execute)

    async def leaderboard(self, limit: int = 5) -> List[Tuple[int, int]]:
        await self.setup()

        def query() -> List[Tuple[int, int]]:
            with sqlite3.connect(self.path) as conn:
                conn.row_factory = sqlite3.Row  # type: ignore[attr-defined]
                cursor = conn.execute(
                    "SELECT user_id, balance FROM points ORDER BY balance DESC, user_id ASC LIMIT ?",
                    (limit,),
                )
                return [
                    (int(row["user_id"]), int(row["balance"]))
                    for row in cursor.fetchall()
                ]

        return await asyncio.to_thread(query)

    async def record_last_save(self, when: datetime) -> None:
        await self.setup()
        iso_value = when.isoformat(timespec="seconds")

        def execute() -> None:
            with sqlite3.connect(self.path) as conn:
                conn.execute(
                    "INSERT INTO metadata (key, value) VALUES ('last_save', ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (iso_value,),
                )
                conn.commit()

        await asyncio.to_thread(execute)

    async def get_last_save(self) -> Optional[datetime]:
        await self.setup()

        def query() -> Optional[str]:
            with sqlite3.connect(self.path) as conn:
                conn.row_factory = sqlite3.Row  # type: ignore[attr-defined]
                cursor = conn.execute(
                    "SELECT value FROM metadata WHERE key = 'last_save'",
                )
                row = cursor.fetchone()
                return str(row["value"]) if row else None

        value = await asyncio.to_thread(query)
        return datetime.fromisoformat(value) if value else None
