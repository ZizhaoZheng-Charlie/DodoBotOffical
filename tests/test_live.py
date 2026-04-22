"""Live integration tests - require network. Run with: pytest -m integration"""
import asyncio
import os

import pytest

pytestmark = pytest.mark.integration


def _sp_creds() -> tuple[str | None, str | None]:
    cid = os.getenv("SPOTIFY_CLIENT_ID") or os.getenv("SPOTIFY_ID")
    sec = os.getenv("SPOTIFY_CLIENT_SECRET") or os.getenv("SPOTIFY_SECRET")
    return cid, sec


def test_yt_dlp_resolves_known_video():
    from bot.audio import resolve_track
    track = asyncio.run(
        resolve_track("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    )
    assert track.title
    assert track.url.startswith("http")
    assert track.duration and track.duration > 60


def test_yt_dlp_search_returns_hits():
    from bot.audio import search_youtube
    results = asyncio.run(search_youtube("lofi hip hop", limit=3))
    assert len(results) >= 1
    assert all(r.webpage_url.startswith("http") for r in results)


def _skip_if_spotify_premium_gated(exc: Exception) -> None:
    # Spotify now restricts Client Credentials access for apps whose owner
    # does not have an active Premium subscription. That is an account-side
    # limitation, not a bug in our client - skip rather than fail.
    msg = str(exc)
    if "premium" in msg.lower() or "403" in msg:
        pytest.skip(f"Spotify app owner lacks Premium / 403: {msg[:120]}")


@pytest.mark.skipif(not all(_sp_creds()), reason="Spotify creds not provided")
def test_spotify_search():
    from bot.spotify_client import SpotifyClient

    cid, sec = _sp_creds()
    sc = SpotifyClient(cid, sec)
    assert sc.enabled
    try:
        hits = sc.search_tracks("fly me to the moon", limit=3)
    except Exception as e:
        _skip_if_spotify_premium_gated(e)
        raise
    assert len(hits) >= 1
    assert all(h.title and h.artists for h in hits)


@pytest.mark.skipif(not all(_sp_creds()), reason="Spotify creds not provided")
def test_spotify_playlist_url():
    from bot.spotify_client import SpotifyClient

    cid, sec = _sp_creds()
    sc = SpotifyClient(cid, sec)
    try:
        refs = sc.tracks_from_url(
            "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
        )
    except Exception as e:
        _skip_if_spotify_premium_gated(e)
        raise
    assert len(refs) >= 1
