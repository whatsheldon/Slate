from __future__ import annotations

import collections
from typing import Optional, List, Tuple, Dict, Union


# TODO Implement more classmethods for each filter type.


class Equalizer:

    def __init__(self, *, bands: List[Tuple[int, float]], name='Equalizer') -> None:

        self._bands = self._bands(bands=bands)
        self._name = name

    def __repr__(self) -> str:
        return f'<slate.Equalizer name=\'{self._name}\' bands={self._bands}>'

    def __str__(self) -> str:
        return self._name

    def _bands(self, *, bands: List[Tuple[int, float]]) -> List[Dict[str, float]]:

        for band, gain in bands:

            if band < 0 or band > 14:
                raise ValueError('Band must be within the valid range of 0 to 14.')
            if gain < -0.25 or gain > 1.0:
                raise ValueError('Gain must be within the valid range of -0.25 to 1.0')

        _dict = collections.defaultdict(int)
        _dict.update(bands)

        return [{'band': band, 'gain': _dict[band]} for band in range(15)]

    @property
    def name(self) -> str:
        return self._name

    @property
    def payload(self) -> Dict[str, float]:
        return self._bands

    @classmethod
    def flat(cls) -> Equalizer:

        bands = [(0, 0.0), (1, 0.0), (2, 0.0), (3, 0.0), (4, 0.0), (5, 0.0), (6, 0.0), (7, 0.0), (8, 0.0), (9, 0.0), (10, 0.0), (11, 0.0), (12, 0.0), (13, 0.0), (14, 0.0)]
        return cls(bands=bands, name='Flat')
    

class Karaoke:

    def __init__(self, *, level: Optional[float] = 1.0, mono_level: Optional[float] = 1.0, filter_band: Optional[float] = 220.0, filter_width: Optional[float] = 100.0) -> None:

        self.level = level
        self.mono_level = mono_level
        self.filter_band = filter_band
        self.filter_width = filter_width

        self._name = 'Karaoke'

    def __repr__(self) -> str:
        return f'<slate.Karaoke level={self.level} mono_level={self.mono_level} filter_band={self.filter_band} filter_width={self.filter_width}>'

    def __str__(self) -> str:
        return self._name
    
    @property
    def name(self) -> str:
        return self._name

    @property
    def payload(self) -> Dict[str, float]:
        return {'level': self.level, 'mono_level': self.mono_level, 'filter_band': self.filter_band, 'filter_width': self.filter_width}


class Timescale:

    def __init__(self, *, speed: Optional[float] = 1.0, pitch: Optional[float] = 1.0, rate: Optional[float] = 1.0) -> None:

        self.speed = speed
        self.pitch = pitch
        self.rate = rate

        self._name = 'Timescale'

    def __repr__(self) -> str:
        return f'<slate.Timescale speed={self.speed} pitch={self.pitch} rate={self.rate}>'

    def __str__(self) -> str:
        return self._name

    @property
    def name(self) -> str:
        return self._name

    @property
    def payload(self) -> Dict[str, float]:
        return {'speed': self.speed, 'pitch': self.pitch, 'rate': self.rate}


class Tremolo:

    def __init__(self, *, frequency: Optional[float] = 2.0, depth: Optional[float] = 0.5) -> None:

        if frequency < 0:
            raise ValueError('Frequency must be more than 0.0')
        if not 0 < depth <= 1:
            raise ValueError('Depth must be more than 0.0 and less than or equal to 1.0')

        self.frequency = frequency
        self.depth = depth

        self._name = 'Tremolo'

    def __repr__(self) -> str:
        return f'<slate.Tremolo frequency={self.frequency} depth={self.depth}>'

    def __str__(self) -> str:
        return self._name

    @property
    def name(self) -> str:
        return self._name

    @property
    def payload(self) -> Dict[str, float]:
        return {'frequency': self.frequency, 'depth': self.depth}


class Vibrato:

    def __init__(self, *, frequency: Optional[float] = 2.0, depth: Optional[float] = 0.5) -> None:

        if not 0 < frequency <= 14:
            raise ValueError('Frequency must be more than 0.0 and less than or equal to 14.0')
        if not 0 < depth <= 1:
            raise ValueError('Depth must be more than 0.0 and less than or equal to 1.0')

        self.frequency = frequency
        self.depth = depth

        self._name = 'Vibrato'

    def __repr__(self) -> str:
        return f'<slate.Vibrato frequency={self.frequency} depth={self.depth}>'

    def __str__(self) -> str:
        return self._name

    @property
    def name(self) -> str:
        return self._name

    @property
    def payload(self) -> Dict[str, float]:
        return {'frequency': self.frequency, 'depth': self.depth}


class Filter:

    def __init__(self, *, filter: Filter = None, volume: Optional[float] = None, equalizer: Optional[Equalizer] = None, karaoke: Optional[Karaoke] = None,
                 timescale: Optional[Timescale] = None, tremolo: Optional[Tremolo] = None, vibrato: Optional[Vibrato] = None) -> None:

        self.filter = filter
        self.volume = volume
        self.equalizer = equalizer
        self.karaoke = karaoke
        self.timescale = timescale
        self.tremolo = tremolo
        self.vibrato = vibrato

    def __repr__(self) -> str:
        return f'<slate.Filter volume={self.volume} equalizer={self.equalizer} karaoke={self.karaoke} timescale={self.timescale} tremolo={self.tremolo} vibrato={self.vibrato}>'

    @property
    def payload(self) -> Dict[str, Union[Dict[str, float], float]]:

        payload = self.filter.payload.copy() if self.filter is not None else {}

        if self.volume is not None:
            payload['volume'] = self.volume

        if self.equalizer is not None:
            payload['equalizer'] = self.equalizer.payload
        if self.karaoke is not None:
            payload['karaoke'] = self.karaoke.payload
        if self.timescale is not None:
            payload['timescale'] = self.timescale.payload
        if self.tremolo is not None:
            payload['tremolo'] = self.tremolo.payload
        if self.vibrato is not None:
            payload['vibrato'] = self.vibrato.payload

        return payload
