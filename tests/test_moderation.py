import types

import pytest
from discord.ext import commands
from discord.ext.commands import guild_only


@pytest.mark.asyncio
async def test_guild_only_command_rejects_dm_context() -> None:
    predicate = guild_only().predicate
    dm_ctx = types.SimpleNamespace(guild=None)

    with pytest.raises(commands.NoPrivateMessage):
        await predicate(dm_ctx)
