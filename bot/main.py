"""Entry point: builds the bot, loads the Music cog, starts the gateway."""
from __future__ import annotations

import asyncio
import logging
import sys

import discord
from discord.ext import commands
from dotenv import load_dotenv

from .cogs.music import setup as setup_music
from .config import load_config
from .spotify_client import SpotifyClient


def build_bot(spotify: SpotifyClient) -> commands.Bot:
    intents = discord.Intents.default()
    intents.message_content = False
    intents.voice_states = True

    bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

    @bot.event
    async def on_ready() -> None:
        logging.info("Logged in as %s (id=%s)", bot.user, getattr(bot.user, "id", "?"))
        try:
            synced = await bot.tree.sync()
            logging.info("Synced %d application commands", len(synced))
        except Exception:
            logging.exception("Failed to sync commands")

    async def _setup_hook() -> None:
        await setup_music(bot, spotify)

    bot.setup_hook = _setup_hook  # type: ignore[method-assign]
    return bot


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        stream=sys.stdout,
    )
    load_dotenv()
    cfg = load_config()
    spotify = SpotifyClient(cfg.spotify_client_id, cfg.spotify_client_secret)
    if spotify.enabled:
        logging.info("Spotify integration enabled")
    else:
        logging.info("Spotify integration disabled (no credentials)")

    bot = build_bot(spotify)
    try:
        asyncio.run(bot.start(cfg.discord_token))
    except KeyboardInterrupt:
        logging.info("Shutting down")


if __name__ == "__main__":
    main()
