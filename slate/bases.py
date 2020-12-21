
from __future__ import annotations

import asyncio
import logging
import urllib.parse
from typing import Dict, List, Optional, Protocol, TYPE_CHECKING, Union

import aiohttp

from . import objects
from .backoff import ExponentialBackoff
from .exceptions import NodeConnectionError, TrackLoadError, TrackLoadFailed

if TYPE_CHECKING:
    from .client import Client
    from .player import Player

__log__ = logging.getLogger(__name__)


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
                __log__.warning(f'Node \'{self.identifier}\' failed to connect due to invalid authorization.')
                raise NodeConnectionError(f'Node \'{self.identifier}\' has invalid authorization.')

            __log__.warning(f'Node \'{self.identifier}\' failed to connect. Error: {error}')
            raise NodeConnectionError(f'Node \'{self.identifier}\' was unable to connect. Reason: {error}')

        self._websocket = websocket
        self._client.nodes[self.identifier] = self

        self._task = asyncio.create_task(self._listen())
        __log__.info(f'Node with identifier \'{self.identifier}\' connected successfully.')

    async def disconnect(self) -> None:

        for player in self._players.copy().values():
            await player.destroy()

        if self.is_connected:
            await self._websocket.close()

        self._task.cancel()

        self._task = None
        self._websocket = None

        __log__.info(f'Node with identifier \'{self.identifier}\' has been disconnected.')

    async def destroy(self) -> None:

        await self.disconnect()
        del self._client.nodes[self.identifier]

        __log__.info(f'Node with identifier \'{self.identifier}\' was destroyed.')

    #

    async def search(self, *, query: str, raw: bool = False, retry: bool = True) -> Union[Optional[objects.Playlist], Optional[List[objects.Track]]]:

        backoff = ExponentialBackoff(base=1)

        for _ in range(5):

            async with self.client.session.get(url=f'{self.http_url}/loadtracks?identifier={urllib.parse.quote(query)}', headers={'Authorization': self.password}) as response:

                if response.status != 200:
                    if retry:
                        time = backoff.delay()
                        __log__.warning(f'LOADTRACKS | Non-200 status code while loading tracks. Retrying in {time}s. Status code: {response.status}')
                        await asyncio.sleep(backoff.delay())
                        continue
                    else:
                        __log__.error(f'LOADTRACKS | Non-200 status code error while loading tracks. Status code: {response.status}')
                        raise TrackLoadError('Error while loading tracks.', data={'status_code': response.status})

                data = await response.json()

            if raw:
                return data

            load_type = data.pop('loadType')

            if load_type == 'NO_MATCHES':
                __log__.debug(f'LOADTRACKS | No matches found for load_tracks. Query: {query}')
                return None

            elif load_type == 'LOAD_FAILED':
                __log__.warning(f'LOADTRACKS | LOAD_FAILED Error. Data: {data}')
                raise TrackLoadFailed(data=data)

            elif load_type == 'PLAYLIST_LOADED':
                __log__.debug(f'LOADTRACKS | Playlist loaded. Name: {data.get("playlistInfo", {}).get("name")}')
                return objects.Playlist(playlist_info=data.get('playlistInfo'), tracks=data.get('tracks'))

            elif load_type in ['SEARCH_RESULT', 'TRACK_LOADED']:
                __log__.debug(f'LOADTRACKS | Tracks loaded. Amount: {len(data.get("tracks"))}')
                return [objects.Track(track_id=track.get('track'), track_info=track.get('info')) for track in data.get('tracks')]
