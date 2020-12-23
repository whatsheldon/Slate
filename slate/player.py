
from __future__ import annotations

import logging
import time
from abc import ABC
from typing import List, Optional, Protocol

import discord
from discord import VoiceProtocol

from . import filters, objects
from .andesite_node import AndesiteNode
from .bases import BaseNode

__log__ = logging.getLogger(__name__)


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
        return f'<slate.Player node={self.node!r} guild={self.guild!r} channel={self.channel!r} is_connected={self.is_connected} is_playing={self.is_playing}>'

    #

    @property
    def guild(self) -> discord.Guild:
        """:py:class:`discord.Guild`: The guild that this :py:class:`Player` is connected to."""
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
        return self.channel is not None

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

        __log__.debug(f'PLAYER | Received VOICE_SERVER_UPDATE from discord. | Data: {data}')

        self._voice_state.update({'event': data})
        await self._dispatch_voice_update()

    async def on_voice_state_update(self, data: dict) -> None:

        __log__.debug(f'PLAYER | Received VOICE_STATE_UPDATE from discord. | Data: {data}')

        self._voice_state.update({'sessionId': data.get('session_id')})

        channel_id = data.get('channel_id')
        if not channel_id:
            self.channel = None
            self._voice_state.clear()
            return

        self.channel = self.guild.get_channel(int(channel_id))
        await self._dispatch_voice_update()

    async def _dispatch_voice_update(self) -> None:

        if {'sessionId', 'event'} == self._voice_state.keys():
            op = 'voice-server-update' if isinstance(self.node, AndesiteNode) else 'voiceUpdate'
            await self.node._send(op=op, guildId=str(self.guild.id), **self._voice_state)

    async def _update_state(self, *, state: dict) -> None:

        __log__.debug(f'PLAYER | Updating player state. | State: {state}')

        self._last_time = state.get('time', 0)
        self._last_position = state.get('position', 0)
        self._last_update = time.time() * 1000

        if isinstance(self.node, AndesiteNode):
            self._paused = state.get('paused', False)
            self._volume = state.get('volume', 100)

            # TODO Parse the filter shit please
            # self._filter = state.get('filters', Filter())

    def _dispatch_event(self, *, data: dict) -> None:

        event = getattr(objects, data.get('type'), None)
        if not event:
            __log__.warning(f'PLAYER | Unknown event type received. | Data: {data} ')
            return

        __log__.info(f'PLAYER | Dispatching {data.get("type")} event. | Data: {data}')

        data['player'] = self
        event = event(data=data)

        self.bot.dispatch(f'slate_{str(event)}', event)

    #

    async def connect(self, *, timeout: float, reconnect: bool) -> None:

        await self.guild.change_voice_state(channel=self.channel, self_deaf=True)
        __log__.info(f'PLAYER | Player for guild {self.guild!r} joined channel {self.channel!r}.')

    async def disconnect(self, *, force: bool = True) -> None:

        if not force and not self.is_connected:
            return

        await self.guild.change_voice_state(channel=None)
        __log__.info(f'PLAYER | Player for guild {self.guild!r} disconnected from voice channel {self.channel!r}.')

        self.cleanup()
        self.channel = None

    async def stop(self, force: bool = True) -> None:

        if not force and not self.current:
            return

        await self.node._send(op='stop', guildId=str(self.guild.id))
        self._current = None
        __log__.info(f'PLAYER | Player for guild {self.guild!r} ended the current track.')

    async def destroy(self) -> None:

        await self.disconnect()

        if self.node.is_connected:
            await self.stop()
            await self.node._send(op='destroy', guildId=str(self.guild.id))

        __log__.info(f'PLAYER | Player for guild {self.guild!r} was destroyed.')
        del self.node.players[self.guild.id]

    async def play(self, *, track: objects.Track, start: int = 0, end: int = 0, volume: int = None, no_replace: bool = False, pause: bool = False) -> None:

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
        if volume:
            payload['volume'] = volume
        if no_replace:
            payload['noReplace'] = no_replace
        if pause:
            payload['pause'] = pause

        await self.node._send(**payload)
        self._current = track

        __log__.info(f'PLAYER | Player for guild {self.guild!r} is playing the track {self._current!r}.')

    async def set_filter(self, *, filter: filters.Filter) -> None:

        await self.node._send(op='filters', guildId=str(self.guild.id), **filter.payload)
        self._filter = filter

        __log__.info(f'PLAYER | Player for guild {self.guild!r} is using the filter {self._filter!r}')

    async def set_volume(self, *, volume: int) -> None:

        await self.node._send(op='volume', guildId=str(self.guild.id), volume=volume)
        self._volume = volume

        __log__.info(f'PLAYER | Player for guild {self.guild!r} has set its volume to {self._volume}.')

    async def set_pause(self, *, pause: bool) -> None:

        await self.node._send(op='pause', guildId=str(self.guild.id), pause=pause)
        self._paused = pause

        __log__.info(f'PLAYER | Player for guild {self.guild!r} has set its paused status to {self._paused}.')

    async def set_position(self, *, position: int) -> None:

        if not self.current:
            return

        if 0 > position > self.current.length:
            return

        await self.node._send(op='seek', guildId=str(self.guild.id), position=position)
        __log__.info(f'PLAYER | Player for guild {self.guild!r} has set its position to {self.position}.')
