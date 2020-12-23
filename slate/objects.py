
from __future__ import annotations

from typing import Dict, List, Optional, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from .player import Player


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

        self.data: dict = data
        self.player: Protocol[Player] = data.get('player')

        self.track = data.get('track')

    def __repr__(self) -> str:
        return f'<LavaLinkTrackStartEvent player={self.player!r} track=\'{self.track}\''

    def __str__(self) -> str:
        return 'track_start'


class TrackEndEvent:

    __slots__ = ('data', 'player', 'track', 'reason', 'may_start_next')

    def __init__(self, *, data: dict) -> None:

        self.data: dict = data
        self.player: Protocol[Player] = data.get('player')

        self.track = data.get('track')

        self.reason: str = data.get('reason')
        self.may_start_next: bool = data.get('mayStartNext', False)

    def __repr__(self) -> str:
        return f'<slate.TrackEndEvent player={self.player} track=\'{self.track}\' reason=\'{self.reason}\''

    def __str__(self) -> str:
        return 'track_end'


class TrackExceptionEvent:

    __slots__ = ('data', 'player', 'track', 'message', 'cause', 'stack', 'suppressed', 'severity')

    def __init__(self, *, data: dict) -> None:

        self.data: dict = data
        self.player: Protocol[Player] = data.get('player')

        self.track = data.get('track')

        exception = data.get('exception')
        self.message: str = exception.get('message')
        self.cause: str = exception.get('cause', None)
        self.stack: str = exception.get('stack', [])
        self.suppressed: str = exception.get('suppressed', [])
        self.severity: str = exception.get('severity', 'UNKNOWN')

    def __repr__(self) -> str:
        return f'<slate.TrackExceptionEvent player={self.player} track=\'{self.track}\' message=\'{self.message}\' severity=\'{self.severity}\' cause=\'{self.cause}\''

    def __str__(self) -> str:
        return 'track_exception'


class TrackStuckEvent:

    __slots__ = ('data', 'player', 'track', 'threshold_ms')

    def __init__(self, *, data: dict) -> None:

        self.data: dict = data
        self.player: Protocol[Player] = data.get('player')

        self.track = data.get('track')

        self.threshold_ms: str = data.get('thresholdMs')

    def __repr__(self) -> str:
        return f'<slate.TrackStuckEvent player={self.player} track=\'{self.track}\' threshold_ms=\'{self.threshold_ms}\''

    def __str__(self) -> str:
        return 'track_stuck'


class WebSocketClosedEvent:

    __slots__ = ('data', 'player', 'track', 'reason', 'code', 'by_remote')

    def __init__(self, *, data: dict) -> None:

        self.data: dict = data
        self.player: Protocol[Player] = data.get('player')

        self.reason: str = data.get('reason')
        self.code: str = data.get('code')
        self.by_remote: str = data.get('byRemote')

    def __repr__(self) -> str:
        return f'<slate.WebSocketClosedEvent player={self.player} reason=\'{self.reason}\' code=\'{self.code}\' by_remote=\'{self.by_remote}\''

    def __str__(self) -> str:
        return 'websocket_closed'


#


class Track:

    __slots__ = ('_track_id', '_track_info', '_class', '_title', '_author', '_length', '_identifier', '_uri', '_is_stream', '_is_seekable', '_position')

    def __init__(self, *, track_id: str, track_info: dict) -> None:

        self._track_id = track_id
        self._track_info = track_info

        self._class = track_info.get('class', 'UNKNOWN')

        self._title = track_info.get('title')
        self._author = track_info.get('author')
        self._length = track_info.get('length')
        self._identifier = track_info.get('identifier')
        self._uri = track_info.get('uri')
        self._is_stream = track_info.get('isStream')
        self._is_seekable = track_info.get('isSeekable')
        self._position = track_info.get('position')

    def __repr__(self) -> str:
        return f'<slate.Track title=\'{self._title}\' uri=\'<{self._uri}>\' source=\'{self.source}\' length={self._length}>'

    #

    @property
    def track_id(self) -> str:
        return self._track_id

    @property
    def title(self) -> str:
        return self._title

    @property
    def author(self) -> str:
        return self._author

    @property
    def length(self) -> int:
        return self._length

    @property
    def identifier(self) -> str:
        return self._identifier

    @property
    def uri(self) -> str:
        return self._uri

    @property
    def is_stream(self) -> bool:
        return self._is_stream

    @property
    def is_seekable(self) -> bool:
        return self._is_seekable

    @property
    def position(self) -> int:
        return self._position

    #

    @property
    def source(self) -> str:

        if not self.uri:
            return 'UNKNOWN'

        for source in ['bandcamp', 'beam', 'soundcloud', 'twitch', 'vimeo', 'youtube']:
            if source in self.uri:
                return source.title()

        return 'HTTP'

    @property
    def thumbnail(self) -> str:

        if self.source == 'Youtube':
            return f'https://img.youtube.com/vi/{self.identifier}/mqdefault.jpg'

        return f'https://dummyimage.com/1280x720/000/fff.png&text=+'


class Playlist:

    __slots__ = ('_playlist_info', '_raw_tracks', '_tracks', '_name', '_selected_track')

    def __init__(self, *, playlist_info: dict, tracks: List[Dict]) -> None:

        self._playlist_info = playlist_info

        self._name = self._playlist_info.get('name')
        self._selected_track = self._playlist_info.get('selectedTrack')

        self._raw_tracks = tracks

        self._tracks = [Track(track_id=track.get('track'), track_info=track.get('info')) for track in self._raw_tracks]

    def __repr__(self) -> str:
        return f'<slate.Playlist name=\'{self._name}\' selected_track={self.selected_track} track_count={len(self._tracks)}>'

    #

    @property
    def name(self) -> str:
        return self._name

    @property
    def selected_track(self) -> Optional[Track]:
        try:
            return self._tracks[self._selected_track]
        except IndexError:
            return None

    @property
    def tracks(self) -> List[Track]:
        return self._tracks