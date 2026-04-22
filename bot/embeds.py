"""Rich embed builders. All user-facing output comes from here."""
from __future__ import annotations

import discord

from .audio import SearchResult, Track
from .queue import GuildQueue

BRAND_COLOR = discord.Color.from_rgb(255, 140, 0)  # DodoBot orange
ERROR_COLOR = discord.Color.from_rgb(235, 87, 87)
SUCCESS_COLOR = discord.Color.from_rgb(46, 204, 113)


def now_playing_embed(track: Track, queue: GuildQueue) -> discord.Embed:
    embed = discord.Embed(
        title=track.title,
        url=track.webpage_url or None,
        description=f"Requested by **{track.requested_by or 'unknown'}**",
        color=BRAND_COLOR,
    )
    embed.set_author(name="Now playing")
    if track.thumbnail:
        embed.set_thumbnail(url=track.thumbnail)
    embed.add_field(name="Duration", value=track.duration_str, inline=True)
    if track.uploader:
        embed.add_field(name="Uploader", value=track.uploader, inline=True)
    embed.add_field(
        name="Up next",
        value=f"{len(queue)} in queue"
        + (" - auto-recommend ON" if queue.autorecommend else ""),
        inline=False,
    )
    embed.set_footer(text="DodoBot - use the buttons below to control playback")
    return embed


def added_to_queue_embed(track: Track, position: int) -> discord.Embed:
    embed = discord.Embed(
        title=f"Added - {track.title}",
        url=track.webpage_url or None,
        color=SUCCESS_COLOR,
    )
    if track.thumbnail:
        embed.set_thumbnail(url=track.thumbnail)
    embed.add_field(name="Duration", value=track.duration_str, inline=True)
    embed.add_field(name="Position", value=f"#{position}", inline=True)
    embed.add_field(name="Requested by", value=track.requested_by or "-", inline=True)
    return embed


def picker_embed(query: str, results: list[SearchResult]) -> discord.Embed:
    embed = discord.Embed(
        title=f'Results for "{query}"',
        description="Pick a track from the dropdown below.",
        color=BRAND_COLOR,
    )
    for i, r in enumerate(results, 1):
        dur = f" [{_fmt_dur(r.duration)}]" if r.duration else ""
        up = f" - {r.uploader}" if r.uploader else ""
        embed.add_field(
            name=f"{i}. {r.title[:80]}",
            value=f"{up}{dur}",
            inline=False,
        )
    embed.set_footer(text="Selection expires in 60 seconds")
    return embed


def queue_embed(queue: GuildQueue) -> discord.Embed:
    if not queue:
        return discord.Embed(
            title="Queue is empty",
            description="Add songs with `/play`",
            color=BRAND_COLOR,
        )

    embed = discord.Embed(
        title=f"Queue ({len(queue)} items)",
        color=BRAND_COLOR,
    )
    lines = []
    for i, item in enumerate(list(queue.items)[:15], 1):
        lines.append(f"**{i}.** {item.display_title} - _{item.requested_by}_")
    if len(queue) > 15:
        lines.append(f"...and {len(queue) - 15} more")
    embed.description = "\n".join(lines)
    if queue.autorecommend:
        embed.set_footer(text="Auto-recommend is ON")
    return embed


def error_embed(message: str) -> discord.Embed:
    return discord.Embed(
        title="Error", description=message, color=ERROR_COLOR
    )


def info_embed(title: str, message: str = "") -> discord.Embed:
    return discord.Embed(title=title, description=message, color=BRAND_COLOR)


def _fmt_dur(seconds: int | None) -> str:
    if not seconds:
        return "live"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
