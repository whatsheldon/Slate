
from __future__ import annotations

import json


class LavalinkStats:

    __slots__ = 'node', 'data', 'playing_players', 'total_players', 'uptime', 'memory_reservable', 'memory_allocated', 'memory_used', 'memory_free', 'system_load', \
                'lavalink_load', 'cpu_cores', 'frames_sent', 'frames_nulled', 'frames_deficit'

    def __init__(self, *, data: dict) -> None:

        self.data = data

        self.playing_players = data.get('playingPlayers')
        self.total_players = data.get('players')
        self.uptime = data.get('uptime')

        memory = data.get('memory', {})
        self.memory_reservable = memory.get('reservable', 0)
        self.memory_allocated = memory.get('allocated', 0)
        self.memory_used = memory.get('used', 0)
        self.memory_free = memory.get('free', 0)

        cpu = data.get('cpu', {})
        self.lavalink_load = cpu.get('lavalinkLoad', 0)
        self.system_load = cpu.get('systemLoad', 0)
        self.cpu_cores = cpu.get('cores', 0)

        frame_stats = data.get('frameStats', {})
        self.frames_deficit = frame_stats.get('deficit', -1)
        self.frames_nulled = frame_stats.get('nulled', -1)
        self.frames_sent = frame_stats.get('sent', -1)

    def __repr__(self) -> str:
        return f'<slate.LavalinkStats total_players={self.total_players} playing_players={self.playing_players} uptime={self.uptime}>'


class AndesiteStats:

    __slots__ = 'data', 'playing_players', 'total_players', 'uptime', 'runtime_pid', 'runtime_management_spec_version', 'runtime_name', 'vm_name', 'vm_vendor', 'vm_version', \
                'spec_name', 'spec_vendor', 'spec_version', 'processors', 'os_name', 'os_arch', 'os_version', 'cpu_andesite', 'cpu_system'

    def __init__(self, *, data: dict) -> None:

        self.data = data

        players = data.get('players')
        self.playing_players = players.get('playing')
        self.total_players = players.get('total')

        runtime = data.get('runtime')
        self.uptime = runtime.get('uptime')
        self.runtime_pid = runtime.get('pid')
        self.runtime_management_spec_version = runtime.get('managementSpecVersion')
        self.runtime_name = runtime.get('name')

        vm = runtime.get('vm')
        self.vm_name = vm.get('name')
        self.vm_vendor = vm.get('vendor')
        self.vm_version = vm.get('version')

        spec = runtime.get('spec')
        self.spec_name = spec.get('name')
        self.spec_vendor = spec.get('vendor')
        self.spec_version = spec.get('version')

        os = data.get('os')
        self.processors = os.get('processors')
        self.os_name = os.get('name')
        self.os_arch = os.get('arch')
        self.os_version = os.get('version')

        cpu = data.get('cpu')
        self.cpu_andesite = cpu.get('andesite')
        self.cpu_system = cpu.get('system')

        # TODO Add memory stats here maybe.

    def __repr__(self) -> str:
        return f'<slate.AndesiteStats total_players={self.total_players} playing_players={self.playing_players} uptime={self.uptime}>'


class Metadata:

    __slots__ = ('data', 'version', 'version_major', 'version_minor', 'version_revision', 'version_commit', 'version_build', 'node_region', 'node_id', 'enabled_sources',
                 'loaded_plugins')

    def __init__(self, *, data: dict) -> None:

        self.data = data

        self.version = data.get('version')
        self.version_major = data.get('versionMajor')
        self.version_minor = data.get('versionMinor')
        self.version_revision = data.get('versionRevision')
        self.version_commit = data.get('versionCommit')
        self.version_build = data.get('versionBuild')
        self.node_region = data.get('nodeRegion')
        self.node_id = data.get('nodeId')
        self.enabled_sources = data.get('enabledSources')
        self.loaded_plugins = data.get('loadedPlugins')

    def __repr__(self) -> str:
        return f'<slate.Metadata version=\'{self.version}\' region=\'{self.node_region}\' id=\'{self.node_id}\' enabled_sources=\'{self.enabled_sources}\'>'


#


class TrackStartEvent:

    __slots__ = ('data', 'player', 'track')

    def __init__(self, *, data: dict) -> None:

        self.data = data
        self.player = data.get('player')

        self.track = data.get('track')

    def __repr__(self) -> str:
        return f'<LavaLinkTrackStartEvent player={self.player!r} track=\'{self.track}\''

    def __str__(self) -> str:
        return 'track_start'


class TrackEndEvent:

    __slots__ = ('data', 'player', 'track', 'reason', 'may_start_next')

    def __init__(self, *, data: dict) -> None:

        self.data = data
        self.player = data.get('player')

        self.track = data.get('track')
        self.reason = data.get('reason')

        self.may_start_next = data.get('mayStartNext', False)

    def __repr__(self) -> str:
        return f'<slate.TrackEndEvent player={self.player} track=\'{self.track}\' reason=\'{self.reason}\''

    def __str__(self) -> str:
        return 'track_end'


class TrackExceptionEvent:

    __slots__ = ('data', 'player', 'track', 'message', 'cause', 'stack', 'suppressed', 'severity')

    def __init__(self, *, data: dict) -> None:

        self.data = data
        self.player = data.get('player')

        self.track = data.get('track')

        exception = data.get('exception')
        self.message = exception.get('message')
        self.cause = exception.get('cause', None)

        self.stack = exception.get('stack', [])
        self.suppressed = exception.get('suppressed', [])

        self.severity = exception.get('severity', 'UNKNOWN')

    def __repr__(self) -> str:
        return f'<slate.TrackExceptionEvent player={self.player} track=\'{self.track}\' message=\'{self.message}\' severity=\'{self.severity}\' cause=\'{self.cause}\''

    def __str__(self) -> str:
        return 'track_exception'


class TrackStuckEvent:

    __slots__ = ('data', 'player', 'track', 'threshold_ms')

    def __init__(self, *, data: dict) -> None:

        self.data = data
        self.player = data.get('player')

        self.track = data.get('track')
        self.threshold_ms = data.get('thresholdMs')

    def __repr__(self) -> str:
        return f'<slate.TrackStuckEvent player={self.player} track=\'{self.track}\' threshold_ms=\'{self.threshold_ms}\''

    def __str__(self) -> str:
        return 'track_stuck'


class WebSocketClosedEvent:

    __slots__ = ('data', 'player', 'track', 'reason', 'code', 'by_remote')

    def __init__(self, *, data: dict) -> None:

        self.data = data
        self.player = data.get('player')

        self.reason = data.get('reason')
        self.code = data.get('code')
        self.by_remote = data.get('byRemote')

    def __repr__(self) -> str:
        return f'<slate.WebSocketClosedEvent player={self.player} reason=\'{self.reason}\' code=\'{self.code}\' by_remote=\'{self.by_remote}\''

    def __str__(self) -> str:
        return 'websocket_closed'


#


class PlayerConnectedEvent:

    __slots__ = ('data', 'player', 'track', 'threshold_ms')

    def __init__(self, *, data: dict) -> None:

        self.data = data
        self.player = data.get('player')

    def __str__(self) -> str:
        return 'lavalink_player_connected'

    def __repr__(self) -> str:
        return f'<LavaLinkPlayerConnectedEvent player={self.player!r}'


class PlayerDisconnectedEvent:

    __slots__ = ('data', 'player')

    def __init__(self, *, data: dict) -> None:

        self.data = data
        self.player = data.get('player')

    def __str__(self) -> str:
        return 'lavalink_player_disconnected'

    def __repr__(self) -> str:
        return f'<LavaLinkPlayerDisconnectedEvent player={self.player!r}'


class PlayerQueueUpdate:

    __slots__ = ('data', 'player')

    def __init__(self, *, data: dict) -> None:

        self.data = data
        self.player = data.get('player')

    def __str__(self) -> str:
        return 'lavalink_player_queue_update'

    def __repr__(self) -> str:
        return f'<LavaLinkPlayerQueueUpdateEvent player={self.player!r}'


#


class Track:

    __slots__ = ('track_id', 'info', 'ctx', 'identifier', 'is_seekable', 'author', 'length', 'is_stream', 'position', 'title', 'uri', 'requester')

    def __init__(self, *, track_id: str, info: dict, ctx: context.Context = None) -> None:

        self.track_id = track_id
        self.info = info
        self.ctx = ctx

        self.identifier = info.get('identifier')
        self.is_seekable = info.get('isSeekable')
        self.author = info.get('author')
        self.length = info.get('length')
        self.is_stream = info.get('isStream')
        self.position = info.get('position')
        self.title = info.get('title')
        self.uri = info.get('uri')

        if self.ctx is not None:
            self.requester = ctx.author

    def __repr__(self) -> str:
        return f'<LavaLinkTrack title=\'{self.title}\' uri=\'<{self.uri}>\' source=\'{self.source}\' length={self.length}>'

    @property
    def thumbnail(self) -> str:

        thumbnail = None

        if self.source == 'Spotify':
            thumbnail = self.info.get('thumbnail')

        elif self.source == 'Youtube':
            thumbnail = f'https://img.youtube.com/vi/{self.identifier}/mqdefault.jpg'

        if thumbnail is None:
            thumbnail = f'https://dummyimage.com/1280x720/000/fff.png&text=+'

        return thumbnail

    @property
    def source(self) -> str:

        if not self.uri:
            return 'Unknown'

        for source in ['youtube', 'vimeo', 'bandcamp', 'soundcloud', 'spotify']:
            if source in self.uri:
                return source.title()

        return 'HTTP'

    @property
    def json(self) -> str:

        data = self.info.copy()
        data['track_id'] = self.track_id
        data['thumbnail'] = self.thumbnail
        data['requester_id'] = self.requester.id
        data['requester_name'] = self.requester.name
        return json.dumps(data)


class Playlist:

    __slots__ = ('playlist_info', 'raw_tracks', 'ctx', 'tracks', 'name', 'selected_track')

    def __init__(self, *, playlist_info: dict, raw_tracks: list, ctx: context.Context = None) -> None:

        self.playlist_info = playlist_info
        self.raw_tracks = raw_tracks
        self.ctx = ctx

        self.tracks = [Track(track_id=track.get('track'), info=track.get('info'), ctx=self.ctx) for track in self.raw_tracks]

        self.name = self.playlist_info.get('name')
        self.selected_track = self.playlist_info.get('selectedTrack')

    def __repr__(self) -> str:
        return f'<LavaLinkPlaylist name=\'{self.name}\' track_count={len(self.tracks)}>'


class Search:

    __slots__ = ('source', 'source_type', 'tracks', 'result')

    def __init__(self, *, source: str, source_type: str, tracks: typing.List[Track],
                 result: typing.Union[spotify.Track, spotify.Album, spotify.Playlist, typing.List[Track], Playlist]):

        self.source = source
        self.source_type = source_type
        self.tracks = tracks
        self.result = result

    def __repr__(self):
        return f'<LavaLinkSearch source=\'{self.source}\' source_type=\'{self.source_type}\' tracks={self.tracks} result={self.tracks}>'
