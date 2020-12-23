__title__ = 'slate'
__author__ = 'Axelancerr'
__license__ = 'MIT'
__copyright__ = 'Copyright 2020 Axelancerr'
__version__ = '0.1.0'

import logging
from collections import namedtuple

from .andesite_node import AndesiteNode
from .bases import BaseNode
from .client import Client
from .exceptions import *
from .filters import Equalizer, Filter, Karaoke, Timescale, Tremolo, Vibrato
from .lavalink_node import LavalinkNode
from .objects import Playlist, Track, TrackEndEvent, TrackExceptionEvent, TrackStartEvent, TrackStuckEvent, WebSocketClosedEvent, Metadata, LavalinkStats, AndesiteStats
from .player import Player

version_info = namedtuple('VersionInfo', 'major minor micro releaselevel serial')(major=0, minor=1, micro=0, releaselevel='alpha', serial=0)
logging.getLogger(__name__).addHandler(logging.NullHandler())
