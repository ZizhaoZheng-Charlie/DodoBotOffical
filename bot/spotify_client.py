"""Spotify integration using spotipy with Client Credentials flow."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Literal

try:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
except ImportError:  # pragma: no cover
    spotipy = None  # type: ignore[assignment]
    SpotifyClientCredentials = None  # type: ignore[assignment]

log = logging.getLogger(__name__)

SPOTIFY_URL_RE = re.compile(
    r"https?://open\.spotify\.com/(?:intl-[a-z]+/)?(track|album|playlist|artist)/([A-Za-z0-9]+)"
)

SpotifyKind = Literal["track", "album", "playlist", "artist"]


@dataclass
class SpotifyTrackRef:
    """A Spotify track reduced to a search string we feed to YouTube."""

    title: str
    artists: str
    query: str

    @property
    def label(self) -> str:
        return f"{self.title} - {self.artists}"


class SpotifyClient:
    def __init__(self, client_id: str | None, client_secret: str | None) -> None:
        self._sp: spotipy.Spotify | None = None
        if spotipy and client_id and client_secret:
            auth = SpotifyClientCredentials(
                client_id=client_id, client_secret=client_secret
            )
            self._sp = spotipy.Spotify(auth_manager=auth)
        else:
            log.info("Spotify disabled: credentials missing or spotipy not installed")

    @property
    def enabled(self) -> bool:
        return self._sp is not None

    @staticmethod
    def parse_url(url: str) -> tuple[SpotifyKind, str] | None:
        m = SPOTIFY_URL_RE.search(url)
        if not m:
            return None
        kind = m.group(1)
        return kind, m.group(2)  # type: ignore[return-value]

    def _track_to_ref(self, track: dict) -> SpotifyTrackRef:
        title = track.get("name") or "Unknown"
        artists = ", ".join(a["name"] for a in track.get("artists", []) if a.get("name"))
        return SpotifyTrackRef(
            title=title, artists=artists, query=f"{title} {artists}".strip()
        )

    def tracks_from_url(self, url: str) -> list[SpotifyTrackRef]:
        if not self._sp:
            return []
        parsed = self.parse_url(url)
        if not parsed:
            return []
        kind, sid = parsed
        refs: list[SpotifyTrackRef] = []
        if kind == "track":
            t = self._sp.track(sid)
            refs.append(self._track_to_ref(t))
        elif kind == "album":
            data = self._sp.album_tracks(sid)
            while data:
                refs.extend(self._track_to_ref(t) for t in data["items"] if t)
                data = self._sp.next(data) if data.get("next") else None
        elif kind == "playlist":
            data = self._sp.playlist_tracks(sid)
            while data:
                refs.extend(
                    self._track_to_ref(t["track"])
                    for t in data["items"]
                    if t and t.get("track")
                )
                data = self._sp.next(data) if data.get("next") else None
        elif kind == "artist":
            data = self._sp.artist_top_tracks(sid)
            refs.extend(self._track_to_ref(t) for t in data.get("tracks", []))
        return refs

    def search_tracks(self, query: str, *, limit: int = 5) -> list[SpotifyTrackRef]:
        if not self._sp:
            return []
        res = self._sp.search(q=query, type="track", limit=limit)
        items = (res or {}).get("tracks", {}).get("items", [])
        return [self._track_to_ref(t) for t in items if t]
