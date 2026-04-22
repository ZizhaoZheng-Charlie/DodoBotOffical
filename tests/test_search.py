"""Unit tests for input classification and Spotify URL parsing."""
from bot.search import InputKind, classify
from bot.spotify_client import SpotifyClient


class TestClassify:
    def test_youtube_watch(self):
        r = classify("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert r.kind is InputKind.YOUTUBE_URL

    def test_youtube_short_domain(self):
        r = classify("https://youtu.be/dQw4w9WgXcQ")
        assert r.kind is InputKind.YOUTUBE_URL

    def test_youtube_shorts(self):
        r = classify("https://www.youtube.com/shorts/jeCvbd7gejE")
        assert r.kind is InputKind.YOUTUBE_URL

    def test_youtube_music(self):
        r = classify("https://music.youtube.com/watch?v=abc")
        assert r.kind is InputKind.YOUTUBE_URL

    def test_spotify_track(self):
        r = classify("https://open.spotify.com/track/6rqhFgbbKwnb9MLmUQDhG6")
        assert r.kind is InputKind.SPOTIFY_URL

    def test_spotify_with_intl_prefix(self):
        r = classify("https://open.spotify.com/intl-ja/track/6rqhFgbbKwnb9MLmUQDhG6")
        assert r.kind is InputKind.SPOTIFY_URL

    def test_text_query(self):
        r = classify("bohemian rhapsody")
        assert r.kind is InputKind.TEXT_QUERY
        assert r.value == "bohemian rhapsody"

    def test_strips_whitespace(self):
        r = classify("  fly me to the moon  ")
        assert r.value == "fly me to the moon"


class TestSpotifyUrlParse:
    def test_track(self):
        out = SpotifyClient.parse_url(
            "https://open.spotify.com/track/6rqhFgbbKwnb9MLmUQDhG6"
        )
        assert out == ("track", "6rqhFgbbKwnb9MLmUQDhG6")

    def test_album(self):
        out = SpotifyClient.parse_url(
            "https://open.spotify.com/album/4aawyAB9vmqN3uQ7FjRGTy"
        )
        assert out == ("album", "4aawyAB9vmqN3uQ7FjRGTy")

    def test_playlist_with_query(self):
        out = SpotifyClient.parse_url(
            "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M?si=abc"
        )
        assert out == ("playlist", "37i9dQZF1DXcBWIGoYBM5M")

    def test_artist_with_intl_prefix(self):
        out = SpotifyClient.parse_url(
            "https://open.spotify.com/intl-es/artist/5JZ7CnR6gTvEMKX4g70Amv"
        )
        assert out == ("artist", "5JZ7CnR6gTvEMKX4g70Amv")

    def test_invalid(self):
        assert SpotifyClient.parse_url("https://example.com/foo") is None
