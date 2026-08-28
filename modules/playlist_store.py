"""Persistence for Rekordbox source playlists and editable CrateIQ playlists."""

import json
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
        playlist = {
            "id": self._new_id(name), "name": name.strip() or "Untitled playlist",
            "source": "custom", "trackIds": list(track_ids), "createdAt": self._now(),
            "updatedAt": self._now(),
        }
        playlists = self.local_playlists()
        playlists.append(playlist)
        self._write(self.local_path, {"playlists": playlists})
        return playlist

    def update(self, playlist_id, name=None, track_ids=None):
        playlists = self.local_playlists()
        playlist = next((item for item in playlists if item["id"] == playlist_id), None)
        if playlist is None:
            source = next((item for item in self.source_playlists() if item["id"] == playlist_id), None)
            if source is None:
                return None
            playlist = {
                "id": self._new_id(source["name"]), "name": source["name"],
                "source": "rekordbox-copy", "sourceId": source["id"],
                "trackIds": list(source.get("trackIds", [])), "createdAt": self._now(),
                "updatedAt": self._now(),
            }
            playlists.append(playlist)
        if name is not None:
            playlist["name"] = str(name).strip() or playlist["name"]
        if track_ids is not None:
            playlist["trackIds"] = list(track_ids)
        playlist["updatedAt"] = self._now()
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
