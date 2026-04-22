"""Guild-scoped player: connects, plays the next queue item, handles auto-recommend."""
from __future__ import annotations

import asyncio
import logging
import re
from typing import TYPE_CHECKING

import discord

from .audio import (
    Track,
    fetch_youtube_mix,
    make_ffmpeg_source,
    resolve_track,
)
from .embeds import now_playing_embed
from .queue import GuildQueue, QueueItem, QueueManager

if TYPE_CHECKING:
    from discord.ext import commands

log = logging.getLogger(__name__)

VIDEO_ID_RE = re.compile(r"(?:v=|youtu\.be/|/shorts/)([A-Za-z0-9_-]{11})")


def extract_video_id(url: str) -> str | None:
    m = VIDEO_ID_RE.search(url)
    return m.group(1) if m else None


class GuildPlayer:
    """Owns one voice client and its playback loop for one guild."""

    def __init__(
        self,
        bot: commands.Bot,
        guild: discord.Guild,
        queue: GuildQueue,
        queues: QueueManager,
    ) -> None:
        self.bot = bot
        self.guild = guild
        self.queue = queue
        self._queues = queues
        self.voice: discord.VoiceClient | None = None
        self.current: Track | None = None
        self.now_playing_message: discord.Message | None = None
        self._play_next_event = asyncio.Event()
        self._task: asyncio.Task | None = None
        self._closed = False

    async def ensure_connected(self, channel: discord.VoiceChannel) -> None:
        if self.voice and self.voice.is_connected():
            if self.voice.channel != channel:
                await self.voice.move_to(channel)
            return
        self.voice = await channel.connect(self_deaf=True)

    def start(self, channel: discord.abc.Messageable) -> None:
        if self._task is None or self._task.done():
            self._task = self.bot.loop.create_task(self._run(channel))

    async def _run(self, channel: discord.abc.Messageable) -> None:
        try:
            while not self._closed:
                item = self.queue.pop_next()
                if item is None:
                    if self.queue.autorecommend and self.queue.last_played_video_id:
                        await self._extend_with_mix(self.queue.last_played_video_id)
                        continue
                    break

                try:
                    track = await resolve_track(item.query, requested_by=item.requested_by)
                except Exception as exc:
                    log.exception("Failed to resolve %s", item.query)
                    await channel.send(f"Skipped `{item.display_title}`: {exc}")
                    continue

                self.current = track
                self.queue.last_played_video_id = (
                    extract_video_id(track.webpage_url) or self.queue.last_played_video_id
                )

                if self.voice is None or not self.voice.is_connected():
                    log.warning("Voice dropped before play; aborting")
                    return

                source = make_ffmpeg_source(track)
                self._play_next_event.clear()
                self.voice.play(source, after=self._after_play)

                await self._send_now_playing(channel)
                await self._play_next_event.wait()
                self.current = None

            if self.voice and self.voice.is_connected():
                await self._send_idle_message(channel)
        finally:
            self._task = None

    async def _extend_with_mix(self, vid: str) -> None:
        mix = await fetch_youtube_mix(vid, limit=5)
        if not mix:
            return
        self.queue.extend(
            [
                QueueItem(
                    query=m.webpage_url,
                    display_title=m.title,
                    requested_by="auto-recommend",
                )
                for m in mix
            ]
        )

    def _after_play(self, error: Exception | None) -> None:
        if error:
            log.error("Playback error: %s", error)
        self.bot.loop.call_soon_threadsafe(self._play_next_event.set)

    async def _send_now_playing(self, channel: discord.abc.Messageable) -> None:
        from .cogs.views import ControlPanelView  # local import to avoid cycle

        if self.current is None:
            return
        embed = now_playing_embed(self.current, self.queue)
        view = ControlPanelView(self)

        if self.now_playing_message:
            try:
                await self.now_playing_message.delete()
            except discord.HTTPException:
                pass
        self.now_playing_message = await channel.send(embed=embed, view=view)

    async def _send_idle_message(self, channel: discord.abc.Messageable) -> None:
        try:
            await channel.send("Queue is empty. Use `/play` to add songs.")
        except discord.HTTPException:
            pass

    async def skip(self) -> None:
        if self.voice and self.voice.is_playing():
            self.voice.stop()

    async def pause_toggle(self) -> str:
        if not self.voice:
            return "not connected"
        if self.voice.is_paused():
            self.voice.resume()
            return "resumed"
        if self.voice.is_playing():
            self.voice.pause()
            return "paused"
        return "idle"

    async def shuffle(self) -> None:
        self.queue.shuffle()

    async def toggle_autorecommend(self) -> bool:
        self.queue.autorecommend = not self.queue.autorecommend
        return self.queue.autorecommend

    async def disconnect(self) -> None:
        self._closed = True
        self.queue.clear()
        if self.voice and self.voice.is_connected():
            if self.voice.is_playing() or self.voice.is_paused():
                self.voice.stop()
            await self.voice.disconnect(force=True)
        self._queues.drop(self.guild.id)
        self._play_next_event.set()

    async def refresh_panel(self, interaction: discord.Interaction) -> None:
        if not self.current:
            await interaction.response.send_message(
                "Nothing is playing.", ephemeral=True
            )
            return
        await interaction.response.edit_message(
            embed=now_playing_embed(self.current, self.queue)
        )


class PlayerManager:
    def __init__(self, queues: QueueManager) -> None:
        self.queues = queues
        self._players: dict[int, GuildPlayer] = {}

    def get(self, bot: commands.Bot, guild: discord.Guild) -> GuildPlayer:
        p = self._players.get(guild.id)
        if p is None or p._closed:
            p = GuildPlayer(bot, guild, self.queues.get(guild.id), self.queues)
            self._players[guild.id] = p
        return p

    def drop(self, guild_id: int) -> None:
        self._players.pop(guild_id, None)
