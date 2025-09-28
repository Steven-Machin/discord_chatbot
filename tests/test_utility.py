from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord
import pytest
from discord.ext import commands

from cogs.utility import Utility


class DummyBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(command_prefix="!", intents=discord.Intents.none())

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
        embed = send_mock.await_args.kwargs.get("embed")
        assert embed is not None
        assert embed.title == "Pong!"
    finally:
        await bot.close()
