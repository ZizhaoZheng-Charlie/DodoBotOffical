"""Route an arbitrary /play argument to either a direct resolver or a picker."""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto

from .audio import SearchResult
from .spotify_client import SpotifyClient, SpotifyTrackRef

YOUTUBE_URL_RE = re.compile(
    r"https?://(?:www\.)?(?:youtube\.com|youtu\.be|music\.youtube\.com)/\S+"
)
SPOTIFY_URL_RE = re.compile(r"https?://open\.spotify\.com/\S+")


class InputKind(Enum):
    YOUTUBE_URL = auto()
    SPOTIFY_URL = auto()
    TEXT_QUERY = auto()


@dataclass
class RoutedInput:
    kind: InputKind
    value: str


def classify(user_input: str) -> RoutedInput:
    s = user_input.strip()
    if YOUTUBE_URL_RE.match(s):
        return RoutedInput(InputKind.YOUTUBE_URL, s)
    if SPOTIFY_URL_RE.match(s):
        return RoutedInput(InputKind.SPOTIFY_URL, s)
    return RoutedInput(InputKind.TEXT_QUERY, s)


@dataclass
class QueryPlan:
    """Result of pre-flight routing.

    - ``direct_target`` set => play it immediately (URL or Spotify search result).
    - ``picker_results`` set => ask user to pick from a list.
    - ``bulk_refs`` set => expand into multiple tracks (Spotify album/playlist/artist).
    """

    direct_target: str | None = None
    picker_results: list[SearchResult] | None = None
    bulk_refs: list[SpotifyTrackRef] | None = None
    summary: str = ""


def plan_for_url(routed: RoutedInput, spotify: SpotifyClient) -> QueryPlan:
    if routed.kind is InputKind.YOUTUBE_URL:
        return QueryPlan(direct_target=routed.value, summary="YouTube link")

    if routed.kind is InputKind.SPOTIFY_URL:
        parsed = SpotifyClient.parse_url(routed.value)
        if not parsed:
            return QueryPlan(summary="Unrecognised Spotify URL")
        kind, _ = parsed
        if not spotify.enabled:
            return QueryPlan(summary="Spotify is not configured on this bot")
        refs = spotify.tracks_from_url(routed.value)
        if not refs:
            return QueryPlan(summary="Spotify link returned no tracks")
        if kind == "track":
            return QueryPlan(direct_target=refs[0].query, summary=refs[0].label)
        return QueryPlan(bulk_refs=refs, summary=f"Spotify {kind} ({len(refs)} tracks)")

    raise ValueError("plan_for_url expects a URL input")
