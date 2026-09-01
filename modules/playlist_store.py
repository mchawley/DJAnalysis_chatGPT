"""Persistence for Rekordbox source playlists and editable CrateIQ playlists."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


class PlaylistStore:
    def __init__(self, output_directory):
        root = Path(output_directory).parent
        self.source_path = root / "rekordbox_playlists.json"
        self.local_path = root / "playlists.json"

    def source_playlists(self):
        return self._read(self.source_path).get("playlists", [])

    def local_playlists(self):
        return self._read(self.local_path).get("playlists", [])

    def all_playlists(self):
        return self.source_playlists() + self.local_playlists()

    def save_sources(self, playlists):
        self._write(self.source_path, {"playlists": playlists})

    def create(self, name, track_ids):
        playlist = self._playlist(name, "custom", track_ids)
        playlists = self.local_playlists()
        playlists.append(playlist)
        self._write(self.local_path, {"playlists": playlists})
        return playlist

    def entries(self, playlist):
        """Return stable entries without changing immutable source playlists."""
        entries = playlist.get("entries")
        if isinstance(entries, list) and all(isinstance(item, dict) and item.get("id") and item.get("trackId") for item in entries):
            return entries
        return [
            {"id": f"{playlist.get('id', 'playlist')}-{index}", "trackId": track_id}
            for index, track_id in enumerate(playlist.get("trackIds", []))
        ]

    def update(self, playlist_id, name=None, track_ids=None, entry_ids=None):
        playlists = self.local_playlists()
        playlist = next((item for item in playlists if item["id"] == playlist_id), None)
        if playlist is None:
            source = next((item for item in self.source_playlists() if item["id"] == playlist_id), None)
            if source is None:
                return None
            playlist = self._playlist(source["name"], "rekordbox-copy", source.get("trackIds", []), source["id"])
            playlists.append(playlist)
        self._materialize_entries(playlist)
        if name is not None:
            playlist["name"] = str(name).strip() or playlist["name"]
        if entry_ids is not None:
            by_id = {item["id"]: item for item in playlist["entries"]}
            playlist["entries"] = [by_id[item_id] for item_id in entry_ids if item_id in by_id]
        elif track_ids is not None:
            available, reordered = list(playlist["entries"]), []
            for track_id in track_ids:
                match = next((item for item in available if item["trackId"] == track_id), None)
                if match is not None:
                    available.remove(match)
                    reordered.append(match)
                else:
                    reordered.append({"id": self._entry_id(), "trackId": track_id})
            playlist["entries"] = reordered
        playlist["trackIds"] = [item["trackId"] for item in playlist["entries"]]
        playlist.setdefault("segmentExclusions", {})
        playlist["updatedAt"] = self._now()
        self._write(self.local_path, {"playlists": playlists})
        return playlist

    def set_segment_included(self, playlist_id, entry_id, segment_index, included):
        playlist, entry_id = self._editable_entry(playlist_id, entry_id)
        if playlist is None or entry_id not in {item["id"] for item in playlist["entries"]}:
            return None
        try:
            segment_index = int(segment_index)
        except (TypeError, ValueError):
            return None
        exclusions = playlist.setdefault("segmentExclusions", {})
        selected = set(exclusions.get(entry_id, []))
        if included:
            selected.discard(segment_index)
        else:
            selected.add(segment_index)
        if selected:
            exclusions[entry_id] = sorted(selected)
        else:
            exclusions.pop(entry_id, None)
        playlist["updatedAt"] = self._now()
        playlists = self.local_playlists()
        index = next((index for index, item in enumerate(playlists) if item["id"] == playlist["id"]), None)
        if index is not None:
            playlists[index] = playlist
            self._write(self.local_path, {"playlists": playlists})
        return playlist

    def restore_segments(self, playlist_id, entry_id):
        playlist, entry_id = self._editable_entry(playlist_id, entry_id)
        if playlist is None or entry_id not in {item["id"] for item in playlist["entries"]}:
            return None
        playlist.setdefault("segmentExclusions", {}).pop(entry_id, None)
        playlist["updatedAt"] = self._now()
        playlists = self.local_playlists()
        index = next((index for index, item in enumerate(playlists) if item["id"] == playlist["id"]), None)
        if index is not None:
            playlists[index] = playlist
            self._write(self.local_path, {"playlists": playlists})
        return playlist

    def delete(self, playlist_id):
        playlists = self.local_playlists()
        kept = [item for item in playlists if item["id"] != playlist_id]
        if len(kept) == len(playlists):
            return False
        self._write(self.local_path, {"playlists": kept})
        return True

    def restore(self, playlist_id):
        playlist = next((item for item in self.local_playlists() if item["id"] == playlist_id), None)
        source_id = playlist and playlist.get("sourceId")
        source = next((item for item in self.source_playlists() if item["id"] == source_id), None)
        return self.update(playlist_id, track_ids=source["trackIds"]) if source else None

    def _playlist(self, name, source, track_ids, source_id=None):
        playlist = {
            "id": self._new_id(name), "name": name.strip() or "Untitled playlist", "source": source,
            "entries": [{"id": self._entry_id(), "trackId": track_id} for track_id in track_ids],
            "trackIds": list(track_ids), "segmentExclusions": {}, "createdAt": self._now(), "updatedAt": self._now(),
        }
        if source_id:
            playlist["sourceId"] = source_id
        return playlist

    def _materialize_entries(self, playlist):
        if not playlist.get("entries"):
            playlist["entries"] = [{"id": self._entry_id(), "trackId": track_id} for track_id in playlist.get("trackIds", [])]

    def _editable_entry(self, playlist_id, entry_id):
        """Return an editable playlist and translate a source entry into its copy."""
        source = next((item for item in self.source_playlists() if item["id"] == playlist_id), None)
        source_entries = self.entries(source) if source else []
        source_index = next((index for index, item in enumerate(source_entries) if item["id"] == entry_id), None)
        playlist = self.update(playlist_id)
        if playlist is not None and source_index is not None:
            entry_id = playlist["entries"][source_index]["id"]
        return playlist, entry_id

    @staticmethod
    def _read(path):
        if not path.exists():
            return {"playlists": []}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"playlists": []}

    @staticmethod
    def _write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _new_id(name):
        import hashlib
        return "playlist-" + hashlib.sha256(f"{name}:{PlaylistStore._now()}".encode()).hexdigest()[:12]

    @staticmethod
    def _entry_id():
        return "entry-" + uuid.uuid4().hex[:12]
