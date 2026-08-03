from datetime import datetime, timezone

from modules.energy import EnergyExtractor
from modules.plugin import Plugin


class EnergyPlugin(Plugin):
    """Generate phrase-level audio features from Rekordbox phrase boundaries."""

    NAME = "energy"
    VERSION = "1.1"

    def __init__(self, extractor=None):
        self.extractor = extractor or EnergyExtractor()

    def needs_processing(self, document, track):
        phrases = document.get("analysis", {}).get("phrases", [])
        status = document.get("system", {}).get("modules", {}).get(self.NAME, {})
        return bool(phrases) and not (
            status.get("completed") is True and status.get("version") == self.VERSION
        )

    def process(self, document, track):
        document["energy"] = self.extractor.extract(track.path, document["analysis"])
        document.setdefault("system", {}).setdefault("modules", {})[self.NAME] = {
            "version": self.VERSION,
            "completed": True,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
