
from __future__ import annotations

import asyncio
import time
from typing import Dict, Optional, TYPE_CHECKING
from urllib import parse

import aiohttp

from .exceptions import NodeConnectionError, NodeCreationError
from .objects import Metadata, Pong, Stats

if TYPE_CHECKING:
    from .client import Client
    from .player import Player


class Node:

    def __init__(self, *, client: Client, host: str, port: str, password: str, identifier: str, andesite: bool = False, lavalink_compatibility: bool = True) -> None:

        self._client = client
        self._host = host
        self._port = port
        self._password = password
        self._identifier = identifier
        self._andesite = andesite
        self._lavalink_compatibility = lavalink_compatibility

        self._connection_id: Optional[int] = None
        self._metadata: Optional[Metadata] = None

        self._stats: Optional[Stats] = None
        self._players: Dict[int, Player] = {}

        self.rest_url: str = f'https://{self.host}:{self.port}/'
        self.ws_url: str = f'ws://{self.host}:{self.port}/{"websocket" if self.lavalink_compatibility else ""}'

        self.headers: dict = {
            'Authorization': self.password,
            'User-Id': str(self.client.bot.user.id),
            'Client-Name': 'Slate/0.1.0'
        }

        if self._andesite:
            self.headers['Andesite-Resume-Id'] = self._connection_id,
            self.headers['Andesite-Short-Errors'] = True

        self._websocket: Optional[aiohttp.ClientWebSocketResponse] = None
        self._task: Optional[asyncio.Task] = None

    def __repr__(self) -> str:
        return f'<slate.Node identifier=\'{self._identifier}\' player_count={len(self._players)}>'

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

    @property
    def andesite(self) -> bool:
        return self._andesite

    @property
    def lavalink_compatibility(self) -> bool:
        return self.andesite and self._lavalink_compatibility

    @property
    def connection_id(self) -> int:
        return self._connection_id

    @property
    def metadata(self) -> Optional[Metadata]:
        return self._metadata

    @property
    def stats(self) -> Optional[Stats]:
        return self._stats

    @property
    def players(self) -> Dict[int, Player]:
        return self._players

    #

    @property
    def is_connected(self) -> bool:
        return self._websocket is not None and not self._websocket.closed

    #

    async def _listen(self) -> None:

        while True:

            message = await self._websocket.receive()

            if message.type is aiohttp.WSMsgType.CLOSED:
                await self.disconnect()
                raise NodeConnectionError(f'Node \'{self.identifier}\' has closed. Reason: {message.extra}')

            else:

                message = message.json()

                op = message.get('op', None)
                if not op:
                    continue

                if op == 'connection-id':  # Andesite specific event.
                    self._connection_id = message.get('id')

                elif op == 'pong':  # Andesite specific event.
                    self.client.bot.dispatch('slate_node_pong', Pong(node=self, time=time.time()))

                elif op == 'metadata':  # Andesite specific event.
                    self._metadata = Metadata(data=message.get('data'))

                #

                elif op in ['playerUpdate', 'player-update']:  # Lavalink and Andesite event.

                    player = self.players.get(int(message.get('guildId')))
                    if not player:
                        return

                    await player.update_state(state=message.get('state'))

                elif op == 'event':  # Lavalink and Andesite event.

                    player = self.players.get(int(message.get('guildId')))
                    if not player:
                        return

                    message['player'] = player
                    player.dispatch_event(data=message)

                elif op == 'stats':  # Lavalink and Andesite event.
                    self._stats = Stats(data=message.get('stats'))

                else:
                    pass  # TODO Log warning here, maybe raise exception idk.

    async def _send(self, **data: dict) -> None:

        if not self.is_connected:
            raise NodeConnectionError(f'Node \'{self.identifier}\' is not connected.')

        await self._websocket.send_json(data)

    #

    async def connect(self) -> None:

        await self.client.bot.wait_until_ready()

        try:
            websocket = await self.client.session.ws_connect(self.ws_url, headers=self.headers)

        except Exception as error:

            if isinstance(error, aiohttp.WSServerHandshakeError):
                if error.status == 401:
                    raise NodeCreationError(f'Node \'{self.identifier}\' has invalid authorization.')
            else:
                raise NodeCreationError(f'Node \'{self.identifier}\' was unable to connect. Reason: {error}')

        else:

            self._websocket = websocket
            self.client.nodes[self.identifier] = self

            self._task = asyncio.create_task(self._listen())

    async def disconnect(self) -> None:

        for player in self.players.copy().values():
            await player.destroy()

        if self.is_connected:
            await self._websocket.close()

        self._task.cancel()

    async def destroy(self) -> None:

        await self.disconnect()
        del self.client.nodes[self.identifier]

    #

    async def decode_track(self, *, track_id: str, ctx: context.Context = None) -> objects.Track:

        async with self.client.session.get(f'{self.rest_url}/decodetrack?', headers={'Authorization': self.password}, params={'track': track_id}) as response:
            data = await response.json()

            if response.status != 200:
                raise exceptions.VoiceError('Track id was not valid.')

        return objects.Track(track_id=track_id, info=data, ctx=ctx)

    async def search(self, *, query: str, raw: bool = False, ctx: context.Context = None) -> objects.Search:

        spotify_check = self.spotify_url_regex.match(query)
        if spotify_check is not None:

            spotify_type, spotify_id = spotify_check.groups()
            return await self.spotify_search(query=query, spotify_type=spotify_type, spotify_id=spotify_id, ctx=ctx)

        url_check = yarl.URL(query)
        if url_check.scheme is not None and url_check.host is not None:
            return await self.lavalink_search(query=query, ctx=ctx, raw=raw)

        if query.startswith('soundcloud'):
            return await self.lavalink_search(query=f'scsearch:{query[11:]}', ctx=ctx, raw=raw)

        return await self.lavalink_search(query=f'ytsearch:{query}', ctx=ctx, raw=raw)

    async def lavalink_search(self, *, query: str, raw: bool = False, ctx: context.Context = None) -> objects.Search:

        async with self.client.session.get(url=f'{self.rest_url}/loadtracks?identifier={parse.quote(query)}', headers={'Authorization': self.password}) as response:
            data = await response.json()

        if raw:
            return data

        load_type = data.pop('loadType')

        if load_type == 'LOAD_FAILED':
            exception = data.get("exception")
            raise exceptions.VoiceError(f'There was an error of severity `{exception.get("severity")}` while loading tracks. Reason: `{exception.get("message")}`')

        elif load_type == 'NO_MATCHES':
            raise exceptions.VoiceError(f'The query `{query}` returned no tracks.')

        elif load_type == 'PLAYLIST_LOADED':
            playlist = objects.Playlist(playlist_info=data.get('playlistInfo'), raw_tracks=data.get('tracks'), ctx=ctx)
            return objects.Search(source=playlist.tracks[0].source, source_type='playlist', tracks=playlist.tracks, result=playlist)

        elif load_type in ['SEARCH_RESULT', 'TRACK_LOADED']:

            raw_tracks = data.get('tracks')
            if not raw_tracks:
                raise exceptions.VoiceError(f'The query `{query}` returned no tracks.')

            tracks = [objects.Track(track_id=track.get('track'), info=track.get('info'), ctx=ctx) for track in raw_tracks]
            return objects.Search(source=tracks[0].source, source_type='track', tracks=tracks, result=tracks)

    async def spotify_search(self, *, query: str, spotify_type: str, spotify_id: str, ctx: context.Context = None) -> objects.Search:

        try:
            if spotify_type == 'album':
                result = await self.client.bot.spotify.get_album(spotify_id)
                spotify_tracks = await result.get_all_tracks()
            elif spotify_type == 'playlist':
                result = spotify.Playlist(self.client.bot.spotify, await self.client.bot.spotify_http.get_playlist(spotify_id))
                spotify_tracks = await result.get_all_tracks()
            elif spotify_type == 'track':
                result = await self.client.bot.spotify.get_track(spotify_id)
                spotify_tracks = [result]
            else:
                raise exceptions.VoiceError(f'The query `{query}` is not a valid spotify URL.')

        except spotify.NotFound:
            raise exceptions.VoiceError(f'The query `{query}` is not a valid spotify URL.')

        if not spotify_tracks:
            raise exceptions.VoiceError(f'The query `{query}` is a valid spotify URL however no tracks could be found for it.')

        tracks = []
        for track in spotify_tracks:

            info = {'identifier': track.id, 'isSeekable': False, 'author': ', '.join(artist.name for artist in track.artists), 'length': track.duration,
                    'isStream': False, 'position': 0, 'title': track.name, 'uri': track.url or 'spotify',
                    'thumbnail': track.images[0].url if track.images else None
                    }
            tracks.append(objects.Track(track_id='', info=info, ctx=ctx))

        return objects.Search(source='spotify', source_type=spotify_type, tracks=tracks, result=result)

