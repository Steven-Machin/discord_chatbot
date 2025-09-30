from __future__ import annotations

from typing import Any, Optional, cast

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import guild_only

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

    async def _send_interaction_message(
        self,
        interaction: discord.Interaction,
        *,
        content: Optional[str] = None,
        embed: Optional[discord.Embed] = None,
        ephemeral: bool = False,
    ) -> None:
        payload: dict[str, Any] = {"ephemeral": ephemeral}
        if content is not None:
            payload["content"] = content
        if embed is not None:
            payload["embed"] = embed

        if interaction.response.is_done():
            await interaction.followup.send(**payload)
        else:
            await interaction.response.send_message(**payload)

    async def _enforce_role_interaction(
        self,
        interaction: discord.Interaction,
        *,
        admin: bool,
    ) -> bool:
        guild = interaction.guild
        user = interaction.user
        if guild is None or not isinstance(user, discord.Member):
            await self._send_interaction_message(
                interaction,
                content="This command can only be used in a server.",
                ephemeral=True,
            )
            return False

        required_role = await self._get_required_role(guild, admin=admin)
        if required_role is None:
            return True
        if required_role in user.roles:
            return True

        role_type = "administrator" if admin else "moderator"
        await self._send_interaction_message(
            interaction,
            content=(
                f"You need the {required_role.mention if required_role else role_type} role to use this command."
            ),
            ephemeral=True,
        )
        return False

    def _log_moderation_action(
        self,
        guild: discord.Guild,
        moderator: discord.abc.User,
        target: discord.abc.Snowflake,
        *,
        action: str,
        reason: str,
    ) -> None:
        moderator_name = getattr(
            moderator,
            "display_name",
            getattr(moderator, "name", str(moderator)),
        )
        target_name = getattr(
            target,
            "display_name",
            getattr(target, "name", str(target)),
        )
        log_entry = (
            f"action={action} | guild={guild.name} ({guild.id}) | "
            f"moderator={moderator_name} ({moderator.id}) | "
            f"target={target_name} ({target.id}) | reason={reason}"
        )
        self.bot.logger.info(log_entry)
        self.bot.command_logger.info(log_entry)

    async def _handle_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        if isinstance(error, app_commands.MissingPermissions):
            missing = ", ".join(error.missing_permissions)
            message = f"You are missing permissions: `{missing}`."
        elif isinstance(error, app_commands.BotMissingPermissions):
            missing = ", ".join(error.missing_permissions)
            message = f"I need these permissions: `{missing}`."
        elif isinstance(error, app_commands.CheckFailure):
            message = "You don't have permission to run that command."
        else:
            message = (
                "Something went wrong while running that command. "
                "Please try again later."
            )
            original = getattr(error, "original", error)
            self.bot.logger.exception(
                "Unhandled application command error",
                exc_info=original,
            )

        await self._send_interaction_message(
            interaction,
            content=message,
            ephemeral=True,
        )

    @commands.command(name="setmodrole")
    @guild_only()
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
    @guild_only()
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
    @guild_only()
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
    @guild_only()
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
    @guild_only()
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

    @app_commands.command(
        name="kick",
        description="Kick a member from the server.",
    )
    @app_commands.checks.guild_only()
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.checks.bot_has_permissions(kick_members=True)
    async def kick_slash(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: Optional[str] = None,
    ) -> None:
        guild = interaction.guild
        if guild is None:
            await self._send_interaction_message(
                interaction,
                content="This command can only be used in a server.",
                ephemeral=True,
            )
            return

        if not isinstance(interaction.user, discord.Member):
            await self._send_interaction_message(
                interaction,
                content="This command can only be used in a server.",
                ephemeral=True,
            )
            return

        if member == interaction.user:
            await self._send_interaction_message(
                interaction,
                content="You can't kick yourself.",
                ephemeral=True,
            )
            return

        if (
            member.top_role >= interaction.user.top_role
            and interaction.user != guild.owner
        ):
            await self._send_interaction_message(
                interaction,
                content="You can't kick someone with an equal or higher role.",
                ephemeral=True,
            )
            return

        if not await self._enforce_role_interaction(interaction, admin=False):
            return

        reason_text = reason.strip() if reason else "No reason provided."
        audit_reason = (
            f"Kicked by {interaction.user} ({interaction.user.id}) | "
            f"Reason: {reason_text}"
        )

        try:
            await member.kick(reason=audit_reason)
        except discord.Forbidden:
            await self._send_interaction_message(
                interaction,
                content="I don't have permission to kick that member.",
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await self._send_interaction_message(
                interaction,
                content="Failed to kick that member. Please try again later.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="Member Kicked",
            description=(f"{member.mention} was kicked.\nReason: {reason_text}"),
            color=discord.Color.orange(),
        )
        embed.set_footer(text=f"Action by {interaction.user.display_name}")
        await self._send_interaction_message(interaction, embed=embed)
        self._log_moderation_action(
            guild,
            interaction.user,
            member,
            action="kick",
            reason=reason_text,
        )

    @kick_slash.error
    async def kick_slash_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        await self._handle_app_command_error(interaction, error)

    @app_commands.command(
        name="ban",
        description="Ban a member from the server.",
    )
    @app_commands.checks.guild_only()
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.checks.bot_has_permissions(ban_members=True)
    async def ban_slash(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: Optional[str] = None,
    ) -> None:
        guild = interaction.guild
        if guild is None:
            await self._send_interaction_message(
                interaction,
                content="This command can only be used in a server.",
                ephemeral=True,
            )
            return

        if not isinstance(interaction.user, discord.Member):
            await self._send_interaction_message(
                interaction,
                content="This command can only be used in a server.",
                ephemeral=True,
            )
            return

        if member == interaction.user:
            await self._send_interaction_message(
                interaction,
                content="You can't ban yourself.",
                ephemeral=True,
            )
            return

        if (
            member.top_role >= interaction.user.top_role
            and interaction.user != guild.owner
        ):
            await self._send_interaction_message(
                interaction,
                content="You can't ban someone with an equal or higher role.",
                ephemeral=True,
            )
            return

        if not await self._enforce_role_interaction(interaction, admin=True):
            return

        reason_text = reason.strip() if reason else "No reason provided."
        audit_reason = (
            f"Banned by {interaction.user} ({interaction.user.id}) | "
            f"Reason: {reason_text}"
        )

        try:
            await member.ban(reason=audit_reason)
        except discord.Forbidden:
            await self._send_interaction_message(
                interaction,
                content="I don't have permission to ban that member.",
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await self._send_interaction_message(
                interaction,
                content="Failed to ban that member. Please try again later.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="Member Banned",
            description=(f"{member.mention} was banned.\nReason: {reason_text}"),
            color=discord.Color.red(),
        )
        embed.set_footer(text=f"Action by {interaction.user.display_name}")
        await self._send_interaction_message(interaction, embed=embed)
        self._log_moderation_action(
            guild,
            interaction.user,
            member,
            action="ban",
            reason=reason_text,
        )

    @ban_slash.error
    async def ban_slash_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        await self._handle_app_command_error(interaction, error)

    @app_commands.command(
        name="unban",
        description="Unban a user by ID.",
    )
    @app_commands.checks.guild_only()
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.checks.bot_has_permissions(ban_members=True)
    async def unban_slash(
        self,
        interaction: discord.Interaction,
        user_id: app_commands.Range[int, 1],
        reason: Optional[str] = None,
    ) -> None:
        guild = interaction.guild
        if guild is None:
            await self._send_interaction_message(
                interaction,
                content="This command can only be used in a server.",
                ephemeral=True,
            )
            return

        if not await self._enforce_role_interaction(interaction, admin=True):
            return

        reason_text = reason.strip() if reason else "No reason provided."

        try:
            ban_entry = await guild.fetch_ban(discord.Object(id=user_id))
        except discord.NotFound:
            await self._send_interaction_message(
                interaction,
                content="Couldn't find a banned user with that ID.",
                ephemeral=True,
            )
            return
        except discord.Forbidden:
            await self._send_interaction_message(
                interaction,
                content="I don't have permission to view bans.",
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await self._send_interaction_message(
                interaction,
                content="Failed to fetch the ban list. Please try again later.",
                ephemeral=True,
            )
            return

        target = ban_entry.user
        audit_reason = (
            f"Unbanned by {interaction.user} ({interaction.user.id}) | "
            f"Reason: {reason_text}"
        )

        try:
            await guild.unban(target, reason=audit_reason)
        except discord.HTTPException:
            await self._send_interaction_message(
                interaction,
                content="Failed to unban that user. Please try again later.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="User Unbanned",
            description=f"Unbanned {target.mention}.",
            color=discord.Color.green(),
        )
        embed.add_field(name="User ID", value=str(target.id), inline=False)
        embed.add_field(name="Reason", value=reason_text, inline=False)
        embed.set_footer(text=f"Action by {interaction.user.display_name}")

        await self._send_interaction_message(interaction, embed=embed)
        self._log_moderation_action(
            guild,
            interaction.user,
            target,
            action="unban",
            reason=reason_text,
        )

    @unban_slash.error
    async def unban_slash_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        await self._handle_app_command_error(interaction, error)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(cast(BotWithLogger, bot)))
