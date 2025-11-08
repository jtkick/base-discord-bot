#!/usr/bin/env python3

"""
BaseDiscordBot - A Discord bot for basing my more particular bots on.

This program provides a bot that plays music in a voice chat and fulfills other
commands in text channels.

Author: Jared Kick <jaredkick@gmail.com>
Version: 0.2.2

For detailed documentation, please refer to:
    <url>
Source Code:
    https://github.com/jtkick/base-discord-bot
"""


# BOT PERMISSIONS
# 1729383718059856

PROJECT_VERSION = "0.2.2"

# Standard imports
import logging
import os
import sys

# Third-part imports
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from openai import OpenAI

# Project imports
import database

class BaseDiscordBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = database.Database("basediscordbot.db")
        self.logger = logging.getLogger("basediscordbot")
        self.add_listener(self._load_cogs, 'on_ready')
    
    async def _load_cogs(self):
        self.logger.info("Loading cogs...")
        directory = os.path.dirname(os.path.abspath(__file__))
        for filename in os.listdir(f'{directory}/cogs'):
            if filename.endswith('.py'):
                await self.load_extension(f'cogs.{filename[:-3]}')
                self.logger.info("Loaded %s cog", filename)
        for server in self.guilds:
            await self.tree.sync(guild=discord.Object(id=server.id))

def main():
    # Create custom logging handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
    console_handler.setFormatter(console_formatter)

    # Make sure all loggers use this handler
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    
    # Load credentials
    load_dotenv()
    TOKEN = os.getenv('DISCORD_TOKEN')

    # Create bot
    client = BaseDiscordBot(
        command_prefix = '!',
        intents=discord.Intents.all(),
        log_hander=False
    )

    # Run bot
    client.run(TOKEN, log_handler=None)

if __name__ == "__main__":
    main()
