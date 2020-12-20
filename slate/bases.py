
from __future__ import annotations

import asyncio
from typing import Dict, Optional, Protocol, TYPE_CHECKING

import aiohttp

from .exceptions import NodeConnectionError

if TYPE_CHECKING:
    from .client import Client
    from .player import Player


class BaseNode:

    def __init__(self, *, client: Client, host: str, port: str, password: str, identifier: str) -> None:

        self._client: Client = client
        self._host: str = host
        self._port: str = port
        self._password: str = password
        self._identifier: str = identifier

        self._headers: Optional[Dict[str]] = {}

        self._http_url: Optional[str] = None
        self._ws_url: Optional[str] = None

        self._players: Dict[int, Protocol[Player]] = {}

        self._websocket: Optional[aiohttp.ClientWebSocketResponse] = None
        self._task: Optional[asyncio.Task] = None

    def __repr__(self) -> str:
        return f'<slate.BaseNode identifier=\'{self._identifier}\' player_count={len(self._players)}>'

    #

    @property
    def client(self) -> Client:
        return self._client

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> str:
        return self._port

    @property
    def password(self) -> str:
        return self._password

    @property
    def identifier(self) -> str:
        return self._identifier

    #

    @property
    def http_url(self) -> str:
        return self._http_url

    @property
    def ws_url(self) -> str:
        return self._ws_url

    #

    @property
    def players(self) -> Dict[int, Protocol[Player]]:
        return self._players

    #

    @property
    def is_connected(self) -> bool:
        return self._websocket is not None and not self._websocket.closed

    #

    async def _listen(self) -> None:
        pass

    async def _handle_message(self, message: dict) -> None:
        pass

    async def _send(self, **data) -> None:
        pass

    #

    async def connect(self) -> None:

        await self.client.bot.wait_until_ready()

        try:
            websocket = await self.client.session.ws_connect(self.ws_url, headers=self._headers)

        except Exception as error:

            if isinstance(error, aiohttp.WSServerHandshakeError) and error.status == 4001:
                raise NodeConnectionError(f'Node \'{self.identifier}\' has invalid authorization.')

            raise NodeConnectionError(f'Node \'{self.identifier}\' was unable to connect. Reason: {error}')

        self._websocket = websocket
        self._client.nodes[self.identifier] = self

        self._task = asyncio.create_task(self._listen())

    async def disconnect(self) -> None:

        for player in self._players.copy().values():
            await player.destroy()

        if self.is_connected:
            await self._websocket.close()

        self._task.cancel()

    async def destroy(self) -> None:

        await self.disconnect()
        del self._client.nodes[self.identifier]
