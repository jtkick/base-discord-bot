import ast
import atexit
import datetime
import discord
from discord.ext import commands
from discord import app_commands
import enum
import random
import asyncio
import itertools
import sys
import traceback
import requests
import os
import validators
import threading
import pickle
from async_timeout import timeout
from functools import partial
import yt_dlp
from yt_dlp import YoutubeDL
import logging

import database
import assets

logger = logging.getLogger("music_player")

# Get API key for last.fm
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")

# Suppress noise about console usage from errors
# yt_dlp.utils.bug_reports_message = lambda: ""


class VoiceConnectionError(commands.CommandError):
    """Custom Exception class for connection errors."""


class InvalidVoiceChannel(VoiceConnectionError):
    """Exception for cases of invalid Voice Channels."""


class YTDLSource(discord.PCMVolumeTransformer):

    # Whether or not to download the video before playing
    download = False

    _downloader = YoutubeDL({
        "format": "bestaudio[ext=m4a]/bestaudio",   # Use OPUS for FFmpeg
        "outtmpl": "downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s",
        "restrictfilenames": True,
        "noplaylist": True,
        "nocheckcertificate": True,
        "ignoreerrors": False,
        "logtostderr": False,
        "quiet": True,
        "no_warnings": True,
        "default_search": "auto",
        "source_address": "0.0.0.0",  # ipv6 addresses cause issues sometimes
        "retries": 5,
        "ignoreerrors": True,
        'throttled_rate': '1M',
        "fragment_retries": 10,  # Prevents seemingly random stream crashes
    })

    def __init__(self, source, **kwargs):
        super().__init__(source)

        # YouTube Metadata
        self.title = kwargs.get("title")
        self.url = kwargs.get("url")
        self.web_url = kwargs.get("web_url")
        self.thumbnail_url = kwargs.get("thumbnail_url")
        self.filename = kwargs.get("filename")

        # Song metadata
        self.search_term = kwargs.get("search_term")
        self.artist = kwargs.get("artist")
        self.song_title = kwargs.get("song_title")

        # Discord info
        self.requester = kwargs.get("requester")

    def __str__(self):
        if self.song_title and self.artist:
            return f"'{self.song_title}' by {self.artist}"
        else:
            return f"{self.title}"

    @classmethod
    async def create(cls, search: str = ""):
        # Get YouTube video source
        logger.info(f"Getting YouTube video: {search}")
        to_run = partial(cls._downloader.extract_info,
                         url=search, download=cls.download)
        data = await asyncio.get_event_loop().run_in_executor(None, to_run)

        # There's an error with yt-dlp that throws a 403: Forbidden error, so
        # only proceed if it returns anything
        if data and "entries" in data:
            # take first item from a playlist
            data = data["entries"][0]

        # Get either source filename or URL, depending on if we're downloading
        if cls.download:
            source = cls._downloader.prepare_filename(data)
        else:
            source = data["url"]
        logger.info(f"Using source: {data["webpage_url"]}")

        # Setup actual audio source
        ffmpeg_source = discord.FFmpegPCMAudio(
            source,
            before_options="-nostdin -reconnect 1 -reconnect_streamed 1 "\
                           "-reconnect_delay_max 5",
            options="-vn -f s16le -ar 48000 -ac 2")
        return cls(
            ffmpeg_source,
            title = data.get("title"),
            url = data.get("url"),
            web_url = data.get("webpage_url"),
            thumbnail_url = data.get("thumbnail"),
            filename = data.get("filename"),
            search_term = search
        )

    # @classmethod
    # async def from_url(cls, url: str = ""):
    #     # Get the actual source
    #     source = await cls.create(url)

    #     # Get video title
    #     to_run = partial(cls._downloader.extract_info,
    #                      url=udl, download=cls.download)
    #     data = await asyncio.get_event_loop().run_in_executor(None, to_run)

    #     source.song_title = source['title']

    @classmethod
    async def from_search(cls, search: str = ""):
        # Get song metadata
        logger.info(f"Searching LastFM for: '{search}'")
        url = f"http://ws.audioscrobbler.com/2.0/?method=track.search&"\
            f"track={search}&api_key={LASTFM_API_KEY}&format=json"
        response = requests.get(url)
        lastfm_data = response.json()

        # Handle errors
        if "error" in lastfm_data:
            raise RuntimeError(
                f"LastFM returned error code '{lastfm_data["error"]}': "
                f"{lastfm_data["message"]}")

        # Let's get the first result, if any
        if not lastfm_data and not lastfm_data['results'] and not lastfm_dataa['results']['trackmatches'] and not lastfm_data['results']['trackmatches']['track']:
            raise RuntimeError("LastFM returned no results")
        
        track = lastfm_data['results']['trackmatches']['track'][0]
        artist = track['artist']
        song_title = track['name']
        logger.info(f"LastFM returned: '{song_title}' by '{artist}'") 

        # Get the actual source
        source = await cls.create(f"{song_title} {artist} official audio")

        # Add the found metadata
        source.artist = artist
        source.song_title = song_title

        return source

    # @classmethod
    # async def create_source(cls, ctx, search: str, *, download=False):
    #     loop = ctx.bot.loop if ctx else asyncio.get_event_loop()

    #     # If we got a YouTube link, get the video title for the song search
    #     logger.debug("Search parameter:", search)
    #     if isinstance(search, dict):
    #         search_term = search["title"]
    #         artist_str = f"&artist={search["artist"]}"
    #     elif isinstance(search, str) and validators.url(search):
    #         with YoutubeDL() as ydl:
    #             info = ydl.extract_info(search, download=False)
    #             search_term = info.get("title", "")
    #         artist_str = ""
    #     else:
    #         search_term = search
    #         artist_str = ""

    #     # Get song metadata
    #     logger.info(f"Searching LastFM for: '{search_term}'")
    #     url = f"http://ws.audioscrobbler.com/2.0/?method=track.search&"\
    #         f"track={search_term}{artist_str}&api_key={LASTFM_API_KEY}&format=json"
    #     response = requests.get(url)
    #     lastfm_data = response.json()
    #     # Let's get the first result, if any
    #     if not lastfm_data['results']['trackmatches']['track']:
    #         raise RuntimeError("LastFM returned no results")
    #     track = lastfm_data['results']['trackmatches']['track'][0]
    #     logger.debug("LastFM match: ", track)
    #     artist = track['artist']
    #     song_title = track['name']
    #     search = f"{song_title} {artist}"
    #     logger.info(f"LastFM returned: '{song_title}' by '{artist}'")

    #     # Adjust search term if we didn't get a URL
    #     if isinstance(search, dict) and not validators.url(search):
    #         search = f"{song_title} {artist}"
    #         logger.debug(f"Search string is not a URL; converting to {search}")

    #     # Get YouTube video source
    #     logger.info(f"Getting YouTube video: {search}")
    #     to_run = partial(cls._downloader.extract_info,
    #                      url=search, download=download)
    #     data = await loop.run_in_executor(None, to_run)

    #     # There's an error with yt-dlp that throws a 403: Forbidden error, so
    #     # only proceed if it returns anything
    #     if data and "entries" in data:
    #         # take first item from a playlist
    #         data = data["entries"][0]

    #     # Get either source filename or URL, depending on if we're downloading
    #     if download:
    #         source = cls._downloader.prepare_filename(data)
    #     else:
    #         source = data["url"]
    #     logger.info(f"Using source: {data["webpage_url"]}")

    #     ffmpeg_source = cls(
    #         discord.FFmpegPCMAudio(
    #             source, before_options="-nostdin", options="-vn"),
    #         data=data,
    #         requester=ctx.author if ctx else None,
    #     )
    #     # TODO: ADD THESE TO THE CONSTRUCTOR
    #     ffmpeg_source.search_term = search_term
    #     # ffmpeg_source.song_title = data["title"]
    #     ffmpeg_source.artist = artist
    #     ffmpeg_source.song_title = song_title
    #     ffmpeg_source.filename = source

    #     return ffmpeg_source


class MusicPlayer:
    """
    A class used to play music in a voice channel.

    This class implements a queue and play loop that plays music in a single
    guild. Since each player is assigned to a single voice channel, it allows
    multiple guilds to use the bot simultaneously.

    Methods:
        player_loop() -> None:
            Provides the main loop that waits for requests and plays songs.
        update_now_playing_message(repost[bool], emoji[str]) -> None:
            Updates the channel message that states what song is currently
            being played in the voice channel.
    """

    __slots__ = (
        "bot",
        "_guild",
        "_channel",
        "_cog",
        "_np",
        "_state",
        "_queue",
        "_next",
        "_skipped",
        "current",
        "np",
        "volume",
        "dj_mode",
        "_view",
    )

    # Each player is assiciated with a guild, so create a lock for when we do
    # volatile things in the server like delete previous messages
    _guild_lock = asyncio.Lock()

    class State(enum.Enum):
        IDLE = 1
        PLAYING = 2
        PAUSED = 3

    def __init__(self, ctx: discord.ext.commands.Context):
        """
        Initializes the music player object associated with the given Discord
        context.

        Args:
            ctx (discord.ext.commands.Context):
                The context within the player will connect to play music and
                respond to requests.
        """
        # Ensure proper cleanup
        atexit.register(self.__del__)

        self.bot = ctx.bot
        self._guild = ctx.guild
        self._channel = ctx.channel
        self._cog = ctx.cog
        self._np = None  # 'Now Playing' message

        self._state = self.State.IDLE

        self._queue = asyncio.Queue()
        self._next = asyncio.Event()
        self._skipped = False   # Flag for skipping songs

        self.volume = 0.5
        self.current = None
        self.dj_mode = False

        ctx.bot.loop.create_task(self.player_loop())

    def __del__(self):
        """
        Cleanup music player, which includes deleting messages like the
        'Now Playing' message.
        """
        if self._np:
            asyncio.run(self._np.delete())

    async def _change_state(self, new_state: "MusicPlayer.State" = None):
        """When state changes, update the Discord 'Now Playing' message."""
        if not self._channel:
            return

        # 'None' state is used to refresh message without changing state
        if new_state is not None:
            self._state = new_state

        logger.info("Updating 'Now Playing' message")
        await self.bot.wait_until_ready()
        async with self._guild_lock:
            # Create new 'Now Playing' message
            if self._state is self.State.IDLE:
                embed = discord.Embed(
                    title=f"◻️  Idle", color=discord.Color.light_gray()
                )
            elif self._state is self.State.PLAYING:
                embed = discord.Embed(
                    title=str(self.current),
                    #title=f"'{self.current.song_title}' by {self.current.artist}",
                    url=self.current.web_url,
                    color=discord.Color.green()
                )
            elif self._state is self.State.PAUSED:
                embed = discord.Embed(
                    title=str(self.current),
                    #title=f"'{self.current.song_title}' by {self.current.artist}",
                    url=self.current.web_url,
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title="UNKNOWN STATE", color=discord.Color.red()
                )

            if self._state is self.State.IDLE:
                pass
            elif self._state is self.State.PLAYING:
                embed.set_author(
                    name="Now Playing",
                    icon_url=assets.icons.get_icon_url(
                        icon="media-play", color="green")
                )
            elif self._state is self.State.PAUSED:
                embed.set_author(
                    name="Paused",
                    icon_url=assets.icons.get_icon_url(
                        icon="media-pause", color="green")
                )
            else:
                embed = discord.Embed(
                    title="UNKNOWN STATE", color=discord.Color.red()
                )

            # Get and add the thumbnail
            if self._state in [self.State.PLAYING, self.State.PAUSED]:
                embed.set_thumbnail(url=self.current.thumbnail_url)
                # embed.add_field(
                #     name="",
                #     value=(
                #         f"[{self.current.song_title}]({self.current.web_url}) - "
                #         f"{self.current.artist}"
                #     ),
                #     inline=False,
                # )

            # Add all upcoming songs
            # Possibly dangerous, but only obvious solution
            queue = [s for s in self._queue._queue if s is not None]
            if len(queue) > 0:
                value_str = ""
                for i, song in enumerate(queue):
                    value_str += (
                        f"{i+1}. [{str(song)}]({song.web_url})\n"
                    )
                embed.add_field(name="Queue", value=value_str, inline=False)

            # Add 'DJ Mode' footer if on
            if self.dj_mode:
                print("dj icon url: ", assets.icons.get_icon_url(
                    icon="headphones", color="green"))
                embed.set_footer(text="DJ Mode", icon_url=assets.icons.get_icon_url(
                    icon="headphones", color="green"))

            # Build controls
            controls = discord.ui.View(timeout=None)
            # Construct 'back' button
            prev_button = discord.ui.Button(
                label="⏮",
                style=discord.ButtonStyle.secondary,
                custom_id="prev"
            )
            # prev_button.disabled = self._player.current
            prev_button.disabled = True
            # prev_button.callback =
            controls.add_item(prev_button)

            # Construct 'play/pause' button
            play_button = discord.ui.Button(
                label="⏵" if self._state is self.State.PAUSED else "⏸",
                style=discord.ButtonStyle.secondary,
                custom_id="playpause"
            )
            play_button.disabled = self._state is self.State.IDLE
            if self._state is self.State.PLAYING:
                play_button.callback = self.pause
            elif self._state is self.State.PAUSED:
                play_button.callback = self.resume
            controls.add_item(play_button)

            # Construct 'next' button
            next_button = discord.ui.Button(
                label="⏭",
                style=discord.ButtonStyle.secondary,
                custom_id="next"
            )
            next_button.disabled = self._state is self.State.IDLE
            next_button.callback = self.next
            controls.add_item(next_button)

            # If last post is the 'Now Playing' message, just update it
            last_message = [m async for m in self._channel.history(limit=1)]
            if last_message[0] and self._np and last_message[0].id == self._np.id:
                await self._np.edit(embed=embed, view=controls)
            else:
                if self._np:
                    self._np = await self._np.delete()
                self._np = await self._channel.send(embed=embed, view=controls)

    async def resume(self, interaction: discord.Interaction = None):
        if interaction:
            await interaction.response.defer()
        vc = self._guild.voice_client
        if not vc or not vc.is_connected():
            return
        if vc.is_paused():
            vc.resume()
            await self._change_state(self.State.PLAYING)

    async def pause(self, interaction: discord.Interaction = None):
        if interaction:
            await interaction.response.defer()
        vc = self._guild.voice_client
        if not vc or not vc.is_connected():
            return
        if vc.is_playing():
            vc.pause()
            await self._change_state(self.State.PAUSED)

    async def previous(self, interaction: discord.Interaction = None):
        pass

    async def next(self, interaction: discord.Interaction = None):
        if interaction:
            await interaction.response.defer()
        vc = self._guild.voice_client
        if not vc.is_playing() and not vc.is_paused():
            return
        self._skipped = True    # Notify loop that we skipped the song
        vc.stop()

    async def queue(self, source: YTDLSource):
        await self._queue.put(source)
        await self._change_state(None)

    async def player_loop(self, interaction: discord.Interaction = None):
        """
        The main loop that waits for song requests and plays music accordingly.
        """
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self._next.clear()
            await self._change_state(self.State.IDLE)

            # Always get a song if there's one in the queue
            if self._queue.qsize() > 0 or self.dj_mode is False:
                logger.info("Getting song from play queue")
                try:
                    # Wait for the next song. If we timeout cancel the player
                    # and disconnect...
                    async with timeout(300):  # 5 minutes...
                        source = await self._queue.get()
                except asyncio.TimeoutError:
                    return await self.destroy()
            # Otherwise we're in DJ mode and a user hasn't requested one, so
            # pick a song at random and create a source for it
            else:
                logger.info(
                    "Queue is empty and DJ mode is on. Picking song at random"
                )
                try:
                    user_ids = [m.id for m in self._channel.members]
                    channel_ids = [c.id for c in self._channel.guild.channels]
                    source = await self.bot.db.get_next_song(
                        users=user_ids, channels=channel_ids)
                    if not source:
                        raise RuntimeError("Could not get YouTube source.")
                except Exception as e:
                    # # Something's wrong, turn off DJ mode to prevent infinite
                    # # loop
                    self.dj_mode = False
                    logger.error(e)
                    # await self._channel.send(str(e))

            # For the time being, we're going to use 'None' to signal to the
            # player that it should go back around and check for a song again,
            # mainly because DJ mode was switched on and it should pick a song
            # at random this time
            if source is None:
                continue

            source.volume = self.volume
            self.current = source

            logger.info(f"Playing '{source.song_title}' by '{source.artist}'")
            row_id = self.bot.db.insert_song_play(self._channel.id, source)

            def song_finished(error):
                # Update database to reflect song finishing
                if not error:
                    self.bot.db.update_song_play(row_id, not self._skipped)
                    self._skipped = False
                logger.info(f"Song finiehd with error: {error}")
                self.bot.loop.call_soon_threadsafe(self._next.set)
            try:
                self._guild.voice_client.play(
                    source,
                    after=song_finished
                )
                logger.info("Updating presense and 'now playing' message")
                await self.bot.change_presence(
                    activity=discord.Activity(
                        type=discord.ActivityType.custom,
                        name="custom",
                        state=f"🎵 {source.song_title} by {source.artist}",
                    )
                )
            except Exception as e:
                # Post error message
                embed = discord.Embed(
                    title=f"Error: {str(e)}", color=discord.Color.red()
                )
                await self._channel.send(embed=embed)
                raise e

            logger.info("Waiting for song to finish")
            await self._change_state(self.State.PLAYING)
            await self._next.wait()

            if source.filename and os.path.exists(source.filename):
                os.remove(source.filename)

            # Make sure the FFmpeg process is cleaned up.
            try:
                source.cleanup()
            except:
                pass
            self.current = None

            # Update bot statuses to match no song playing
            await self.bot.change_presence(status=None)

    async def destroy(self):
        """Disconnect and cleanup the player."""
        if self._np:
            self._np = await self._np.delete()
        try:
            return await self._cog.cleanup(self._guild)
        except:
            return None


class Music(commands.Cog):
    """Music related commands."""

    __slots__ = ("bot", "players")

    # Base embeds used as templates by the music player
    _searching = ""

    def __init__(self, bot):
        self.bot = bot
        self.players = {}

    # @commands.Cog.listener()
    # async def on_ready(self):
    #     await self.bot.tree.sync()
    #     logger.info("Synced command tree")

    async def cleanup(self, guild):
        try:
            await guild.voice_client.disconnect()
        except AttributeError:
            pass

        try:
            del self.players[guild.id]
        except KeyError:
            pass

    async def __local_check(self, ctx):
        """
        A local check which applies to all commands in this cog and prevents
        its use in private messages.
        """
        if not ctx.guild:
            raise commands.NoPrivateMessage
        return True

    async def __error(self, ctx, error):
        """
        A local error handler for all errors arising from commands in this cog.
        """
        if isinstance(error, commands.NoPrivateMessage):
            try:
                return await ctx.send(
                    "This command can not be used in Private Messages."
                )
            except discord.HTTPException:
                pass
        elif isinstance(error, InvalidVoiceChannel):
            await ctx.send(
                "Error connecting to Voice Channel. Please make sure you are"
                " in a valid channel or provide me with one"
            )

        print(
            "Ignoring exception in command {}:".format(ctx.command),
            file=sys.stderr,
        )
        traceback.print_exception(
            type(error), error, error.__traceback__, file=sys.stderr
        )

    def get_player(self, ctx):
        """Retrieve the guild player, or generate one."""
        try:
            player = self.players[ctx.guild.id]
        except KeyError:
            player = MusicPlayer(ctx)
            self.players[ctx.guild.id] = player

        return player

    @commands.command(
        name="join", aliases=["connect", "j"], description="connects to voice"
    )
    async def connect_(self, ctx, *, channel: discord.VoiceChannel = None):
        """Connect to voice.
        Parameters
        ------------
        channel: discord.VoiceChannel [Optional]
            The channel to connect to. If a channel is not specified, an attempt to join the voice channel you are in
            will be made.
        This command also handles moving the bot to different channels.
        """
        if not channel:
            try:
                channel = ctx.author.voice.channel
            except AttributeError:
                embed = discord.Embed(
                    title="",
                    description=(
                        "No channel to join. Please call `,join` from a voice"
                        " channel."
                    ),
                    color=discord.Color.green(),
                )
                await ctx.send(embed=embed)
                raise InvalidVoiceChannel(
                    "No channel to join. Please either specify a valid channel"
                    " or join one."
                )

        vc = ctx.voice_client

        if vc:
            if vc.channel.id == channel.id:
                return
            try:
                await vc.move_to(channel)
            except asyncio.TimeoutError:
                raise VoiceConnectionError(
                    f"Moving to channel: <{channel}> timed out."
                )
        else:
            try:
                await channel.connect()
            except asyncio.TimeoutError:
                raise VoiceConnectionError(
                    f"Connecting to channel: <{channel}> timed out."
                )
        # await ctx.message.add_reaction('👍')

    @commands.command(name="play", aliases=["p", "queue", "q"])
    async def play_(self, ctx, *, search: str = None):
        """Plays the given song in a voice channel.

        This method takes a string describing the song to play and plays it. In
        the event that a song is already being played, the new one is added to
        a queue of songs.

        Args:
            search (str): The search term or URL used to find the song.

        Example:
            !play Play That Funky Music by Wild Cherry
        """
        print(dir(assets))

        # Ensure we're connected to the proper voice channel
        vc = ctx.voice_client
        if not vc:
            await ctx.invoke(self.connect_)

        # Send message to say we're working on it
        embed = discord.Embed(
            title=f"{search}",
            color=discord.Color.green(),
        )
        embed.set_author(
            name="Searching for:",
            icon_url=assets.icons.get_icon_url(icon="search", color="green")
        )
        message = await ctx.channel.send(embed=embed)

        # Create source
        try:
            if not validators.url(search):
                source = await YTDLSource.from_search(search)
            else:
                source = await YTDLSource.create(search)
            source.requester = ctx.author
            # Track song requests in database
            self.bot.db.insert_song_request(message, source)
            # Add song to the corresponding player object
            player = self.get_player(ctx)
            await player.queue(source)
            # Update previous message to show found song and video
            embed = discord.Embed(
                title=f"",
                description=(
                    f"[{str(source)}]({source.web_url})"
                ),
                color=discord.Color.green(),
            )
            embed.set_author(
                name="Queued",
                icon_url=assets.icons.get_icon_url(
                    icon="line-3", color="green")
            )
            embed.set_thumbnail(url=source.thumbnail_url)
            await message.edit(embed=embed)
        except Exception as e:
            # Gracefully tell user there was an issue
            embed = discord.Embed(
                title=f"ERROR",
                description=f"{str(e)}",
                color=discord.Color.red(),
            )
            await message.edit(embed=embed)
            raise e

    @app_commands.command(name="hello", description="says hello")
    async def hello(self, interaction: discord.Interaction):
        await interaction.response.send_message("hello")

    @commands.command(
        name="djmode", aliases=["dj"], description="Turns DJ mode on or off."
    )
    async def djmode_(self, ctx, *, mode: str = "on"):
        """Turns DJ mode on or off. When on, the bot will play songs
        automatically."""
        # Ensure we're connected to the proper voice channel
        vc = ctx.voice_client
        if not vc:
            await ctx.invoke(self.connect_)
        # Get desired mode
        mode = mode.lower().strip()
        if mode in ("true", "t", "yes", "y", "on"):
            mode = True
        elif mode in ("false", "f", "no", "n", "off"):
            mode = False
        else:
            return
        # Switch to desired mode
        player = self.get_player(ctx)
        player.dj_mode = mode
        # Break player out of waiting on queue so it can pick a song at random
        if player.dj_mode:
            await player.queue(None)

    @commands.command(name="pause", description="pauses music")
    async def pause_(self, ctx):
        """Pause the currently playing song."""
        vc = ctx.voice_client

        if not vc or not vc.is_playing():
            embed = discord.Embed(
                title="",
                description="I am currently not playing anything",
                color=discord.Color.green(),
            )
            return await ctx.send(embed=embed)
        elif vc.is_paused():
            return

        vc.pause()

        # Update the 'Now Playing' message to reflect its paused
        player = self.get_player(ctx)
        await player.update_now_playing_message(emoji="⏸️")

    @commands.command(name="resume", description="resumes music")
    async def resume_(self, ctx):
        """Resume the currently paused song."""
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            embed = discord.Embed(
                title="",
                description="I'm not connected to a voice channel",
                color=discord.Color.green(),
            )
            return await ctx.send(embed=embed)
        elif not vc.is_paused():
            return

        vc.resume()

        # Update the 'Now Playing' message to reflect its resumed
        player = self.get_player(ctx)
        await player.update_now_playing_message()

    @commands.command(name="skip", description="skips to next song in queue")
    async def skip_(self, ctx):
        """Skip the song."""
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            embed = discord.Embed(
                title="",
                description="I'm not connected to a voice channel",
                color=discord.Color.green(),
            )
            return await ctx.send(embed=embed)

        if vc.is_paused():
            pass
        elif not vc.is_playing():
            return

        vc.stop()

    @commands.command(
        name="remove",
        aliases=["rm"],
        description="removes specified song from queue",
    )
    async def remove_(self, ctx, pos: int = None):
        """Removes specified song from queue"""

        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            embed = discord.Embed(
                title="",
                description="I'm not connected to a voice channel",
                color=discord.Color.green(),
            )
            return await ctx.send(embed=embed)

        player = self.get_player(ctx)
        if pos == None:
            player.queue._queue.pop()
        else:
            try:
                s = player.queue._queue[pos - 1]
                del player.queue._queue[pos - 1]
                embed = discord.Embed(
                    title="",
                    description=(
                        f"Removed [{s['title']}]({s['webpage_url']})"
                        f" [{s['requester'].mention}]"
                    ),
                    color=discord.Color.green(),
                )
                await ctx.send(embed=embed)
            except:
                embed = discord.Embed(
                    title="",
                    description=f'Could not find a track for "{pos}"',
                    color=discord.Color.green(),
                )
                await ctx.send(embed=embed)

    @commands.command(
        name="clear",
        aliases=["clr", "cl", "cr"],
        description="clears entire queue",
    )
    async def clear_(self, ctx):
        """
        Deletes entire queue of upcoming songs.

        Args:
            ctx (discord.ext.commands.Context): The Discord context associated
                with the message.
        """
        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            embed = discord.Embed(
                title="",
                description="I am not currently connected to a voice channel.",
                color=discord.Color.yellow(),
            )
            return await ctx.send(embed=embed)

        player = self.get_player(ctx)
        player.queue._queue.clear()
        await ctx.send("**Cleared**")

    @commands.command(
        name="volume",
        aliases=["vol", "v"],
        description="Sets the bot's volume in the voice channel.",
    )
    async def change_volume(self, ctx, *, vol: float = None):
        """
        Change the player volume.

        Args:
            ctx (discord.ext.commands.Context): The Discord context associated
                with the message.
            volume (float, int, required):
                The volume to set the player to in percentage. This must be
                between 1 and 100.
        """
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            embed = discord.Embed(
                title="",
                description="I am not currently connected to a voice channel.",
                color=discord.Color.yellow(),
            )
            return await ctx.send(embed=embed)

        if not vol:
            embed = discord.Embed(
                title="",
                description=f"🔊 **{(vc.source.volume)*100}%**",
                color=discord.Color.green(),
            )
            return await ctx.send(embed=embed)

        if not 0 < vol < 101:
            embed = discord.Embed(
                title="",
                description="Please enter a value between 1 and 100",
                color=discord.Color.green(),
            )
            return await ctx.send(embed=embed)

        player = self.get_player(ctx)

        if vc.source:
            vc.source.volume = vol / 100

        player.volume = vol / 100
        embed = discord.Embed(
            title="",
            description=f"**`{ctx.author}`** set the volume to **{vol}%**",
            color=discord.Color.green(),
        )
        await ctx.send(embed=embed)

    @commands.command(
        name="leave",
        aliases=["stop", "dc", "disconnect", "bye"],
        description="Stops music and disconnects from voice.",
    )
    async def leave_(self, ctx: discord.ext.commands.Context):
        """
        Stop the currently playing song and destroy the player.

        Args:
            ctx (discord.ext.commands.Context): The Discord context associated
                with the message.

        Notes:
            This will destroy the player assigned to your guild, also deleting
            any queued songs and settings.
        """
        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            embed = discord.Embed(
                title="",
                description="I am not currently connected to a voice channel.",
                color=discord.Color.yellow(),
            )
            return await ctx.send(embed=embed)

        await ctx.message.add_reaction("👋")
        await self.cleanup(ctx.guild)


async def setup(bot):
    await bot.add_cog(Music(bot))
