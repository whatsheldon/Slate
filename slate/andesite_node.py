
from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional, TYPE_CHECKING

import aiohttp
import async_timeout

from .bases import BaseNode
from .exceptions import NodeConnectionClosed
from .objects import AndesiteStats, LavalinkStats, Metadata

if TYPE_CHECKING:
    from .client import Client

__log__ = logging.getLogger(__name__)


class AndesiteNode(BaseNode):
    """
    An implementation of :py:class:`BaseNode` that allows connection to :resource:`Andesite <andesite>` nodes with support for their :resource:`Lavalink <lavalink>`
    compatibility mode.

    Parameters
    ----------
    client: :py:class:`Client`
        The Slate Client that this Node is associated with.
    host: :py:class:`str`
        The host address of the external node that this Node should connect to.
    port: :py:class:`port`
        The port of the external node that this node should connect with.
    password: :py:class:`str`
        The password used for authentification with the external node.
    identifier: :py:class:`str`
        This Nodes unique identifier.
    use_compatibility: :py:class:`bool`
        Whether or not this node should use the :resource:`Lavalink <lavalink>` compatible websocket.`
    **kwargs
        Custom keyword arguments that have been passed to this Node from :py:meth:`Client.create_node`
    """

    def __init__(self, *, client: Client, host: str, port: str, password: str, identifier: str, use_compatibility: bool = False, **kwargs) -> None:
        super().__init__(client=client, host=host, port=port, password=password, identifier=identifier, **kwargs)

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
        """
        :py:class:`bool`:
            Whether or not this Node is using the :resource:`Lavalink <lavalink>` compatible websocket.
        """
        return self._use_compatibility

    #

    @property
    def connection_id(self) -> Optional[int]:
        """
        :py:class:`typing.Optional` [ :py:class:`int` ]:
            The connection id sent on connection with :resource:`Andesite <andesite>`. This could be :py:class:`None` if :py:attr:`AndesiteNode.use_compatibility` is
            :py:class:`True`.
        """
        return self._connection_id

    @property
    def metadata(self) -> Optional[Metadata]:
        """
        :py:class:`typing.Optional` [ :py:class:`Metadata` ]:
            Metadata sent from :resource:`Andesite <andesite>` that contains version information and node information. This could be :py:class:`None` if
            :py:attr:`AndesiteNode.use_compatibility` is :py:class:`True`.
        """
        return self._metadata

    @property
    def andesite_stats(self) -> Optional[AndesiteStats]:
        """
        :py:class:`typing.Optional` [ :py:class:`AndesiteStats` ]:
            Stats sent from :resource:`Andesite <andesite>` that contains information about the system and current status. These stats are sent from andesite upon using
            :py:meth:`AndesiteNode.request_andesite_stats`.
        """
        return self._andesite_stats

    @property
    def lavalink_stats(self) -> Optional[LavalinkStats]:
        """
        :py:class:`typing.Optional` [ :py:class:`LavalinkStats` ]:
            Stats sent from :resource:`Andesite <andesite>` when using the :resource:`Lavalink <lavalink>` compatible websocket. These stats are sent every 30ish seconds or so.
        """
        return self._lavalink_stats

    #

    async def _listen(self) -> None:

        while True:

            message = await self._websocket.receive()

            if message.type is aiohttp.WSMsgType.CLOSED:
                await self.disconnect()
                __log__.info(f'WEBSOCKET | Node \'{self.identifier}\'\'s websocket has been closed. | Reason: {message.extra}')
                raise NodeConnectionClosed(f'Node \'{self.identifier}\' websocket has been closed. Reason: {message.extra}')

            message = message.json()
            __log__.debug(f'WEBSOCKET | Node \'{self.identifier}\' received payload. | {message}')

            op = message.get('op', None)
            if not op:
                __log__.warning(f'WEBSOCKET | Node \'{self.identifier}\' received payload with no op code. | Payload: {message}')
                continue

            await self._handle_message(message=message)

    async def _handle_message(self, message: dict) -> None:

        op = message['op']
        __log__.debug(f'WEBSOCKET | Node \'{self.identifier}\' received payload with op \'{op}\'. | Payload: {message}')

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

        __log__.debug(f'WEBSOCKET | Node \'{self.identifier}\' sent a \'{data.get("op")}\' payload. | Payload: {data}')
        await self._websocket.send_json(data)

    #

    async def ping(self) -> float:
        """
        Returns the latency between this Node and its websocket in milliseconds. This works on both the lavalink compatible websocket and the normal websocket.

        Returns
        -------
        :py:class:`float`
            The latency in milliseconds.

        Raises
        ------
        :py:class:`asyncio.TimeoutError`
            Requesting the latency took over 30 seconds.
        """

        start_time = time.time()
        await self._send(op='ping')

        async with async_timeout.timeout(timeout=30):
            await self._pong_event.wait()

        end_time = time.time()
        self._pong_event.clear()

        return end_time - start_time

    async def request_andesite_stats(self) -> AndesiteStats:
        """
        Requests andesite stats from the node. This works on both the lavalink compatible websocket and the normal websocket.

        Returns
        -------
        :py:class:`AndesiteStats`
            The stats that were returned.

        Raises
        ------
        :py:class:`asyncio.TimeoutError`
            Requesting the stats took over 30 seconds.
        """

        await self._send(op='get-stats')

        async with async_timeout.timeout(timeout=30):
            await self._andesite_stats_event.wait()

        self._andesite_stats_event.clear()
        return self._andesite_stats
