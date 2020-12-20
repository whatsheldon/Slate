
from __future__ import annotations

import time
from abc import ABC
from typing import List, Optional, Protocol, TYPE_CHECKING

import discord
from discord import VoiceProtocol

if TYPE_CHECKING:
    from .bases import BaseNode
    from . import objects
    from . import filters


class Player(VoiceProtocol, ABC):

    def __init__(self, bot: Protocol[discord.Client], channel: discord.VoiceChannel) -> None:
        super().__init__(bot, channel)

        self.client: Protocol[discord.Client] = bot
        self.bot: Protocol[discord.Client] = bot

        self.channel: discord.VoiceChannel = channel
        self._guild: discord.Guild = channel.guild

        self._node: Optional[Protocol[BaseNode]] = None

        self._current: Optional[objects.Track] = None
        self._filter: Optional[filters.Filter] = None
        self._volume: int = 100
        self._paused: bool = False

        self._last_position: int = 0
        self._last_update: int = 0
        self._last_time: int = 0

        self._voice_state: dict = {}

    def __repr__(self) -> str:
        return f'<slate.Player node={self.node} guild={self.guild} channel={self.channel} is_connected={self.is_connected} is_playing={self.is_playing}>'

    #

    @property
    def guild(self) -> discord.Guild:
        return self._guild

    @property
    def node(self) -> Protocol[BaseNode]:
        return self._node

    @property
    def current(self) -> Optional[objects.Track]:
        return self._current

    @property
    def filter(self) -> Optional[filters.Filter]:
        return self._filter

    @property
    def volume(self) -> int:
        return self._volume

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def is_connected(self) -> bool:
        return self._channel is not None

    @property
    def is_playing(self) -> bool:
        return self.is_connected and self._current is not None

    @property
    def position(self) -> float:

        if not self.is_playing or not self.current:
            return 0

        if self._paused:
            return min(self._last_position, self.current.length)

        position = self._last_position + ((time.time() * 1000) - self._last_update)

        if position > self.current.length:
            return 0

        return min(position, self.current.length)

    @property
    def listeners(self) -> List[discord.Member]:
        return [member for member in self.channel.members if not member.bot and not member.voice.deaf or not member.voice.self_deaf]

    #

    async def on_voice_server_update(self, data: dict) -> None:

        self._voice_state.update({'event': data})
        await self._dispatch_voice_update()

    async def on_voice_state_update(self, data: dict) -> None:

        self._voice_state.update({'sessionId': data.get('session_id')})

        channel_id = data.get('channel_id')
        if not channel_id:
            self._channel = None
            self._voice_state.clear()
            return

        self._channel = self.guild.get_channel(int(channel_id))
        await self._dispatch_voice_update()

    async def _dispatch_voice_update(self) -> None:

        if {'sessionId', 'event'} == self._voice_state.keys():
            op = 'voice-server-update' if self.node.andesite and not self.node.lavalink_compatibility else 'voiceUpdate'
            await self.node._send(op=op, guildId=str(self.guild.id), **self._voice_state)

    async def _update_state(self, *, state: dict) -> None:

        self._last_time = state.get('time', 0)
        self._last_position = state.get('position', 0)
        self._last_update = time.time() * 1000

        if self.node.andesite and not self.node.lavalink_compatibility:
            self._paused = state.get('paused', False)
            self._volume = state.get('volume', 100)

            # TODO Parse the filter shit please
            # self._filter = state.get('filters', Filter())

    def _dispatch_event(self, *, data: dict) -> None:

        event = getattr(objects, data.pop('type'), None)
        if not event:
            return  # TODO Log the fact that we have an unknown event here.

        event = event(data=data)
        self.bot.dispatch(f'slate_{str(event)}', event)

    #

    async def connect(self, *, timeout: float, reconnect: bool) -> None:
        await self.guild.change_voice_state(channel=self.channel, self_deaf=True)

    async def disconnect(self, *, force: bool = True) -> None:

        if not force and not self.is_connected:
            return

        await self.guild.change_voice_state(channel=None)
        self.channel = None

    async def stop(self) -> None:

        await self.node._send(op='stop', guildId=str(self.guild.id))
        self._current = None

    async def destroy(self) -> None:

        await self.disconnect()

        if self.node.is_connected:
            await self.stop()
            await self.node._send(op='destroy', guildId=str(self.guild.id))

        await self.cleanup()
        del self.node.players[self.guild.id]

    async def play(self, *, track: objects.Track, start: int = 0, end: int = 0, no_replace: bool = False, pause: bool = False) -> None:

        self._last_position = 0
        self._last_time = 0
        self._last_update = 0

        payload = {
            'op': 'play',
            'guildId': str(self.guild.id),
            'track': str(track.track_id),
        }
        if 0 < start < track.length:
            payload['startTime'] = start
        if 0 < end < track.length:
            payload['endTime'] = end
        if no_replace:
            payload['noReplace'] = no_replace
        if pause:
            payload['pause'] = pause

        await self.node._send(**payload)
        self._current = track

    async def set_filter(self, *, filter: filters.Filter) -> None:

        await self.node.send(op='filters', guildId=str(self.guild.id), **filter.payload)
        self._filter = filter

    async def set_volume(self, *, volume: int) -> None:

        await self.node.send(op='volume', guildId=str(self.guild.id), volume=volume)
        self._volume = volume

    async def set_pause(self, *, pause: bool) -> None:

        await self.node.send(op='pause', guildId=str(self.guild.id), pause=pause)
        self._paused = pause

    async def set_position(self, *, position: int) -> None:

        if not self.current:
            return

        if 0 > position > self.current.length:
            return

        await self.node.send(op='seek', guildId=str(self.guild.id), position=position)
