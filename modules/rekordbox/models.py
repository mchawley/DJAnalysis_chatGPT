from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class CuePoint:
    position: float
    name: str | None = None
    end: float | None = None
    color: str | None = None


@dataclass(frozen=True)
class MemoryCue(CuePoint):
    pass


@dataclass(frozen=True)
class HotCue(CuePoint):
    number: int | None = None


@dataclass(frozen=True)
class Playlist:
    name: str
    track_locations: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class BeatGridMarker:
    position: float
    bpm: float | None = None
    beat_number: int | None = None


@dataclass
class RekordboxTrack:
    track_id: str
    location: str
    title: str
    artist: str
    album: str | None
    genre: str | None
    bpm: float | None
    key: str | None
    rating: int | None
    color: str | None
    comments: str | None
    date_added: datetime | None
    play_count: int | None
    last_played: datetime | None
    memory_cues: list[MemoryCue] = field(default_factory=list)
    hot_cues: list[HotCue] = field(default_factory=list)
    playlists: list[str] = field(default_factory=list)
    beat_grid: list[BeatGridMarker] = field(default_factory=list)
