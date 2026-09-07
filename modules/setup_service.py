"""Local setup validation and persistence for the browser onboarding flow."""

import json
import os
from copy import deepcopy
from pathlib import Path

from modules.config import DEFAULT_CONFIG


class SetupService:
    MODULES = ("metadata", "rekordbox_library", "rekordbox_analysis", "energy", "fingerprint")

    def __init__(self, path="config/config.json"):
        self.path = Path(path)

    def current(self):
        if not self.path.exists():
            return deepcopy(DEFAULT_CONFIG)
        data = deepcopy(DEFAULT_CONFIG)
        data.update(json.loads(self.path.read_text(encoding="utf-8")))
        data["modules"] = {**DEFAULT_CONFIG["modules"], **data.get("modules", {})}
        return data

    def validate(self, value):
        config = self._normalise(value)
        errors = []
        if not config["musicRoots"]:
            errors.append("Add at least one music folder.")
        for root in config["musicRoots"]:
            if not Path(root).is_dir():
                errors.append(f"Music folder does not exist: {root}")
        if config["rekordboxXmlPath"] and not Path(config["rekordboxXmlPath"]).is_file():
            errors.append(f"Rekordbox XML file does not exist: {config['rekordboxXmlPath']}")
        if not config["supportedFormats"]:
            errors.append("Choose at least one supported audio format.")
        if config["analysisWorkers"] < 1:
            errors.append("Workers must be at least 1.")
        return {"valid": not errors, "errors": errors, "config": config}

    def save(self, value):
        result = self.validate(value)
        if not result["valid"]:
            return result
        Path(result["config"]["outputRoot"]).mkdir(parents=True, exist_ok=True)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(result["config"], indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(temporary, self.path)
        return result

    def _normalise(self, value):
        base = self.current()
        roots = []
        for item in value.get("musicRoots", []):
            path = str(item or "").strip()
            if path:
                resolved = str(Path(path).expanduser().resolve())
                if resolved not in roots:
                    roots.append(resolved)
        raw_xml = str(value.get("rekordboxXmlPath") or "").strip()
        formats = []
        for extension in value.get("supportedFormats", base["supportedFormats"]):
            extension = str(extension).strip().lower()
            if extension:
                formats.append(extension if extension.startswith(".") else f".{extension}")
        return {
            "musicRoots": roots,
            "outputRoot": str(Path(value.get("outputRoot") or base["outputRoot"]).expanduser()),
            "rekordboxXmlPath": str(Path(raw_xml).expanduser().resolve()) if raw_xml else None,
            "analysisWorkers": max(0, int(value.get("analysisWorkers", base["analysisWorkers"]))),
            "modules": {name: bool(value.get("modules", {}).get(name, base["modules"][name])) for name in self.MODULES},
            "supportedFormats": list(dict.fromkeys(formats)),
        }
