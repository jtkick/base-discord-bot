#!/usr/bin/env python3

"""
BaseDiscordBot - A Discord bot for basing my more particular bots on.

This program provides a bot that plays music in a voice chat and fulfills other
commands in text channels.

Author: Jared Kick <jaredkick@gmail.com>
Version: 0.1.0

For detailed documentation, please refer to:
    <url>
Source Code:
    https://github.com/jtkick/base-discord-bot
"""

PROJECT_VERSION = "0.1.0"

# Standard imports
import logging
import os
import sys

# Third-part imports
import discord
from discord.ext import commands
from dotenv import load_dotenv
from openai import OpenAI

# Project imports
import database

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

    # Get bot logger
    logger = logging.getLogger("basediscordbot")

    # Load credentials
    load_dotenv()
    TOKEN = os.getenv('DISCORD_TOKEN')

    # Create custom bot with database connection
    class BaseDiscordBot(commands.Bot):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.db = database.Database("basediscordbot.db")
            self.ai = OpenAI()
    client = BaseDiscordBot(
        command_prefix = '!',
        intents=discord.Intents.all(),
        log_hander=False
    )

    # Load all bot cogs in directory
    # You need to import os for this method
    @client.event
    async def on_ready():
        logger.info("%s is now running", client.user)
        # Load cogs
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await client.load_extension(f'cogs.{filename[:-3]}')
                logger.info("Loaded %s cog", filename)

    client.run(TOKEN, log_handler=None)

if __name__ == "__main__":
    main()
