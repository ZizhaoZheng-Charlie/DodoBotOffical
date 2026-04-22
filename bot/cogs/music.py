"""Slash-command surface for the music bot."""
from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from ..audio import resolve_track, search_youtube
from ..embeds import (
    added_to_queue_embed,
    error_embed,
    info_embed,
    picker_embed,
    queue_embed,
)
from ..player import PlayerManager
from ..queue import QueueItem, QueueManager
from ..search import InputKind, classify, plan_for_url
from ..spotify_client import SpotifyClient
from .views import SongPickerView

log = logging.getLogger(__name__)


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot, spotify: SpotifyClient) -> None:
        self.bot = bot
        self.spotify = spotify
        self.queues = QueueManager()
        self.players = PlayerManager(self.queues)

    # ---- helpers ----------------------------------------------------------

    async def _ensure_voice(
        self, interaction: discord.Interaction
    ) -> discord.VoiceChannel | None:
        user = interaction.user
        if not isinstance(user, discord.Member):
            return None
        if not user.voice or not user.voice.channel:
            await interaction.followup.send(
                embed=error_embed("Join a voice channel first."), ephemeral=True
            )
            return None
        channel = user.voice.channel
        if not isinstance(channel, discord.VoiceChannel):
            await interaction.followup.send(
                embed=error_embed("You must be in a standard voice channel."),
                ephemeral=True,
            )
            return None
        return channel

    # ---- commands ---------------------------------------------------------

    @app_commands.command(name="play", description="Play a song, playlist, or search query")
    @app_commands.describe(query="YouTube URL, Spotify URL, or search text")
    async def play(self, interaction: discord.Interaction, query: str) -> None:
        await interaction.response.defer(thinking=True)

        if interaction.guild is None:
            await interaction.followup.send(
                embed=error_embed("This command only works in a server."), ephemeral=True
            )
            return

        channel = await self._ensure_voice(interaction)
        if channel is None:
            return

        player = self.players.get(self.bot, interaction.guild)
        await player.ensure_connected(channel)

        routed = classify(query)
        requester = interaction.user.display_name

        if routed.kind is InputKind.YOUTUBE_URL:
            await self._enqueue_direct(
                interaction, player, routed.value, requester=requester
            )
            return

        if routed.kind is InputKind.SPOTIFY_URL:
            plan = plan_for_url(routed, self.spotify)
            if plan.direct_target:
                await self._enqueue_direct(
                    interaction, player, plan.direct_target,
                    requester=requester, label=plan.summary,
                )
                return
            if plan.bulk_refs:
                items = [
                    QueueItem(
                        query=r.query, display_title=r.label, requested_by=requester
                    )
                    for r in plan.bulk_refs
                ]
                player.queue.extend(items)
                await interaction.followup.send(
                    embed=info_embed(
                        "Added from Spotify",
                        f"{plan.summary} added - queue is now {len(player.queue)}.",
                    )
                )
                player.start(interaction.channel)
                return
            await interaction.followup.send(
                embed=error_embed(plan.summary or "Spotify link didn't work.")
            )
            return

        # TEXT_QUERY -> show picker
        results = await search_youtube(query, limit=5)
        if not results:
            await interaction.followup.send(
                embed=error_embed(f'No results for "{query}".')
            )
            return

        view = SongPickerView(
            results,
            player=player,
            requester=interaction.user,
            channel=interaction.channel,
        )
        message = await interaction.followup.send(
            embed=picker_embed(query, results), view=view
        )
        view.message = message

    async def _enqueue_direct(
        self,
        interaction: discord.Interaction,
        player,
        value: str,
        *,
        requester: str,
        label: str | None = None,
    ) -> None:
        try:
            track = await resolve_track(value, requested_by=requester)
        except Exception as exc:
            log.exception("resolve_track failed")
            await interaction.followup.send(
                embed=error_embed(f"Couldn't load that: {exc}")
            )
            return
        player.queue.push(
            QueueItem(
                query=track.webpage_url or value,
                display_title=label or track.title,
                requested_by=requester,
            )
        )
        await interaction.followup.send(
            embed=added_to_queue_embed(track, position=len(player.queue))
        )
        player.start(interaction.channel)

    @app_commands.command(name="pause", description="Pause or resume playback")
    async def pause(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            return
        player = self.players.get(self.bot, interaction.guild)
        state = await player.pause_toggle()
        await interaction.response.send_message(
            embed=info_embed(f"Playback {state}"), ephemeral=True
        )

    @app_commands.command(name="skip", description="Skip the current track")
    async def skip(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            return
        player = self.players.get(self.bot, interaction.guild)
        await player.skip()
        await interaction.response.send_message(
            embed=info_embed("Skipped"), ephemeral=True
        )

    @app_commands.command(name="queue", description="Show the queue")
    async def show_queue(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            return
        q = self.queues.get(interaction.guild.id)
        await interaction.response.send_message(embed=queue_embed(q))

    @app_commands.command(name="shuffle", description="Shuffle the queue")
    async def shuffle(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            return
        q = self.queues.get(interaction.guild.id)
        if not q:
            await interaction.response.send_message(
                embed=error_embed("Queue is empty."), ephemeral=True
            )
            return
        q.shuffle()
        await interaction.response.send_message(embed=info_embed("Queue shuffled"))

    @app_commands.command(name="clear", description="Clear the queue and stop playback")
    async def clear(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            return
        player = self.players.get(self.bot, interaction.guild)
        player.queue.clear()
        await player.skip()
        await interaction.response.send_message(embed=info_embed("Queue cleared"))

    @app_commands.command(
        name="autorecommend",
        description="Toggle auto-recommend (keep playing related YouTube tracks)",
    )
    async def autorecommend(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            return
        player = self.players.get(self.bot, interaction.guild)
        now_on = await player.toggle_autorecommend()
        await interaction.response.send_message(
            embed=info_embed(f"Auto-recommend: {'ON' if now_on else 'OFF'}")
        )

    @app_commands.command(name="disconnect", description="Disconnect the bot")
    async def disconnect(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            return
        player = self.players.get(self.bot, interaction.guild)
        await player.disconnect()
        await interaction.response.send_message(embed=info_embed("Disconnected"))


async def setup(bot: commands.Bot, spotify: SpotifyClient) -> None:
    await bot.add_cog(Music(bot, spotify))
