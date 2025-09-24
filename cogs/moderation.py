from typing import Optional

import discord
from discord.ext import commands


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

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

        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("You can't kick someone with an equal or higher role.")
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
            description=f"{member.mention} was kicked.\nReason: {reason or 'No reason provided.'}",
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

        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("You can't ban someone with an equal or higher role.")
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
            description=f"{member.mention} was banned.\nReason: {reason or 'No reason provided.'}",
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

        name, _, discriminator = tag.partition("#")
        if not name or not discriminator:
            await ctx.send("Please provide the user as `username#1234`.")
            return

        try:
            bans = await ctx.guild.bans()
        except discord.Forbidden:
            await ctx.send("I don't have permission to view bans.")
            return

        for entry in bans:
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
    await bot.add_cog(Moderation(bot))
