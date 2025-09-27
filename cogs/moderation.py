from typing import Any, Optional, cast

import discord
from discord.ext import commands

from core.bot_types import BotWithLogger


class Moderation(commands.Cog):
    def __init__(self, bot: BotWithLogger) -> None:
        self.bot = bot

    @property
    def database(self) -> Any:
        return self.bot.database  # type: ignore[attr-defined]

    async def _get_required_role(
        self,
        guild: discord.Guild,
        *,
        admin: bool,
    ) -> Optional[discord.Role]:
        if admin:
            role_id = await self.database.get_admin_role_id(guild.id)
        else:
            role_id = await self.database.get_moderator_role_id(guild.id)

        if role_id is None:
            return None

        role = guild.get_role(role_id)
        if role is None:
            if admin:
                await self.database.set_admin_role(guild.id, None)
            else:
                await self.database.set_moderator_role(guild.id, None)
        return role

    async def _enforce_role(
        self,
        ctx: commands.Context,
        *,
        admin: bool,
    ) -> bool:
        if ctx.guild is None or not isinstance(ctx.author, discord.Member):
            return False

        required_role = await self._get_required_role(ctx.guild, admin=admin)
        if required_role is None:
            return True
        if required_role in ctx.author.roles:
            return True

        role_type = "administrator" if admin else "moderator"
        await ctx.send(
            f"You need the {required_role.mention if required_role else role_type} role to use this command.",
        )
        return False

    @commands.command(name="setmodrole")
    @commands.has_permissions(manage_guild=True)
    async def setmodrole(
        self,
        ctx: commands.Context,
        role: Optional[discord.Role] = None,
    ) -> None:
        if ctx.guild is None:
            await ctx.send("This command can only be used in a server.")
            return

        if role is None:
            await self.database.set_moderator_role(ctx.guild.id, None)
            description = "Moderator role requirement cleared."
        else:
            await self.database.set_moderator_role(ctx.guild.id, role.id)
            description = f"Moderator role set to {role.mention}."

        embed = discord.Embed(
            title="Moderator Role Updated",
            description=description,
            color=discord.Color.blue(),
        )
        await ctx.send(embed=embed)

    @commands.command(name="setadminrole")
    @commands.has_permissions(manage_guild=True)
    async def setadminrole(
        self,
        ctx: commands.Context,
        role: Optional[discord.Role] = None,
    ) -> None:
        if ctx.guild is None:
            await ctx.send("This command can only be used in a server.")
            return

        if role is None:
            await self.database.set_admin_role(ctx.guild.id, None)
            description = "Administrator role requirement cleared."
        else:
            await self.database.set_admin_role(ctx.guild.id, role.id)
            description = f"Administrator role set to {role.mention}."

        embed = discord.Embed(
            title="Administrator Role Updated",
            description=description,
            color=discord.Color.dark_blue(),
        )
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        reason: Optional[str] = None,
    ) -> None:
        if ctx.guild is None:
            await ctx.send("This command can only be used in a server.")
            return

        if member == ctx.author:
            await ctx.send("You can't kick yourself.")
            return

        author = ctx.author
        if not isinstance(author, discord.Member):
            await ctx.send("This command can only be used in a server.")
            return

        if member.top_role >= author.top_role and author != ctx.guild.owner:
            await ctx.send("You can't kick someone with an equal or higher role.")
            return

        if not await self._enforce_role(ctx, admin=False):
            return

        try:
            await member.kick(reason=reason or f"Kicked by {ctx.author}")
        except discord.Forbidden:
            await ctx.send("I don't have permission to kick that member.")
            return
        except discord.HTTPException:
            await ctx.send("Failed to kick that member. Please try again later.")
            return

        embed = discord.Embed(
            title="Member Kicked",
            description=(
                f"{member.mention} was kicked.\n"
                f"Reason: {reason or 'No reason provided.'}"
            ),
            color=discord.Color.orange(),
        )
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        reason: Optional[str] = None,
    ) -> None:
        if ctx.guild is None:
            await ctx.send("This command can only be used in a server.")
            return

        if member == ctx.author:
            await ctx.send("You can't ban yourself.")
            return

        author = ctx.author
        if not isinstance(author, discord.Member):
            await ctx.send("This command can only be used in a server.")
            return

        if member.top_role >= author.top_role and author != ctx.guild.owner:
            await ctx.send("You can't ban someone with an equal or higher role.")
            return

        if not await self._enforce_role(ctx, admin=True):
            return

        try:
            await member.ban(reason=reason or f"Banned by {ctx.author}")
        except discord.Forbidden:
            await ctx.send("I don't have permission to ban that member.")
            return
        except discord.HTTPException:
            await ctx.send("Failed to ban that member. Please try again later.")
            return

        embed = discord.Embed(
            title="Member Banned",
            description=(
                f"{member.mention} was banned.\n"
                f"Reason: {reason or 'No reason provided.'}"
            ),
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, *, tag: str) -> None:
        if ctx.guild is None:
            await ctx.send("This command can only be used in a server.")
            return

        if not await self._enforce_role(ctx, admin=True):
            return

        name, _, discriminator = tag.partition("#")
        if not name or not discriminator:
            await ctx.send("Please provide the user as `username#1234`.")
            return

        try:
            bans_iter = ctx.guild.bans()
        except discord.Forbidden:
            await ctx.send("I don't have permission to view bans.")
            return

        async for entry in bans_iter:
            user = entry.user
            if user.name == name and user.discriminator == discriminator:
                try:
                    await ctx.guild.unban(user)
                except discord.HTTPException:
                    await ctx.send("Failed to unban that user. Please try again later.")
                    return

                embed = discord.Embed(
                    title="User Unbanned",
                    description=f"Unbanned {user.name}#{user.discriminator}.",
                    color=discord.Color.green(),
                )
                await ctx.send(embed=embed)
                return

        await ctx.send("Couldn't find a banned user with that name and discriminator.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(cast(BotWithLogger, bot)))
