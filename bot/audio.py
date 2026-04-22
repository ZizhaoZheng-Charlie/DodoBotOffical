"""yt-dlp + FFmpeg streaming audio source (no disk writes)."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import discord
from yt_dlp import YoutubeDL

log = logging.getLogger(__name__)

YDL_BASE_OPTS: dict[str, Any] = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "skip_download": True,
    "extract_flat": False,
    "source_address": "0.0.0.0",
    "default_search": "ytsearch5",
}

FFMPEG_OPTS = {
    "before_options": (
        "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
    ),
    "options": "-vn -loglevel warning",
}


@dataclass
class Track:
    """A resolved audio track we can stream."""

    title: str
    url: str
    webpage_url: str
    duration: int | None
    thumbnail: str | None
    uploader: str | None
    requested_by: str = ""

    @property
    def duration_str(self) -> str:
        if not self.duration:
            return "live"
        m, s = divmod(int(self.duration), 60)
        h, m = divmod(m, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


@dataclass
class SearchResult:
    """A single search hit (not yet resolved to a stream URL)."""

    title: str
    webpage_url: str
    duration: int | None
    uploader: str | None
    thumbnail: str | None = None


def _from_info(info: dict[str, Any], requested_by: str = "") -> Track:
    return Track(
        title=info.get("title") or "Unknown",
        url=info["url"],
        webpage_url=info.get("webpage_url") or info.get("original_url") or "",
        duration=info.get("duration"),
        thumbnail=info.get("thumbnail"),
        uploader=info.get("uploader") or info.get("channel"),
        requested_by=requested_by,
    )


async def resolve_track(url_or_query: str, *, requested_by: str = "") -> Track:
    """Resolve an arbitrary URL / search string to a single streamable Track."""

    def _extract() -> dict[str, Any]:
        opts = dict(YDL_BASE_OPTS)
        opts["default_search"] = "ytsearch1"
        with YoutubeDL(opts) as ydl:
            data = ydl.extract_info(url_or_query, download=False)
            if data is None:
                raise RuntimeError("yt-dlp returned no data")
            if "entries" in data:
                entries = [e for e in data["entries"] if e]
                if not entries:
                    raise RuntimeError("No results")
                data = entries[0]
            return data

    info = await asyncio.to_thread(_extract)
    return _from_info(info, requested_by=requested_by)


async def search_youtube(query: str, *, limit: int = 5) -> list[SearchResult]:
    """Return up to `limit` YouTube candidates for a text query."""

    def _extract() -> list[dict[str, Any]]:
        opts = dict(YDL_BASE_OPTS)
        opts["default_search"] = f"ytsearch{limit}"
        opts["extract_flat"] = "in_playlist"
        with YoutubeDL(opts) as ydl:
            data = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
            if not data or "entries" not in data:
                return []
            return [e for e in data["entries"] if e]

    entries = await asyncio.to_thread(_extract)
    results: list[SearchResult] = []
    for e in entries:
        webpage = e.get("webpage_url") or e.get("url") or ""
        if webpage and not webpage.startswith("http"):
            webpage = f"https://www.youtube.com/watch?v={e.get('id', '')}"
        results.append(
            SearchResult(
                title=e.get("title") or "Unknown",
                webpage_url=webpage,
                duration=e.get("duration"),
                uploader=e.get("uploader") or e.get("channel"),
                thumbnail=(e.get("thumbnails") or [{}])[-1].get("url")
                if e.get("thumbnails")
                else None,
            )
        )
    return results


async def fetch_youtube_mix(video_id: str, *, limit: int = 10) -> list[SearchResult]:
    """Fetch the YouTube Mix (radio) for a video id, used by auto-recommend."""

    def _extract() -> list[dict[str, Any]]:
        opts = dict(YDL_BASE_OPTS)
        opts["noplaylist"] = False
        opts["extract_flat"] = "in_playlist"
        opts["playlistend"] = limit + 1
        url = f"https://www.youtube.com/watch?v={video_id}&list=RD{video_id}"
        with YoutubeDL(opts) as ydl:
            data = ydl.extract_info(url, download=False)
            if not data or "entries" not in data:
                return []
            return [e for e in data["entries"] if e]

    entries = await asyncio.to_thread(_extract)
    out: list[SearchResult] = []
    for e in entries:
        if e.get("id") == video_id:
            continue
        wid = e.get("id")
        if not wid:
            continue
        out.append(
            SearchResult(
                title=e.get("title") or "Unknown",
                webpage_url=f"https://www.youtube.com/watch?v={wid}",
                duration=e.get("duration"),
                uploader=e.get("uploader") or e.get("channel"),
            )
        )
        if len(out) >= limit:
            break
    return out


def make_ffmpeg_source(track: Track) -> discord.AudioSource:
    """Wrap a Track in a discord.FFmpegPCMAudio + VolumeTransformer."""
    src = discord.FFmpegPCMAudio(track.url, **FFMPEG_OPTS)
    return discord.PCMVolumeTransformer(src, volume=1.0)
