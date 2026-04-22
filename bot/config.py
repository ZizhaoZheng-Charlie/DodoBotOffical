"""Runtime configuration loaded from environment variables / .env."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    discord_token: str
    spotify_client_id: str | None
    spotify_client_secret: str | None
    command_prefix: str = "!"
    max_search_results: int = 5
    inactivity_timeout_seconds: int = 300

    @property
    def spotify_enabled(self) -> bool:
        return bool(self.spotify_client_id and self.spotify_client_secret)


def load_config() -> Config:
    token = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")
    if not token:
        raise RuntimeError(
            "DISCORD_TOKEN is not set. Add it to your .env file or export it."
        )

    return Config(
        discord_token=token,
        spotify_client_id=os.getenv("SPOTIFY_CLIENT_ID") or os.getenv("SPOTIFY_ID"),
        spotify_client_secret=os.getenv("SPOTIFY_CLIENT_SECRET")
        or os.getenv("SPOTIFY_SECRET"),
    )
