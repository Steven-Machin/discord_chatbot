from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord
import pytest
from discord.ext import commands

from cogs.utility import Utility


class DummyBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(command_prefix="!", intents=discord.Intents.none())
        self.launch_time = datetime.now(timezone.utc)

    @property
    def latency(self) -> float:
        return 0.123


@pytest.mark.asyncio
async def test_ping_command_exists_and_sends_embed():
    bot = DummyBot()
    try:
        await bot.add_cog(Utility(bot))
        command = bot.get_command("ping")
        assert command is not None

        send_mock = AsyncMock()
        ctx = SimpleNamespace(bot=bot, send=send_mock)

        await command.callback(command.cog, ctx)

        send_mock.assert_awaited()
        embed = send_mock.await_args.kwargs["embed"]
        assert embed is not None
        assert embed.title == "Pong!"
    finally:
        await bot.close()


@pytest.mark.asyncio
async def test_uptime_command_exists_and_returns_string():
    bot = DummyBot()
    bot.launch_time = datetime.now(timezone.utc) - timedelta(
        hours=1, minutes=2, seconds=3
    )
    try:
        await bot.add_cog(Utility(bot))
        command = bot.get_command("uptime")
        assert command is not None

        send_mock = AsyncMock()
        ctx = SimpleNamespace(bot=bot, send=send_mock)

        await command.callback(command.cog, ctx)

        send_mock.assert_awaited()
        embed = send_mock.await_args.kwargs["embed"]
        assert embed is not None
        assert embed.title == "Uptime"
        field_value = embed.fields[0].value
        assert isinstance(field_value, str)
        assert field_value
    finally:
        await bot.close()
