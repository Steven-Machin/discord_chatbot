from __future__ import annotations

import logging
import types

import pytest
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import guild_only

from cogs.moderation import Moderation


class DummyBot:
    logger: logging.Logger
    error_logger: logging.Logger
    command_logger: logging.Logger

    def __init__(self) -> None:
        logger = logging.getLogger("tests.moderation")
        self.logger = logger
        self.error_logger = logger
        self.command_logger = logger


@pytest.fixture()
def moderation_cog() -> Moderation:
    return Moderation(DummyBot())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_guild_only_command_rejects_dm_context() -> None:
    predicate = guild_only().predicate
    dm_ctx = types.SimpleNamespace(guild=None)

    with pytest.raises(commands.NoPrivateMessage):
        await predicate(dm_ctx)


def test_slash_commands_exist(moderation_cog: Moderation) -> None:
    commands_to_check = [
        (moderation_cog.kick_slash, "kick"),
        (moderation_cog.ban_slash, "ban"),
        (moderation_cog.unban_slash, "unban"),
    ]

    for command_obj, expected_name in commands_to_check:
        assert isinstance(command_obj, app_commands.Command)
        assert command_obj.name == expected_name
        assert command_obj.description
        assert command_obj.guild_only is True
        assert command_obj.binding is moderation_cog
