import json
from copy import deepcopy
from pathlib import Path


class JsonManager:
    """Load, save, and update per-track JSON documents."""

    TRACK_DOCUMENT_TEMPLATE = {
        "metadata": {},
        "rekordbox": {},
        "audio": {},
        "structure": {},
        "features": {},
        "energy": {},
        "dj": {},
        "system": {"modules": {}},
    }

    def __init__(self, output_directory):
        self.output_directory = Path(output_directory)
        self.output_directory.mkdir(parents=True, exist_ok=True)

    def get_json_path(self, track_id):
        return self.output_directory / f"{track_id}.json"

    def load(self, track_id):
        """Load a document, or return a new track document when none exists."""
        json_path = self.get_json_path(track_id)

        if not json_path.exists():
            return deepcopy(self.TRACK_DOCUMENT_TEMPLATE)

        with json_path.open("r", encoding="utf-8") as json_file:
            return json.load(json_file)

    def save(self, track_id, document):
        """Persist a track document."""
        with self.get_json_path(track_id).open("w", encoding="utf-8") as json_file:
            json.dump(document, json_file, indent=4, ensure_ascii=False)

    def update_section(self, track_id, section_name, section_data):
        document = self.load(track_id)
        document[section_name] = section_data
        self.save(track_id, document)

    def get_section(self, track_id, section_name):
        return self.load(track_id).get(section_name, {})

    def update_module_status(
        self,
        track_id,
        module_name,
        version,
        completed=True,
        timestamp=None,
    ):
        document = self.load(track_id)
        system = document.setdefault("system", {})
        modules = system.setdefault("modules", {})
        modules[module_name] = {
            "version": version,
            "completed": completed,
            "timestamp": timestamp,
        }
        self.save(track_id, document)

    def get_module_status(self, track_id, module_name):
        document = self.load(track_id)
        return document.get("system", {}).get("modules", {}).get(module_name)
