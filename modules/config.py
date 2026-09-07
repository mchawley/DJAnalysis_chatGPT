"""Configuration loading with a safe first-run state."""

import json
from pathlib import Path


DEFAULT_CONFIG = {
    "musicRoots": [], "outputRoot": "./output/tracks", "rekordboxXmlPath": None,
    "analysisWorkers": 2,
    "modules": {"metadata": True, "rekordbox_library": True, "rekordbox_analysis": True, "energy": True, "fingerprint": True},
    "supportedFormats": [".mp3", ".flac", ".wav", ".aiff", ".m4a"],
}


class ConfigurationRequiredError(RuntimeError):
    """Raised when analysis is requested before local setup is complete."""


class Config:
    def __init__(self, path="config/config.json", data=None):
        self.path = Path(path)
        if data is not None:
            self.data = data
        elif self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self.data = dict(DEFAULT_CONFIG)

    @property
    def configured(self):
        return bool(self.data.get("musicRoots") or self.data.get("musicRoot"))

    def require_configured(self):
        if not self.configured:
            raise ConfigurationRequiredError("Complete local setup before running analysis.")

    def module_enabled(self, name, default=True):
        return bool(self.data.get("modules", {}).get(name, default))
