"""Per-guild playback queue with auto-recommend support."""
from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass, field


@dataclass
class QueueItem:
    """A pending play request. Keep it lazy: just a query string and metadata."""

    query: str
    display_title: str
    requested_by: str


@dataclass
class GuildQueue:
    items: deque[QueueItem] = field(default_factory=deque)
    autorecommend: bool = False
    last_played_video_id: str | None = None

    def push(self, item: QueueItem) -> None:
        self.items.append(item)

    def extend(self, new_items: list[QueueItem]) -> None:
        self.items.extend(new_items)

    def pop_next(self) -> QueueItem | None:
        return self.items.popleft() if self.items else None

    def clear(self) -> None:
        self.items.clear()

    def shuffle(self) -> None:
        data = list(self.items)
        random.shuffle(data)
        self.items = deque(data)

    def __len__(self) -> int:
        return len(self.items)

    def __bool__(self) -> bool:
        return bool(self.items)


class QueueManager:
    """Dict of guild_id -> GuildQueue, created on demand."""

    def __init__(self) -> None:
        self._queues: dict[int, GuildQueue] = {}

    def get(self, guild_id: int) -> GuildQueue:
        q = self._queues.get(guild_id)
        if q is None:
            q = GuildQueue()
            self._queues[guild_id] = q
        return q

    def drop(self, guild_id: int) -> None:
        self._queues.pop(guild_id, None)
