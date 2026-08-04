import json
from math import isfinite
from pathlib import Path


class FingerprintValidator:
    """Inspect fingerprint completeness and plot comparable feature distributions."""

    FEATURES = ("energy.overall", "bass.overall", "rhythm.density", "spectrum.spectral_centroid")

    def validate(self, fingerprint):
        issues = []
        for path in self.FEATURES:
            value = self._value(fingerprint, path)
            if not isinstance(value, (int, float)) or not isfinite(value): issues.append(path)
        return issues

    def summarize_documents(self, json_paths):
        rows = []
        for json_path in json_paths:
            document = json.loads(Path(json_path).read_text())
            for index, fingerprint in enumerate(document.get("analysis", {}).get("fingerprints", [])):
                rows.append({"track_id": document.get("system", {}).get("trackId"), "segment_index": index, "fingerprint": fingerprint, "issues": self.validate(fingerprint)})
        return rows

    def plot(self, rows, output_path):
        import matplotlib.pyplot as plt
        figure, axes = plt.subplots(2, 2, figsize=(12, 8))
        for axis, path in zip(axes.flat, self.FEATURES):
            values = [self._value(row["fingerprint"], path) for row in rows]
            axis.hist([value for value in values if isinstance(value, (int, float))], bins=30)
            axis.set_title(path)
        figure.tight_layout(); figure.savefig(output_path); plt.close(figure)

    @staticmethod
    def _value(fingerprint, path):
        value = fingerprint
        for part in path.split("."):
            value = value.get(part) if isinstance(value, dict) else None
        return value
