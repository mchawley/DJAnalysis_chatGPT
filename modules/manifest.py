import json
from pathlib import Path


class ManifestManager:
    """Maintain a lightweight index of the tracks known to the pipeline."""

    def __init__(self, output_directory, filename="tracks_manifest.json"):
        output_path = Path(output_directory)
        self.manifest_path = output_path.parent / filename
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self):
        """Return the stored track index, or an empty index on first run."""
        if not self.manifest_path.exists():
            return {"tracks": {}}

        with self.manifest_path.open("r", encoding="utf-8") as manifest_file:
            manifest = json.load(manifest_file)

        manifest.setdefault("tracks", {})
        return manifest

    def save(self, tracks):
        """Persist the complete current track index."""
        with self.manifest_path.open("w", encoding="utf-8") as manifest_file:
            json.dump({"tracks": tracks}, manifest_file, indent=4, ensure_ascii=False)

    @staticmethod
    def build_entry(track_id, source_path, document_path):
        source_path = Path(source_path)
        stat = source_path.stat()
        return {
            "path": str(source_path),
            "size": stat.st_size,
            "modified": stat.st_mtime_ns,
            "hash": track_id,
            "json": str(document_path),
        }

    @staticmethod
    def get_track_state(previous_entry, current_entry):
        """Classify a track whose content hash has not changed."""
        if previous_entry is None:
            return "new"
        if previous_entry.get("path") != current_entry["path"]:
            return "moved"
        if (
            previous_entry.get("size") != current_entry["size"]
            or previous_entry.get("modified") != current_entry["modified"]
        ):
            return "modified"
        return "unchanged"
