
from __future__ import annotations

import asyncio
import time
from typing import Optional, TYPE_CHECKING

import aiohttp
import async_timeout

from .exceptions import NodeConnectionClosed
from .objects import AndesiteStats, LavalinkStats, Metadata

if TYPE_CHECKING:
    from .client import Client

from .bases import BaseNode


class AndesiteNode(BaseNode):

    def __init__(self, *, client: Client, host: str, port: str, password: str, identifier: str, use_compatibility: bool = False) -> None:
        super().__init__(client=client, host=host, port=port, password=password, identifier=identifier)

        self._use_compatibility: bool = use_compatibility

        self._http_url: str = f'http://{self._host}:{self._port}/'
        self._ws_url: str = f'ws://{self._host}:{self._port}/{"websocket" if not self._use_compatibility else ""}'

        self._headers: dict = {
            'Authorization': self._password,
            'User-Id': str(self._client.bot.user.id),
            'Client-Name': 'Slate/0.1.0',

            'Andesite-Short-Errors': 'True'
        }

        self._connection_id: Optional[int] = None
        self._metadata: Optional[Metadata] = None

        self._andesite_stats: Optional[AndesiteStats] = None
        self._lavalink_stats: Optional[LavalinkStats] = None

        self._andesite_stats_event = asyncio.Event()
        self._pong_event = asyncio.Event()

    def __repr__(self) -> str:
        return f'<slate.AndesiteNode identifier=\'{self._identifier}\' player_count={len(self._players)} use_compatibility={self._use_compatibility}>'

    #

    @property
    def use_compatibility(self) -> bool:
        return self._use_compatibility

    #

    @property
    def connection_id(self) -> int:
        return self._connection_id

    @property
    def metadata(self) -> Optional[Metadata]:
        return self._metadata

    @property
    def andesite_stats(self) -> Optional[AndesiteStats]:
        return self._andesite_stats

    @property
    def lavalink_stats(self) -> Optional[LavalinkStats]:
        return self._lavalink_stats

    #

    async def _listen(self) -> None:

        while True:

            message = await self._websocket.receive()

            if message.type is aiohttp.WSMsgType.CLOSED:
                await self.disconnect()
                raise NodeConnectionClosed(f'Node \'{self.identifier}\' has closed. Reason: {message.extra}')

            message = message.json()

            op = message.get('op', None)
            if not op:
                continue  # TODO Log the fact that received a message with no 'op'.

            await self._handle_message(message=message)

    async def _handle_message(self, message: dict) -> None:

        op = message['op']

        if op == 'metadata':  # Andesite-mode only event.
            self._metadata = Metadata(data=message.get('data'))

        elif op == 'connection-id':  # Andesite-mode only event.
            self._connection_id = message.get('id')

        elif op == 'pong':  # Andesite-mode only event.
            self._pong_event.set()

        elif op in ['player-update', 'playerUpdate']:

            player = self.players.get(int(message.get('guildId')))
            if not player:
                return

            await player._update_state(state=message.get('state'))

        elif op == 'event':

            player = self.players.get(int(message.get('guildId')))
            if not player:
                return

            player._dispatch_event(data=message)

        elif op == 'stats':

            stats = message.get('stats', None)
            if stats:
                self._andesite_stats = AndesiteStats(data=stats)
                self._andesite_stats_event.set()
            else:
                self._lavalink_stats = LavalinkStats(data=message)

    async def _send(self, **data) -> None:

        if not self.is_connected:
            raise NodeConnectionClosed(f'Node \'{self.identifier}\' is not connected.')

        await self._websocket.send_json(data)

    #

    async def ping(self) -> float:

        start_time = time.time()
        await self._send(op='ping')

        async with async_timeout.timeout(timeout=30):
            await self._pong_event.wait()

        end_time = time.time()
        self._pong_event.clear()

        return end_time - start_time

    async def request_andesite_stats(self) -> AndesiteStats:

        await self._send(op='get-stats')

        async with async_timeout.timeout(timeout=30):
            await self._andesite_stats_event.wait()

        self._andesite_stats_event.clear()
        return self._andesite_stats

    #
