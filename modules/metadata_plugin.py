from datetime import datetime, timezone

from modules.metadata import MetadataExtractor
from modules.plugin import Plugin


class MetadataPlugin(Plugin):
    """Extract normalized tags and technical details for a track."""

    NAME = "metadata"
    VERSION = "1.0"

    def __init__(self, extractor=None):
        self.extractor = extractor or MetadataExtractor()

    def needs_processing(self, document, track):
        status = document.get("system", {}).get("modules", {}).get(self.NAME)
        return not document.get("metadata") or not self._is_current(status)

    def process(self, document, track):
        document["metadata"] = self.extractor.extract(track.path)

        system = document.setdefault("system", {})
        modules = system.setdefault("modules", {})
        modules[self.NAME] = {
            "version": self.VERSION,
            "completed": True,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }

    def _is_current(self, status):
        return (
            status is not None
            and status.get("completed") is True
            and status.get("version") == self.VERSION
        )
