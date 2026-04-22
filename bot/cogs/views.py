"""discord.ui components: multi-result picker dropdown + playback control panel."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord

from ..audio import SearchResult
from ..embeds import added_to_queue_embed, error_embed, info_embed
from ..queue import QueueItem

if TYPE_CHECKING:
    from ..player import GuildPlayer

log = logging.getLogger(__name__)


class SongPickerView(discord.ui.View):
    """Shown when /play produces multiple results."""

    def __init__(
        self,
        results: list[SearchResult],
        *,
        player: GuildPlayer,
        requester: discord.abc.User,
        channel: discord.abc.Messageable,
        timeout: float = 60.0,
    ) -> None:
        super().__init__(timeout=timeout)
        self.results = results
        self.player = player
        self.requester = requester
        self.channel = channel
        self.message: discord.Message | None = None
        self.add_item(SongPickerSelect(results))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.requester.id:
            await interaction.response.send_message(
                "Only the requester can pick.", ephemeral=True
            )
            return False
        return True

    async def on_timeout(self) -> None:
        if self.message:
            try:
                await self.message.edit(
                    embed=info_embed("Selection expired"), view=None
                )
            except discord.HTTPException:
                pass


class SongPickerSelect(discord.ui.Select):
    def __init__(self, results: list[SearchResult]) -> None:
        options = []
        for i, r in enumerate(results[:25]):
            desc_parts = []
            if r.uploader:
                desc_parts.append(r.uploader)
            if r.duration:
                m, s = divmod(int(r.duration), 60)
                desc_parts.append(f"{m}:{s:02d}")
            options.append(
                discord.SelectOption(
                    label=r.title[:100] or f"Track {i + 1}",
                    description=" - ".join(desc_parts)[:100] or None,
                    value=str(i),
                )
            )
        super().__init__(
            placeholder="Pick the right track...",
            options=options,
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        view: SongPickerView = self.view  # type: ignore[assignment]
        idx = int(self.values[0])
        chosen = view.results[idx]

        from ..audio import resolve_track  # local to avoid cycle

        try:
            track = await resolve_track(
                chosen.webpage_url, requested_by=view.requester.display_name
            )
        except Exception as exc:
            log.exception("resolve_track failed")
            await interaction.response.edit_message(
                embed=error_embed(f"Couldn't load that track: {exc}"), view=None
            )
            return

        view.player.queue.push(
            QueueItem(
                query=track.webpage_url,
                display_title=track.title,
                requested_by=view.requester.display_name,
            )
        )
        await interaction.response.edit_message(
            embed=added_to_queue_embed(track, position=len(view.player.queue)),
            view=None,
        )

        view.player.start(view.channel)
        view.stop()


class ControlPanelView(discord.ui.View):
    """Persistent-ish control panel attached to every now-playing message."""

    def __init__(self, player: GuildPlayer) -> None:
        super().__init__(timeout=None)
        self.player = player

    async def _ensure_in_voice(self, interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            return False
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "Join a voice channel first.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Pause", style=discord.ButtonStyle.primary, emoji="\u23F8")
    async def pause(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await self._ensure_in_voice(interaction):
            return
        state = await self.player.pause_toggle()
        button.label = "Resume" if state == "paused" else "Pause"
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary, emoji="\u23ED")
    async def skip(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await self._ensure_in_voice(interaction):
            return
        await self.player.skip()
        await interaction.response.defer()

    @discord.ui.button(label="Shuffle", style=discord.ButtonStyle.secondary, emoji="\U0001F500")
    async def shuffle(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await self._ensure_in_voice(interaction):
            return
        await self.player.shuffle()
        await interaction.response.send_message("Shuffled.", ephemeral=True)

    @discord.ui.button(label="Auto-recommend", style=discord.ButtonStyle.success, emoji="\U0001F525")
    async def autorec(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await self._ensure_in_voice(interaction):
            return
        now_on = await self.player.toggle_autorecommend()
        button.style = (
            discord.ButtonStyle.success if now_on else discord.ButtonStyle.secondary
        )
        button.label = f"Auto-recommend: {'ON' if now_on else 'OFF'}"
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.success, emoji="\U0001F504")
    async def refresh(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.player.refresh_panel(interaction)

    @discord.ui.button(label="Disconnect", style=discord.ButtonStyle.danger, emoji="\u270B")
    async def disconnect(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await self._ensure_in_voice(interaction):
            return
        await self.player.disconnect()
        await interaction.response.edit_message(
            embed=info_embed("Disconnected"), view=None
        )
