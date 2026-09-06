"""Global, local-on-disk playable segment choices."""

import json
from datetime import datetime, timezone
from pathlib import Path

from modules.playlist_store import PlaylistStore


class SegmentSelectionStore:
    VERSION = 1

    def __init__(self, output_directory):
        self.output_root = Path(output_directory).parent
        self.path = self.output_root / "segment_selections.json"

    def excluded(self, track_id):
        data = self._migrate()
        return set(data.get("tracks", {}).get(track_id, {}).get("excludedSegments", []))

    def set_included(self, track_id, segment_index, included):
        try:
            segment_index = int(segment_index)
        except (TypeError, ValueError):
            return None
        data = self._migrate()
        tracks = data.setdefault("tracks", {})
        selection = tracks.setdefault(track_id, {"excludedSegments": []})
        excluded = set(selection.get("excludedSegments", []))
        if included:
            excluded.discard(segment_index)
        else:
            excluded.add(segment_index)
        if excluded:
            selection["excludedSegments"] = sorted(excluded)
            selection["updatedAt"] = self._now()
        else:
            tracks.pop(track_id, None)
        self._write(data)
        return {"trackId": track_id, "excludedSegments": sorted(excluded)}

    def restore(self, track_id):
        data = self._migrate()
        data.setdefault("tracks", {}).pop(track_id, None)
        self._write(data)
        return {"trackId": track_id, "excludedSegments": []}

    def _migrate(self):
        data = self._read()
        if data.get("migrationVersion") == self.VERSION:
            return data
        store = PlaylistStore(self.output_root / "tracks")
        playlists = store.local_playlists()
        tracks = data.setdefault("tracks", {})
        changed = False
        for playlist in playlists:
            exclusions = playlist.get("segmentExclusions", {})
            if not exclusions:
                continue
            entries = {entry["id"]: entry["trackId"] for entry in store.entries(playlist)}
            for entry_id, indexes in exclusions.items():
                track_id = entries.get(entry_id)
                if not track_id:
                    continue
                selection = tracks.setdefault(track_id, {"excludedSegments": []})
                selection["excludedSegments"] = sorted(set(selection["excludedSegments"]) | {int(index) for index in indexes})
                selection["updatedAt"] = self._now()
            playlist["segmentExclusions"] = {}
            playlist["updatedAt"] = self._now()
            changed = True
        if changed:
            store._write(store.local_path, {"playlists": playlists})
        data["migrationVersion"] = self.VERSION
        self._write(data)
        return data

    def _read(self):
        if not self.path.exists():
            return {"migrationVersion": None, "tracks": {}}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"migrationVersion": None, "tracks": {}}

    def _write(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
