from dataclasses import dataclass
from pathlib import Path

from .models import RekordboxTrack


@dataclass(frozen=True)
class MatchResult:
    track: RekordboxTrack | None
    confidence: int
    method: str


class RekordboxMatcher:
    """Match CrateIQ tracks to Rekordbox records without hashing."""

    def __init__(self, rekordbox_tracks):
        self.rekordbox_tracks = list(rekordbox_tracks)

    def match(self, crateiq_track, document=None):
        path_match = self._unique_match(
            lambda track: self._normalise_path(track.location)
            == self._normalise_path(crateiq_track.path)
        )
        if path_match:
            return MatchResult(path_match, 100, "Path")

        filename_match = self._unique_match(
            lambda track: Path(track.location).name.casefold()
            == Path(crateiq_track.path).name.casefold()
        )
        if filename_match:
            return MatchResult(filename_match, 90, "Filename")

        metadata = (document or {}).get("metadata", {})
        title = metadata.get("title")
        artist = metadata.get("artist")
        if title and artist:
            title_artist_match = self._unique_match(
                lambda track: track.title.casefold() == str(title).casefold()
                and track.artist.casefold() == str(artist).casefold()
            )
            if title_artist_match:
                return MatchResult(title_artist_match, 80, "TitleArtist")

        return MatchResult(None, 0, "No Match")

    def _unique_match(self, predicate):
        matches = [track for track in self.rekordbox_tracks if predicate(track)]
        return matches[0] if len(matches) == 1 else None

    @staticmethod
    def _normalise_path(path):
        return str(Path(path)).replace("\\", "/").casefold()
