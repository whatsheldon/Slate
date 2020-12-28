
from __future__ import annotations

import abc
import asyncio
import logging
import urllib.parse
from typing import Dict, List, Optional, Protocol, TYPE_CHECKING, Union

import aiohttp
from discord.ext import commands

from .objects import Track, Playlist
from .backoff import ExponentialBackoff
from .exceptions import NodeConnectionError, TrackLoadError, TrackLoadFailed, TrackDecodeError

if TYPE_CHECKING:
    from .client import Client
    from .player import Player


__log__ = logging.getLogger(__name__)


class BaseNode(abc.ABC):
    """
    The abstract base class for creating a Node with. Nodes connect to an external nodes websocket such as (:resource:`Andesite <andesite>` or :resource:`Lavalink <lavalink>`
    using custom logic defined in that Nodes subclass. All Nodes passed to :py:meth:`Client.create_node` must inherit from this class.

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
        """
        :py:class:`Client`:
            The slate Client that this Node is associated with.
        """
        return self._client

    @property
    def host(self) -> str:
        """
        :py:class:`str`:
            The host address of the external node that this Node should connect to.
        """
        return self._host

    @property
    def port(self) -> str:
        """
        :py:class:`str`:
            The port of the external node that this node should connect with.
        """
        return self._port

    @property
    def password(self) -> str:
        """
        :py:class:`str`:
            The password used for authentification with the external node.
        """
        return self._password

    @property
    def identifier(self) -> str:
        """
        :py:class:`str`:
            This Nodes unique identifier.
        """
        return self._identifier

    #

    @property
    def http_url(self) -> str:
        """
        :py:class:`str`:
            The url used to make http requests with the external node.
        """
        return self._http_url

    @property
    def ws_url(self) -> str:
        """
        :py:class:`str`:
            The url used for connecting to the external nodes websocket.
        """
        return self._ws_url

    @property
    def players(self) -> Dict[int, Protocol[Player]]:
        """
        :py:class:`typing.Mapping` [ :py:class:`int` , :py:class:`typing.Protocol` [ :py:class:`Player`] ]:
            A mapping of Player guild id's to Players that this Node is managing.
        """
        return self._players

    #

    @property
    def is_connected(self) -> bool:
        """
        :py:class:`bool`:
            Whether or not this Node is connected to it's external node's websocket.
        """
        return self._websocket is not None and not self._websocket.closed

    #

    @abc.abstractmethod
    async def _listen(self) -> None:
        pass

    @abc.abstractmethod
    async def _handle_message(self, message: dict) -> None:
        pass

    @abc.abstractmethod
    async def _send(self, **data) -> None:
        pass

    #

    async def connect(self) -> None:
        """Connects this Node to it's external websocket.

        Raises
        ------
        :py:class:`NodeConnectionError`:
            There was an error while connecting to the websocket, could be invalid authorization or an unreachable/invalid host address or port, etc.
        """

        await self.client.bot.wait_until_ready()

        try:
            websocket = await self.client.session.ws_connect(self.ws_url, headers=self._headers)

        except Exception as error:

            if isinstance(error, aiohttp.WSServerHandshakeError) and error.status == 4001:
                __log__.warning(f'NODE | Node \'{self.identifier}\' failed to connect due to invalid authorization.')
                raise NodeConnectionError(f'Node \'{self.identifier}\' has invalid authorization.')

            __log__.warning(f'NODE | Node \'{self.identifier}\' failed to connect. Error: {error}')
            raise NodeConnectionError(f'Node \'{self.identifier}\' was unable to connect. Reason: {error}')

        self._websocket = websocket
        self._client._nodes[self.identifier] = self

        self._task = asyncio.create_task(self._listen())
        __log__.info(f'NODE | Node with identifier \'{self.identifier}\' connected successfully.')

    async def disconnect(self) -> None:
        """Disconnects this Node from it's websocket and destroys all it's Players."""

        for player in self._players.copy().values():
            await player.destroy()

        if self.is_connected:
            await self._websocket.close()
        self._websocket = None

        self._task.cancel()
        self._task = None

        __log__.info(f'NODE | Node with identifier \'{self.identifier}\' has been disconnected.')

    async def destroy(self) -> None:
        """Calls :py:meth:`BaseNode.disconnect` and removes the Node from it's Client."""

        await self.disconnect()
        del self._client.nodes[self.identifier]

        __log__.info(f'NODE | Node with identifier \'{self.identifier}\' was destroyed.')

    #

    async def search(self, *, query: str, ctx: Protocol[commands.Context] = None, retry: bool = True, raw: bool = False) -> Optional[Union[Playlist, List[Track], Dict]]:
        """
        Searches for and returns a list of :py:class:`Track`'s or a :py:class:`Playlist`.

        Parameters
        ----------
        query: str
            The query to search with. Could be a link or a search term if prepended with "scsearch:" (Soundcloud) or "ytsearch:" (Youtube).
        ctx: :py:class:`typing.Protocol` [ :py:class:`commands.Context`]
            An optional context argument to pass to the track for quality of life features such as :py:attr:`Track.requester`.
        retry: :py:class:`typing.Optional` [ :py:class:`bool` ]
            Whether or not to retry the search if a non-200 status code is received. If :py:class:`True` the search will be retried upto 5 times, with an exponential backoff between each time.
        raw: :py:class:`typing.Optional` [ :py:class:`bool` ]
            Whether or not to return the raw json result of the search.

        Returns
        -------
        :py:class:`typing.Optional` [ :py:class:`typing.Union` [ :py:class:`Playlist` , :py:class:`List` [ :py:class:`Track` ] , :py:class:`dict` ] ]:
            The raw json result, list of Tracks, or Playlist that was found.

        Raises
        ------
        :py:class:`TrackLoadError`:
            The server sent a non-200 HTTP status code while loading tracks.
        :py:class:`TrackLoadFailed`:
            The server did not error, but there was some kind of other problem while loading tracks. Could be a restricted video, youtube ratelimit, etc.
        """

        backoff = ExponentialBackoff(base=1)

        for _ in range(5):

            params = {'identifier': urllib.parse.quote(query)}
            async with self.client.session.get(url=f'{self.http_url}/loadtracks', headers={'Authorization': self.password}, params=params) as response:

                if response.status != 200:
                    if retry:
                        time = backoff.delay()
                        __log__.warning(f'LOADTRACKS | Non-200 status code while loading tracks. Retrying in {time}s. | Status code: {response.status}')
                        await asyncio.sleep(backoff.delay())
                        continue
                    else:
                        __log__.error(f'LOADTRACKS | Non-200 status code error while loading tracks. Not retrying. | Status code: {response.status}')
                        raise TrackLoadError('Non-200 status code error while loading tracks.', data={'status_code': response.status})

                data = await response.json()

            if raw:
                return data

            load_type = data.pop('loadType')

            if load_type == 'NO_MATCHES':
                __log__.debug(f'LOADTRACKS | No matches found for query: {query}')
                return None

            elif load_type == 'LOAD_FAILED':
                __log__.warning(f'LOADTRACKS | Encountered a LOAD_FAILED while getting tracks for query: {query} | Data: {data}')
                raise TrackLoadFailed(data=data)

            elif load_type == 'PLAYLIST_LOADED':
                __log__.debug(f'LOADTRACKS | Playlist loaded for query: {query} | Name: {data.get("playlistInfo", {}).get("name", "UNKNOWN")}')
                return Playlist(playlist_info=data.get('playlistInfo'), tracks=data.get('tracks'), ctx=ctx)

            elif load_type in ['SEARCH_RESULT', 'TRACK_LOADED']:
                __log__.debug(f'LOADTRACKS | Tracks loaded for query: {query} | Amount: {len(data.get("tracks"))}')
                return [Track(track_id=track.get('track'), track_info=track.get('info'), ctx=ctx) for track in data.get('tracks')]

        __log__.error(f'LOADTRACKS | Non-200 status code error while loading tracks. All 5 retries used.| Status code: {response.status}')
        raise TrackLoadError('Non-200 status code error while loading tracks.', data={'status_code': response.status})

    async def decode_track(self, *, track_id: str, ctx: Protocol[commands.Context] = None, retry: bool = True, raw: bool = False) -> Optional[Union[Track, Dict]]:

        backoff = ExponentialBackoff(base=1)

        for _ in range(5):

            async with self.client.session.get(url=f'{self.http_url}/decodetrack', headers={'Authorization': self.password}, params={'track': track_id}) as response:

                if response.status != 200:

                    if retry:
                        time = backoff.delay()
                        __log__.warning(f'DECODETRACKS | Non-200 status code while decoding tracks. Retrying in {time}s. | Status code: {response.status}')
                        await asyncio.sleep(backoff.delay())
                        continue
                    else:
                        __log__.error(f'DECODETRACKS | Non-200 status code error while decoding tracks. Not retrying. | Status code: {response.status}')
                        raise TrackDecodeError('Non-200 status code error while decoding tracks.', data={'status_code': response.status})

                data = await response.json()

            if raw:
                return data

            return Track(track_id=track_id, track_info=data.get('info', None) or data, ctx=ctx)

        __log__.error(f'DECODETRACKS | Non-200 status code error while decoding tracks. All 5 retries used. | Status code: {response.status}')
        raise TrackDecodeError('Non-200 status code error while decoding tracks.', data={'status_code': response.status})


