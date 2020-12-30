
from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING

import aiohttp

from .bases import BaseNode
from .exceptions import NodeConnectionClosed
from .objects import LavalinkStats

if TYPE_CHECKING:
    from .client import Client

__log__ = logging.getLogger(__name__)


class LavalinkNode(BaseNode):
    """
    An implementation of :py:class:`BaseNode` that allows connection to :resource:`Lavalink <lavalink>` nodes.

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
    **kwargs
        Custom keyword arguments that have been passed to this Node from :py:meth:`Client.create_node`
    """

    def __init__(self, *, client: Client, host: str, port: str, password: str, identifier: str, **kwargs) -> None:
        super().__init__(client=client, host=host, port=port, password=password, identifier=identifier, **kwargs)

        self._http_url: str = f'http://{self._host}:{self._port}/'
        self._ws_url: str = f'ws://{self._host}:{self._port}/'

        self._headers: dict = {
            'Authorization': self._password,
            'User-Id': str(self._client.bot.user.id),
            'Client-Name': 'Slate/0.1.0',
        }

        self._lavalink_stats: Optional[LavalinkStats] = None

    def __repr__(self) -> str:
        return f'<slate.LavalinkNode identifier=\'{self._identifier}\' player_count={len(self._players)}>'

    #

    @property
    def lavalink_stats(self) -> Optional[LavalinkStats]:
        """
        :py:class:`typing.Optional` [ :py:class:`LavalinkStats` ]:
            Stats sent from :resource:`Lavalink <lavalink>`. These stats are sent every 30ish seconds or so.
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

            op = message.get('op', None)
            if not op:
                __log__.warning(f'WEBSOCKET | Node \'{self.identifier}\' received payload with no op code. | Payload: {message}')
                continue

            __log__.debug(f'WEBSOCKET | Node \'{self.identifier}\' received payload with op \'{op}\'. | Payload: {message}')
            await self._handle_message(message=message)

    async def _handle_message(self, message: dict) -> None:

        op = message['op']

        if op == 'playerUpdate':

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
            self._lavalink_stats = LavalinkStats(data=message)

    async def _send(self, **data) -> None:

        if not self.is_connected:
            raise NodeConnectionClosed(f'Node \'{self.identifier}\' is not connected.')

        __log__.debug(f'WEBSOCKET | Node \'{self.identifier}\' sent a \'{data.get("op")}\' payload. | Payload: {data}')
        await self._websocket.send_json(data)

    #
