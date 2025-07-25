import datetime
import discord
from discord.ext import commands
import logging
import os
import pathlib
import sqlite3
import typing

class Activities(commands.Cog):
    """A cog to track and gather statistics on user activities."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("activities")

    async def __local_check(self, ctx):
        """A local check which applies to all commands in this cog."""
        if not ctx.guild:
            raise commands.NoPrivateMessage
        return True

    async def __error(self, ctx, error):
        """A local error handler for all errors arising from commands in this cog."""
        if isinstance(error, commands.NoPrivateMessage):
            try:
                return await ctx.send(
                    'This command can not be used in private messages.')
            except discord.HTTPException:
                pass

        print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

    @commands.Cog.listener()
    async def on_presence_update(
        self,
        before: discord.Member,
        after: discord.Member):
        # Log the activity or status change
        if after.activity:
            self.logger.info(
                f"User '{before.name}' changed activity to "\
                f"'{after.activity.name}'")
        else:
            self.logger.info(
                f"User '{before.name}' changed status to '{after.status}'")
        self.bot.db.insert_activity_change(before, after)

async def setup(bot):
    await bot.add_cog(Activities(bot))