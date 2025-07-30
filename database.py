from datetime import datetime, timedelta
import discord
import logging
import openai
import random
import sqlite3
import typing

from cogs import music_player

logger = logging.getLogger("database")

class Database:
    def __init__(self, path: str):
        self.path = path
        self._ensure_db()

    def _ensure_db(self):
        with sqlite3.connect(self.path) as conn:

            # Table for keeping track of servers
            conn.execute("""
                CREATE TABLE IF NOT EXISTS server (
                    id INTEGER PRIMARY KEY,
                    discord_id INTEGER NOT NULL UNIQUE
                )
            """)

            # Table for keeping track of channels
            conn.execute("""
                CREATE TABLE IF NOT EXISTS channel (
                    id INTEGER PRIMARY KEY,
                    discord_id INTEGER NOT NULL UNIQUE
                )
            """)

            # Table for keeping track of users
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user (
                    id INTEGER PRIMARY KEY,
                    discord_id INTEGER NOT NULL UNIQUE
                )
            """)

            # Create the activity table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS activity_change (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    before_activity_type TEXT,
                    before_activity_name TEXT,
                    before_activity_status TEXT NOT NULL,
                    after_activity_type TEXT,
                    after_activity_name TEXT,
                    after_activity_status TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
                )
            """)
            
            # Create the song request table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS song_request (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    search_term TEXT NOT NULL,
                    song_title TEXT,
                    song_artist TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
                )
            """)

            # Table for songs that actually get played
            conn.execute("""
                CREATE TABLE IF NOT EXISTS song_play (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    channel_id INTEGER NOT NULL,
                    search_term TEXT NOT NULL,
                    song_title TEXT,
                    song_artist TEXT,
                    finished BOOL DEFAULT 0,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
                )
            """)

            conn.commit()

    def _insert_server(self, discord_id: int = None) -> int:
        """
        Inserts Discord server ID into the 'server' table.
        
        This method takes an ID for a server used in Discord, and inserts it
        into the database. It ignores the case where the server ID is already
        present. It then returns the row ID regardless.

        Args:
            discord_id (int): The ID used to identify the server in Discord.

        Returns:
            int: The ID of the server in the server table.
        
        Examples:
            >>> db = Database("path.db")
            >>> db._insert_server(850610922256442889)
            12
        """
        with sqlite3.connect(self.path) as conn:
            cursor = conn.cursor()
            # Insert it; ignoring already exists error
            cursor.execute("""
                INSERT INTO server (discord_id)
                VALUES (?)
                ON CONFLICT(discord_id) DO NOTHING
                RETURNING id;
            """, (discord_id,))
            row = cursor.fetchone()
            if row:
                row_id = row[0]
            else:
                # Get row ID if it already exists and wasn't inserted
                cursor.execute("""
                    SELECT id FROM server WHERE discord_id = ?
                """, (discord_id,))
                row_id = cursor.fetchone()[0]
            return row_id

    def _insert_channel(self, discord_id: int = None) -> int:
        """
        Inserts Discord channel ID into the 'channel' table.
        
        This method takes an ID for a channel used in Discord, and inserts it
        into the database. It ignores the case where the channel ID is already
        present. It then returns the row ID regardless.

        Args:
            discord_id (int): The ID used to identify the channel in Discord.

        Returns:
            int: The ID of the channel in the channel table.
        
        Examples:
            >>> db = Database("path.db")
            >>> db._insert_channel(8506109222564428891)
            12
        """
        with sqlite3.connect(self.path) as conn:
            cursor = conn.cursor()
            # Insert it; ignoring already exists error
            cursor.execute("""
                INSERT INTO channel (discord_id)
                VALUES (?)
                ON CONFLICT(discord_id) DO NOTHING
                RETURNING id;
            """, (discord_id,))
            row = cursor.fetchone()
            if row:
                row_id = row[0]
            else:
                # Get row ID if it already exists and wasn't inserted
                cursor.execute("""
                    SELECT id FROM channel WHERE discord_id = ?
                """, (discord_id,))
                row_id = cursor.fetchone()[0]
            return row_id

    def _insert_user(self, discord_id: int = None) -> int:
        """
        Inserts Discord user ID into the 'user' table.
        
        This method takes an ID for a user used in Discord, and inserts it
        into the database. It ignores the case where the user ID is already
        present. It then returns the row ID regardless.

        Args:
            discord_id (int): The ID used to identify the user in Discord.

        Returns:
            int: The ID of the user in the user table.
        
        Examples:
            >>> db = Database("path.db")
            >>> db._insert_user(850610922256442889)
            12
        """
        with sqlite3.connect(self.path) as conn:
            cursor = conn.cursor()
            # Insert it; ignoring already exists error
            cursor.execute("""
                INSERT INTO user (discord_id)
                VALUES (?)
                ON CONFLICT(discord_id) DO NOTHING
                RETURNING id;
            """, (discord_id,))
            row = cursor.fetchone()
            if row:
                row_id = row[0]
            else:
                # Get row ID if it already exists and wasn't inserted
                cursor.execute("""
                    SELECT id FROM user WHERE discord_id = ?
                """, (discord_id,))
                row_id = cursor.fetchone()[0]
            return row_id

    def insert_activity_change(
        self,
        before: discord.Member,
        after: discord.Member):
        """
        Inserts an activity change into the database.

        This method takes two discord.Memeber objects, and records the change
        in activity into the 'activity_change' table.

        Args:
            before (discord.Member): The previous user status.
            after (discord.Member): The current user status.

        Raises:
            ValueError: If the before and after activity do not refer to the
                same user.

        Examples:
            >>> @commands.Cog.listener()
            >>> async def on_presence_update(
            ...     self,
            ...     before: discord.Member,
            ...     after: discord.Member):
            ...     db = Database("path.db")
            ...     db.insert_activity_change(before, after)
            >>>
        """
        # Ensure the users are the same
        if before.id != after.id:
            raise ValueError("User IDs do not match.")
        user_id = self._insert_user(before.id)
        # Get activities if they exist
        before_type = before.activity.type.name if before.activity else None
        before_name = before.activity.name if before.activity else None
        after_type = after.activity.type.name if after.activity else None
        after_name = after.activity.name if after.activity else None
        # Insert the activity change
        with sqlite3.connect(self.path) as conn:
            conn.execute("""
                INSERT INTO activity_change (
                    user_id,
                    before_activity_type,
                    before_activity_name,
                    before_activity_status,
                    after_activity_type,
                    after_activity_name,
                    after_activity_status
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                user_id,
                before_type,
                before_name,
                before.status.name,
                after_type,
                after_name,
                after.status.name
            ))

    def insert_song_request(
        self,
        message: discord.Message,
        source: music_player.YTDLSource):
        """
        Inserts a song request into the database.

        This method takes a message and its derived music source and inserts
        the relevant information into the 'song_request' table.

        Args:
            message (discord.Message): The Discord message requesting the song.
            source (music_player.YTDLSource): The audio source.
        """
        # Insert the information
        with sqlite3.connect(self.path) as conn:
            conn.execute("""
                INSERT INTO song_request (
                    user_id,
                    channel_id,
                    search_term,
                    song_title,
                    song_artist
                ) VALUES (
                    ?, ?, ?, ?, ?
                )
            """, (
                self._insert_user(message.author.id),
                self._insert_channel(message.channel.id),
                source.search_term,
                source.song_title,
                source.artist
            ))

    def insert_song_play(
        self,
        channel_id: int,
        source: music_player.YTDLSource):
        """
        Inserts a song play into the database.

        This method takes a channel and the song being played and inserts the
        relevant information into the 'song_play' table.

        Args:
            channel (int): The Discord channel the song is being played in.
            source (music_player.YTDLSource): The audio source.

        Returns:
            int: The row ID of the entered song. Used to update 'played' value.
        """
        user_id = self._insert_user(source.requester.id) if source.requester else None
        channel_id = self._insert_channel(channel_id)
        # Insert the information
        with sqlite3.connect(self.path) as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO song_play (
                    user_id,
                    channel_id,
                    search_term,
                    song_title,
                    song_artist
                ) VALUES (
                    ?, ?, ?, ?, ?
                )
            """, (
                user_id,
                channel_id,
                source.search_term,
                source.song_title,
                source.artist
            ))
            return cur.lastrowid

    def update_song_play(self, song_play_id: int, finished: bool):
        """
        Updates a song_play entry on whether or not it was finished.

        When a song plays, we want to know if it was finished or not. This
        implies that either a user didn't want to hear it anymore, or that the
        bot chose the wrong song from the search term.

        Args:
            song_play_id (int): The row ID within the database for the song
                play.
            finished (bool): Whether or not the song was completed.
        """
        with sqlite3.connect(self.path) as conn:
            conn.execute("""
                UPDATE
                    song_play
                SET
                    finished = ?
                WHERE
                    id = ?
            """, (finished, song_play_id))

    def get_activity_stats(
        self,
        member: typing.Union[discord.Member, int],
        start: datetime = datetime.now() - timedelta(days=30)
        ) -> dict[str, timedelta]:
        """
        Gets stats on the activities of the given member.

        This method searches the database for activity changes by the given
        user and computes the amount of time spent in each activity.

        Args:
            member (discord.Member): The Discord member to get stats for.
            start (datetime): The earliest activity change to get.

        Returns:
            dict[str, timedelta]: A dictionary of activity names and
                seconds in each.
        """
        # Get member Discord ID and convert to DB ID
        member_id = member.id if isinstance(member, discord.Member) else member
        member_id = self._insert_user(member_id)
        # Pull all activities for this user
        with sqlite3.connect(self.path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    before_activity_name,
                    after_activity_name,
                    timestamp
                FROM
                    activity_change
                WHERE
                    user_id = (?) AND
                    timestamp > (?)
            """, (member_id, start))
            activities = cursor.fetchall()
        # Collect activities
        activity_stats = {}
        for first, second in zip(activities, activities[1:]):
            if first[1] == second[0]:
                activity_name = first[1]
                activity_time = \
                    datetime.fromisoformat(second[2]) - \
                    datetime.fromisoformat(first[2])
                if activity_name in activity_stats:
                    activity_stats[activity_name] += activity_time
                else:
                    activity_stats[activity_name] = activity_time
        if None in activity_stats:
            del activity_stats[None]
        return activity_stats

    def get_next_song(self, users: list[int], channels: list[int], limit: int = 100, cutoff: datetime = None):
        
        _cutoff = datetime.now() - timedelta(hours=1) if not cutoff else cutoff

        print("users:", users)
        print("channels:", channels)

        # Convert user IDs to row IDs
        with sqlite3.connect(self.path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    id
                FROM
                    user
                WHERE
                    discord_id IN (%s);""" % ",".join("?" for _ in users),
                tuple(users))
            user_ids = [row[0] for row in cursor.fetchall()]

            cursor.execute("""
                SELECT
                    id
                FROM
                    channel
                WHERE
                    discord_id IN (%s);""" % ",".join("?" for _ in channels),
                tuple(channels))
            channel_ids = [row[0] for row in cursor.fetchall()]

            # Pull song plays from the given channels
            logger.info("Getting past song plays")
            cursor.execute("""
                SELECT
                    song_title,
                    song_artist,
                    COUNT(*) AS count
                FROM
                    song_play
                WHERE
                    user_id IN (%s) AND
                    channel_id IN (%s) AND
                    finished = 1 AND
                    timestamp < ?
                GROUP BY
                    song_title,
                    song_artist
                ORDER BY
                    count DESC
                LIMIT ?;
            """ % (
                ",".join(str(id) for id in user_ids),
                ",".join(str(id) for id in channel_ids)
            ), (_cutoff, limit))
            old_song_plays = cursor.fetchall()

        # Compile results into cleaner list of dicts
        candidates = [{"title": t, "artist": a, "plays": p} for t, a, p in old_song_plays]
        print("candidates:", candidates)

        # Get recent song plays
        logger.info("Getting recent song plays")
        with sqlite3.connect(self.path) as conn:
            cursor = conn.cursor()
            # Get recent songs to avoid
            cursor.execute("""
                SELECT
                    song_title,
                    song_artist
                FROM
                    song_play
                WHERE
                    channel_id IN (%s) AND
                    timestamp >= ?
                GROUP BY
                    song_title,
                    song_artist;
            """ % (",".join(str(id) for id in channel_ids)), (_cutoff, ))
            recent_song_plays = cursor.fetchall()
        print("recent:", recent_song_plays)

        # Remove all songs that were recently played
        def keep(song_play: dict[str, str, int]):
            return not (song_play["title"], song_play["artist"]) in recent_song_plays
        candidates = list(filter(keep, candidates))
        print("filtered candidates:", candidates)

        if len(candidates) > 0:
            candidate = random.choice(candidates)
            return {"title": candidate["title"], "artist": candidate["artist"]}
        # If we have no songs left to play, get a recommendation from ChatGPT
        else:

            # Get last five or so completed song plays
            with sqlite3.connect(self.path) as conn:
                cursor = conn.cursor()
                # Get recent songs to avoid
                cursor.execute("""
                    SELECT
                        song_title,
                        song_artist
                    FROM
                        song_play
                    WHERE
                        channel_id IN (%s) AND
                        finished = 1
                    GROUP BY
                        song_title,
                        song_artist
                    ORDER BY
                        timestamp DESC
                    LIMIT 5;
                """ % (",".join(str(id) for id in channel_ids)))
                last_five = cursor.fetchall()

                print("last five song plays:", last_five)

            setup_prompt = "I'm going to give you a list of songs and artists "\
                           "formatted as a Python list of dicts where the "\
                           "song title is the 'title' key and the artist is "\
                           "the 'artist' key. I want you to return a song "\
                           "title and artist that you would recommend based "\
                           "on the given songs. Don't be afraid to branch out "\
                           "and vary songs; the same artist should not be "\
                           "repeated more than twice. You should give me only a bare text "\
                           "string formatted as a Python dict where the "\
                           "'title' key is the song title, and the 'artist' "\
                           "key is the song's artist. Don't add anything other "\
                           "than this dict."
            user_prompt = []
            completion = openai.OpenAI().chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": setup_prompt},
                    {"role": "user", "content": str(last_five)}
                ]
            )
            return eval(completion.choices[0].message.content)