__title__ = 'slate'
__author__ = 'Axelancerr'
__license__ = 'MIT'
__copyright__ = 'Copyright 2020 Axelancerr'
__version__ = '0.1.0'

from collections import namedtuple

version_info = namedtuple('VersionInfo', 'major minor micro releaselevel serial')(major=0, minor=1, micro=0, releaselevel='alpha', serial=0)

from .filters import Filter, Karaoke, Timescale, Tremolo, Vibrato, Equalizer
