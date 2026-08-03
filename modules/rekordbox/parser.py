from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree as ET

from .models import BeatGridMarker, HotCue, MemoryCue, Playlist, RekordboxTrack


class RekordboxParser:
    """Parse a Rekordbox XML export without depending on CrateIQ documents."""

    def parse(self, xml_path) -> list[RekordboxTrack]:
        root = ET.parse(xml_path).getroot()
        tracks_by_id = {
            element.get("TrackID", ""): self._parse_track(element)
            for element in self._elements_named(root, "TRACK")
            if element.get("TrackID")
        }

        playlists = self._parse_playlists(root, tracks_by_id)
        for playlist in playlists:
            for location in playlist.track_locations:
                for track in tracks_by_id.values():
                    if track.location == location:
                        track.playlists.append(playlist.name)

        return list(tracks_by_id.values())

    def _parse_track(self, element):
        memory_cues, hot_cues = self._parse_cues(element)
        return RekordboxTrack(
            track_id=element.get("TrackID", ""),
            location=self._normalise_location(element.get("Location", "")),
            title=element.get("Name", ""),
            artist=element.get("Artist", ""),
            album=self._optional_attribute(element, "Album"),
            genre=self._optional_attribute(element, "Genre"),
            bpm=self._as_float(element.get("AverageBpm")),
            key=self._optional_attribute(element, "Tonality"),
            rating=self._as_int(element.get("Rating")),
            color=self._optional_attribute(element, "Colour"),
            comments=self._optional_attribute(element, "Comments"),
            date_added=self._as_datetime(element.get("DateAdded")),
            play_count=self._as_int(element.get("PlayCount")),
            last_played=self._as_datetime(element.get("LastPlayed")),
            memory_cues=memory_cues,
            hot_cues=hot_cues,
            beat_grid=self._parse_beat_grid(element),
        )

    def _parse_cues(self, element):
        memory_cues = []
        hot_cues = []
        for marker in self._children_named(element, "POSITION_MARK"):
            position = self._as_float(marker.get("Start"))
            if position is None:
                continue
            cue_data = {
                "position": position,
                "name": self._optional_attribute(marker, "Name"),
                "end": self._as_float(marker.get("End")),
                "color": self._marker_color(marker),
            }
            number = self._as_int(marker.get("Num"))
            if marker.get("Type") == "0" and (number is None or number < 0):
                memory_cues.append(MemoryCue(**cue_data))
            else:
                hot_cues.append(HotCue(**cue_data, number=number))
        return memory_cues, hot_cues

    def _parse_beat_grid(self, element):
        return [
            BeatGridMarker(
                position=self._as_float(tempo.get("Inizio")) or 0.0,
                bpm=self._as_float(tempo.get("Bpm")),
                beat_number=self._as_int(tempo.get("Battito")),
            )
            for tempo in self._children_named(element, "TEMPO")
            if self._as_float(tempo.get("Inizio")) is not None
        ]

    def _parse_playlists(self, root, tracks_by_id):
        playlists = []
        playlist_roots = self._elements_named(root, "PLAYLISTS")
        if not playlist_roots:
            return playlists

        def visit(node, parents):
            name = node.get("Name", "")
            path = parents + [name] if name else parents
            track_ids = [child.get("Key") for child in self._children_named(node, "TRACK")]
            if track_ids:
                locations = [
                    tracks_by_id[track_id].location
                    for track_id in track_ids
                    if track_id in tracks_by_id
                ]
                playlists.append(Playlist(name=" / ".join(path), track_locations=locations))
            for child in self._children_named(node, "NODE"):
                visit(child, path)

        for playlist_root in playlist_roots:
            for node in self._children_named(playlist_root, "NODE"):
                visit(node, [])
        return playlists

    @staticmethod
    def _normalise_location(location):
        if not location:
            return ""
        parsed = urlparse(location)
        if parsed.scheme.lower() != "file":
            return unquote(location)
        path = unquote(parsed.path)
        if parsed.netloc and parsed.netloc.lower() not in {"", "localhost"}:
            path = f"//{parsed.netloc}{path}"
        return path

    @staticmethod
    def _marker_color(marker):
        channels = [marker.get(channel) for channel in ("Red", "Green", "Blue")]
        if any(channel is None for channel in channels):
            return None
        return "#{:02X}{:02X}{:02X}".format(*(int(channel) for channel in channels))

    @staticmethod
    def _as_float(value):
        try:
            return float(value) if value not in (None, "") else None
        except ValueError:
            return None

    @staticmethod
    def _as_int(value):
        try:
            return int(value) if value not in (None, "") else None
        except ValueError:
            return None

    @staticmethod
    def _as_datetime(value):
        if not value or value in {"0000-00-00", "0000-00-00 00:00:00"}:
            return None
        for format_string in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
            try:
                return datetime.strptime(value, format_string)
            except ValueError:
                continue
        return None

    @staticmethod
    def _optional_attribute(element, name):
        value = element.get(name)
        return value if value not in (None, "") else None

    @staticmethod
    def _elements_named(root, name):
        return (element for element in root.iter() if element.tag.split("}")[-1] == name)

    @staticmethod
    def _children_named(element, name):
        return (child for child in element if child.tag.split("}")[-1] == name)
