import discord
from discord.ext import commands
from openai import OpenAI
import os

class Chatbot(commands.Cog):
    """Chat related commands."""

    __slots__ = ('bot', 'players')

    def __init__(self, bot, **kwargs):
        self.bot = bot
        self.openai_client = OpenAI()
        self.players = {}

    async def cleanup(self, guild):
        try:
            del self.players[guild.id]
        except KeyError:
            pass

    async def __local_check(self, ctx):
        """A local check which applies to all commands in this cog."""
        if not ctx.guild:
            raise commands.NoPrivateMessage
        return True

    async def __error(self, ctx, error):
        """A local error handler for all errors arising from commands in this cog."""
        if isinstance(error, commands.NoPrivateMessage):
            try:
                return await ctx.send('This command can not be used in Private Messages.')
            except discord.HTTPException:
                pass

        print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

    def get_player(self, ctx):
        """Retrieve the guild player, or generate one."""
        try:
            player = self.players[ctx.guild.id]
        except KeyError:
            player = MusicPlayer(ctx)
            self.players[ctx.guild.id] = player

        return player

    def prompt(self, user_prompt: str):

        setup_prompt = os.getenv('CHATBOT_PROMPT', '')
        if setup_prompt == '':
            return '😴'
        try:
            completion =\
                self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": setup_prompt},
                        {
                            "role": "user",
                            "content": user_prompt
                        }
                    ]
                )
            return completion.choices[0].message.content
        except Exception as e:
            print(e)
            return '😴'

    @commands.command(name='chat', aliases=[], description="Command for chatting with chatbot.")
    async def chat_(self, ctx, *text):
        await ctx.send(self.prompt(' '.join(text)))

async def setup(bot):
    await bot.add_cog(Chatbot(bot))
