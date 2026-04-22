"""Unit tests for the playback queue."""
from bot.queue import GuildQueue, QueueItem, QueueManager


def _item(q: str) -> QueueItem:
    return QueueItem(query=q, display_title=q, requested_by="tester")


class TestGuildQueue:
    def test_starts_empty(self):
        q = GuildQueue()
        assert len(q) == 0
        assert not q
        assert q.autorecommend is False

    def test_push_and_pop(self):
        q = GuildQueue()
        q.push(_item("a"))
        q.push(_item("b"))
        assert len(q) == 2
        assert q.pop_next().query == "a"
        assert q.pop_next().query == "b"
        assert q.pop_next() is None

    def test_extend(self):
        q = GuildQueue()
        q.extend([_item("a"), _item("b"), _item("c")])
        assert len(q) == 3

    def test_clear(self):
        q = GuildQueue()
        q.extend([_item("a"), _item("b")])
        q.clear()
        assert len(q) == 0

    def test_shuffle_preserves_contents(self):
        q = GuildQueue()
        songs = [_item(x) for x in "abcdefghij"]
        q.extend(songs)
        q.shuffle()
        assert sorted(i.query for i in q.items) == list("abcdefghij")

    def test_autorecommend_toggle(self):
        q = GuildQueue()
        q.autorecommend = True
        assert q.autorecommend


class TestQueueManager:
    def test_creates_queue_on_demand(self):
        m = QueueManager()
        q = m.get(123)
        assert isinstance(q, GuildQueue)
        assert m.get(123) is q

    def test_drop(self):
        m = QueueManager()
        q = m.get(1)
        q.push(_item("x"))
        m.drop(1)
        assert m.get(1) is not q
