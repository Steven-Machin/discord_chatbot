from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional, cast

import discord
from discord.ext import commands
import pytest

from core.bot_types import BotWithLogger
from cogs.points import DAILY_REWARD, Points

CommandCallback = Callable[..., Awaitable[Any]]


class FakeDatabase:
    def __init__(self) -> None:
        self.balances: Dict[int, int] = {}
        self.metadata: Dict[str, str] = {}

    async def get_balance(self, user_id: int) -> int:
        return self.balances.get(user_id, 0)

    async def add_balance(self, user_id: int, amount: int) -> int:
        new_total = self.balances.get(user_id, 0) + amount
        self.balances[user_id] = new_total
        return new_total

    async def leaderboard(self, limit: int = 5) -> List[tuple[int, int]]:
        entries = sorted(self.balances.items(), key=lambda item: (-item[1], item[0]))
        return entries[:limit]

    async def get_metadata_value(self, key: str) -> Optional[str]:
        return self.metadata.get(key)

    async def set_metadata_value(self, key: str, value: str) -> None:
        self.metadata[key] = value


class FakeBot:
    def __init__(self) -> None:
        self.database: FakeDatabase = FakeDatabase()
        self.logger: logging.Logger = logging.getLogger("PointsTest.bot")
        self.command_logger: logging.Logger = logging.getLogger("PointsTest.commands")
        self.error_logger: logging.Logger = logging.getLogger("PointsTest.errors")

    def get_user(self, user_id: int) -> Optional[discord.abc.User]:
        return None

    async def fetch_user(self, user_id: int) -> Optional[discord.abc.User]:
        return None


@dataclass
class DummyUser:
    id: int
    name: str

    @property
    def display_name(self) -> str:
        return self.name

    @property
    def mention(self) -> str:
        return f"@{self.name}"


class DummyGuild:
    def __init__(self, members: Dict[int, DummyUser]) -> None:
        self._members = members

    def get_member(self, user_id: int) -> Optional[DummyUser]:
        return self._members.get(user_id)


class DummyContext:
    def __init__(self, author: DummyUser, guild: Optional[DummyGuild] = None) -> None:
        self.author = author
        self.guild = guild
        self.sent: List[discord.Embed] = []

    async def send(self, *, embed: discord.Embed, **_: object) -> None:  # type: ignore[override]
        self.sent.append(embed)


@pytest.mark.asyncio
async def test_balance_command_sends_embed() -> None:
    bot = FakeBot()
    cog = Points(cast(BotWithLogger, bot))
    ctx = DummyContext(author=DummyUser(1, "Alice"))
    context = cast(commands.Context[Any], ctx)

    balance_callback = cast(
        CommandCallback, Points.balance.callback.__get__(cog, Points)
    )
    await balance_callback(context)

    assert ctx.sent, "balance command should send an embed"
    assert ctx.sent[0].title == "Balance"


@pytest.mark.asyncio
async def test_daily_adds_points_for_new_user() -> None:
    bot = FakeBot()
    cog = Points(cast(BotWithLogger, bot))
    user = DummyUser(2, "Bob")
    ctx = DummyContext(author=user)
    context = cast(commands.Context[Any], ctx)

    daily_callback = cast(CommandCallback, Points.daily.callback.__get__(cog, Points))
    await daily_callback(context)

    assert bot.database.balances[user.id] == DAILY_REWARD
    assert ctx.sent[-1].description == "You received 100 points!"


@pytest.mark.asyncio
async def test_leaderboard_runs_without_error() -> None:
    bot = FakeBot()
    # Pre-populate leaderboard data
    await bot.database.add_balance(3, 250)
    await bot.database.add_balance(4, 150)
    await bot.database.add_balance(5, 50)

    members = {3: DummyUser(3, "Carol"), 4: DummyUser(4, "Dave")}
    ctx = DummyContext(author=DummyUser(6, "Eve"), guild=DummyGuild(members))
    context = cast(commands.Context[Any], ctx)

    cog = Points(cast(BotWithLogger, bot))
    leaderboard_callback = cast(
        CommandCallback, Points.leaderboard.callback.__get__(cog, Points)
    )
    await leaderboard_callback(context)

    assert ctx.sent, "leaderboard should result in an embed being sent"
    assert ctx.sent[0].title == "Leaderboard"
