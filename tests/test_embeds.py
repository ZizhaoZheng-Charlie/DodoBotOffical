"""Verify embed builders produce valid discord.Embed objects."""
import discord

from bot.audio import SearchResult, Track
from bot.embeds import (
    added_to_queue_embed,
    error_embed,
    info_embed,
    now_playing_embed,
    picker_embed,
    queue_embed,
)
from bot.queue import GuildQueue, QueueItem


def _track(**over):
    base = dict(
        title="Test Song",
        url="https://stream.example/a",
        webpage_url="https://www.youtube.com/watch?v=abc",
        duration=253,
        thumbnail="https://img.example/t.jpg",
        uploader="Test Artist",
        requested_by="tester",
    )
    base.update(over)
    return Track(**base)


def test_now_playing_has_title_and_thumbnail():
    q = GuildQueue()
    emb = now_playing_embed(_track(), q)
    assert isinstance(emb, discord.Embed)
    assert emb.title == "Test Song"
    assert emb.thumbnail.url == "https://img.example/t.jpg"


def test_now_playing_duration_formatting():
    q = GuildQueue()
    emb = now_playing_embed(_track(duration=4 * 60 + 13), q)
    field_names = [f.name for f in emb.fields]
    durations = [f.value for f in emb.fields if f.name == "Duration"]
    assert "Duration" in field_names
    assert durations == ["4:13"]


def test_now_playing_autorecommend_visible():
    q = GuildQueue()
    q.autorecommend = True
    emb = now_playing_embed(_track(), q)
    up_next = [f.value for f in emb.fields if f.name == "Up next"]
    assert up_next and "auto-recommend ON" in up_next[0]


def test_added_to_queue():
    emb = added_to_queue_embed(_track(), position=3)
    assert "Test Song" in emb.title
    assert any(f.value == "#3" for f in emb.fields)


def test_picker_embed_lists_results():
    results = [
        SearchResult(title=f"Song {i}", webpage_url=f"u{i}", duration=120, uploader="U")
        for i in range(5)
    ]
    emb = picker_embed("query", results)
    assert len(emb.fields) == 5
    assert emb.fields[0].name.startswith("1. Song 0")


def test_queue_embed_empty():
    emb = queue_embed(GuildQueue())
    assert emb.title == "Queue is empty"


def test_queue_embed_with_items():
    q = GuildQueue()
    q.extend(
        [
            QueueItem(query=f"q{i}", display_title=f"Song {i}", requested_by="u")
            for i in range(3)
        ]
    )
    emb = queue_embed(q)
    assert "Song 0" in emb.description
    assert "Song 2" in emb.description


def test_queue_embed_truncates_past_15():
    q = GuildQueue()
    q.extend(
        [
            QueueItem(query=f"q{i}", display_title=f"Song {i}", requested_by="u")
            for i in range(25)
        ]
    )
    emb = queue_embed(q)
    assert "10 more" in emb.description


def test_error_and_info_embeds():
    assert error_embed("boom").title == "Error"
    assert info_embed("hi", "there").title == "hi"
