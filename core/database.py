import asyncio
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class GuildSettings:
    guild_id: int
    prefix: Optional[str]
    welcome_channel_id: Optional[int]
    mod_role_id: Optional[int]
    admin_role_id: Optional[int]


class DatabaseManager:
    """Lightweight async wrapper around sqlite3 for the bot."""

    def __init__(self, path: Path, default_prefix: str) -> None:
        self.path = Path(path)
        self.default_prefix = default_prefix
        self._setup_lock = asyncio.Lock()
        self._is_setup = False
        self._settings_cache: Dict[int, GuildSettings] = {}

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
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id INTEGER PRIMARY KEY,
                    prefix TEXT,
                    welcome_channel_id INTEGER,
                    mod_role_id INTEGER,
                    admin_role_id INTEGER
                )
                """
            )
            conn.commit()

    def _row_to_settings(
        self, guild_id: int, row: Optional[sqlite3.Row]
    ) -> GuildSettings:
        if row is None:
            return GuildSettings(
                guild_id=guild_id,
                prefix=None,
                welcome_channel_id=None,
                mod_role_id=None,
                admin_role_id=None,
            )
        return GuildSettings(
            guild_id=int(row["guild_id"]),
            prefix=row["prefix"],
            welcome_channel_id=(
                int(row["welcome_channel_id"])
                if row["welcome_channel_id"] is not None
                else None
            ),
            mod_role_id=(
                int(row["mod_role_id"]) if row["mod_role_id"] is not None else None
            ),
            admin_role_id=(
                int(row["admin_role_id"]) if row["admin_role_id"] is not None else None
            ),
        )

    async def get_guild_settings(
        self, guild_id: int, *, use_cache: bool = True
    ) -> GuildSettings:
        await self.setup()
        if use_cache:
            cached = self._settings_cache.get(guild_id)
            if cached is not None:
                return cached

        def query() -> GuildSettings:
            with sqlite3.connect(self.path) as conn:
                conn.row_factory = sqlite3.Row  # type: ignore[attr-defined]
                cursor = conn.execute(
                    """
                    SELECT guild_id, prefix, welcome_channel_id, mod_role_id, admin_role_id
                    FROM guild_settings
                    WHERE guild_id = ?
                    """,
                    (guild_id,),
                )
                row = cursor.fetchone()
                return self._row_to_settings(guild_id, row)

        settings = await asyncio.to_thread(query)
        self._settings_cache[guild_id] = settings
        return settings

    async def _upsert_guild_fields(
        self, guild_id: int, values: Dict[str, Optional[Any]]
    ) -> None:
        if not values:
            return
        await self.setup()

        def execute() -> None:
            with sqlite3.connect(self.path) as conn:
                columns = ", ".join(values.keys())
                placeholders = ", ".join("?" for _ in values)
                update_clause = ", ".join(
                    f"{column}=excluded.{column}" for column in values
                )
                conn.execute(
                    f"INSERT INTO guild_settings (guild_id, {columns}) VALUES (?, {placeholders}) "
                    f"ON CONFLICT(guild_id) DO UPDATE SET {update_clause}",
                    (guild_id, *values.values()),
                )
                conn.commit()

        await asyncio.to_thread(execute)
        self._settings_cache.pop(guild_id, None)

    async def set_guild_prefix(
        self, guild_id: int, prefix: Optional[str]
    ) -> GuildSettings:
        normalised = prefix.strip() if isinstance(prefix, str) else None
        await self._upsert_guild_fields(guild_id, {"prefix": normalised or None})
        return await self.get_guild_settings(guild_id, use_cache=False)

    async def reset_guild_prefix(self, guild_id: int) -> GuildSettings:
        await self._upsert_guild_fields(guild_id, {"prefix": None})
        return await self.get_guild_settings(guild_id, use_cache=False)

    async def get_prefix(self, guild_id: Optional[int]) -> str:
        if guild_id is None:
            return self.default_prefix
        settings = await self.get_guild_settings(guild_id)
        return settings.prefix or self.default_prefix

    async def set_welcome_channel(
        self, guild_id: int, channel_id: Optional[int]
    ) -> GuildSettings:
        await self._upsert_guild_fields(guild_id, {"welcome_channel_id": channel_id})
        return await self.get_guild_settings(guild_id, use_cache=False)

    async def set_moderator_role(
        self, guild_id: int, role_id: Optional[int]
    ) -> GuildSettings:
        await self._upsert_guild_fields(guild_id, {"mod_role_id": role_id})
        return await self.get_guild_settings(guild_id, use_cache=False)

    async def set_admin_role(
        self, guild_id: int, role_id: Optional[int]
    ) -> GuildSettings:
        await self._upsert_guild_fields(guild_id, {"admin_role_id": role_id})
        return await self.get_guild_settings(guild_id, use_cache=False)

    async def get_welcome_channel_id(self, guild_id: int) -> Optional[int]:
        settings = await self.get_guild_settings(guild_id)
        return settings.welcome_channel_id

    async def get_moderator_role_id(self, guild_id: int) -> Optional[int]:
        settings = await self.get_guild_settings(guild_id)
        return settings.mod_role_id

    async def get_admin_role_id(self, guild_id: int) -> Optional[int]:
        settings = await self.get_guild_settings(guild_id)
        return settings.admin_role_id

    async def clear_guild_settings(self, guild_id: int) -> None:
        await self.setup()

        def execute() -> None:
            with sqlite3.connect(self.path) as conn:
                conn.execute(
                    "DELETE FROM guild_settings WHERE guild_id = ?", (guild_id,)
                )
                conn.commit()

        await asyncio.to_thread(execute)
        self._settings_cache.pop(guild_id, None)

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
