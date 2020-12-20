
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

import aiohttp

from .bases import BaseNode
from .exceptions import NodeConnectionClosed
from .objects import LavalinkStats

if TYPE_CHECKING:
    from .client import Client


class LavalinkNode(BaseNode):

    def __init__(self, *, client: Client, host: str, port: str, password: str, identifier: str) -> None:
        super().__init__(client=client, host=host, port=port, password=password, identifier=identifier)

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

        await self._websocket.send_json(data)

    #
