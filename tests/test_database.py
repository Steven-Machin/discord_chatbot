import pytest

from core.database import DatabaseManager


@pytest.mark.asyncio
async def test_prefix_roundtrip(tmp_path):
    db_path = tmp_path / "bot.db"
    manager = DatabaseManager(db_path, default_prefix="!")

    await manager.setup()

    assert await manager.get_prefix(123456789) == "!"

    await manager.set_guild_prefix(123456789, "?")
    assert await manager.get_prefix(123456789) == "?"

    await manager.set_guild_prefix(123456789, "  *  ")
    assert await manager.get_prefix(123456789) == "*"

    await manager.reset_guild_prefix(123456789)
    assert await manager.get_prefix(123456789) == "!"


@pytest.mark.asyncio
async def test_guild_settings_roundtrip(tmp_path):
    db_path = tmp_path / "bot.db"
    manager = DatabaseManager(db_path, default_prefix="!")

    await manager.setup()

    await manager.set_welcome_channel(42, 9001)
    assert await manager.get_welcome_channel_id(42) == 9001

    await manager.set_moderator_role(42, 111)
    await manager.set_admin_role(42, 222)

    assert await manager.get_moderator_role_id(42) == 111
    assert await manager.get_admin_role_id(42) == 222

    await manager.set_welcome_channel(42, None)
    assert await manager.get_welcome_channel_id(42) is None

    await manager.set_moderator_role(42, None)
    await manager.set_admin_role(42, None)
    assert await manager.get_moderator_role_id(42) is None
    assert await manager.get_admin_role_id(42) is None
