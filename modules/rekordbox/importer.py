from .models import CuePoint, HotCue, RekordboxTrack


class RekordboxImporter:
    """Copy Rekordbox-specific DJ metadata into a track document's library section."""

    def import_track(self, document, rekordbox_track: RekordboxTrack):
        library = document.setdefault("library", {})
        library.update(
            {
                "provider": "rekordbox",
                "trackId": rekordbox_track.track_id,
                "rating": rekordbox_track.rating,
                "color": rekordbox_track.color,
                "comments": rekordbox_track.comments,
                "bpm": rekordbox_track.bpm,
                "key": rekordbox_track.key,
                "playCount": rekordbox_track.play_count,
                "lastPlayed": self._datetime_value(rekordbox_track.last_played),
                "playlists": list(rekordbox_track.playlists),
                "memoryCues": [self._cue_value(cue) for cue in rekordbox_track.memory_cues],
                "hotCues": [self._cue_value(cue) for cue in rekordbox_track.hot_cues],
            }
        )
        return document

    @staticmethod
    def _datetime_value(value):
        return value.isoformat() if value else None

    @staticmethod
    def _cue_value(cue: CuePoint):
        value = {
            "position": cue.position,
            "name": cue.name,
            "end": cue.end,
            "color": cue.color,
        }
        if isinstance(cue, HotCue):
            value["number"] = cue.number
        return value
