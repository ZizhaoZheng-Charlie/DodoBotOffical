"""Config loading."""
import importlib

import pytest


def test_loads_discord_token(monkeypatch):
    monkeypatch.setenv("DISCORD_TOKEN", "abc123")
    for name in (
        "SPOTIFY_CLIENT_ID",
        "SPOTIFY_CLIENT_SECRET",
        "SPOTIFY_ID",
        "SPOTIFY_SECRET",
    ):
        monkeypatch.delenv(name, raising=False)
    import bot.config as c
    importlib.reload(c)
    cfg = c.load_config()
    assert cfg.discord_token == "abc123"
    assert cfg.spotify_enabled is False


def test_legacy_env_names(monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    monkeypatch.setenv("TOKEN", "legacy")
    monkeypatch.setenv("SPOTIFY_ID", "sid")
    monkeypatch.setenv("SPOTIFY_SECRET", "ssec")
    import bot.config as c
    importlib.reload(c)
    cfg = c.load_config()
    assert cfg.discord_token == "legacy"
    assert cfg.spotify_enabled is True


def test_missing_token_raises(monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    monkeypatch.delenv("TOKEN", raising=False)
    import bot.config as c
    importlib.reload(c)
    with pytest.raises(RuntimeError):
        c.load_config()
