"""Unit tests for player helpers (video id extraction)."""
from bot.player import extract_video_id


class TestExtractVideoId:
    def test_watch(self):
        assert (
            extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
            == "dQw4w9WgXcQ"
        )

    def test_short_domain(self):
        assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_shorts(self):
        assert extract_video_id("https://www.youtube.com/shorts/jeCvbd7gejE") == "jeCvbd7gejE"

    def test_none_on_non_youtube(self):
        assert extract_video_id("https://open.spotify.com/track/abc") is None
