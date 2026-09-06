"""Lossless raw-feature sidecars and compact fingerprint document helpers."""

import json
import os
import tempfile
from pathlib import Path


RAW_ARRAY_FIELDS = (
    "rms", "mfcc", "chroma", "spectral_contrast", "tonnetz",
    "zero_crossing_rate", "spectral_flux", "onset_strength", "beat_positions",
)
TEMPORAL_FIELDS = ("rms", "onset_strength", "spectral_flux", "zero_crossing_rate")
DISPLAY_BINS = 120
TEMPORAL_BINS = 32
VERSION = "1.0"


def resample(values, size):
    """Return a fixed-length linear representation without needing raw audio."""
    if not values:
        return [0.0] * size
    if len(values) == 1:
        return [float(values[0])] * size
    result = []
    for index in range(size):
        position = index * (len(values) - 1) / max(size - 1, 1)
        left = int(position)
        right = min(left + 1, len(values) - 1)
        result.append(float(values[left]) + (float(values[right]) - float(values[left])) * (position - left))
    return result


def display_values(fingerprint, field):
    display = fingerprint.get("display_features", {})
    if field in display:
        return display[field]
    return fingerprint.get("raw_features", {}).get(field, [])


def temporal_values(fingerprint, field):
    temporal = fingerprint.get("temporal_features", {})
    if field in temporal:
        return temporal[field]
    return fingerprint.get("raw_features", {}).get(field, [])


def load_raw_features(document, fingerprint, output_root):
    """Load one segment's exact raw data from either supported storage format."""
    raw = fingerprint.get("raw_features", {})
    if any(field in raw for field in RAW_ARRAY_FIELDS):
        return raw
    store = document.get("analysis", {}).get("rawFeatureStore", {})
    segment = raw.get("sidecar_segment")
    if store.get("format") != "npz" or not isinstance(segment, int):
        return raw
    import numpy as np
    path = Path(output_root).parent / store.get("path", "")
    with np.load(path, allow_pickle=False) as sidecar:
        values = {field: sidecar[f"segment_{segment}/{field}"].tolist() for field in RAW_ARRAY_FIELDS}
    values["lufs"] = raw.get("lufs")
    return values


class FingerprintCompactor:
    """Move large exact arrays out of a track document without changing its summaries."""

    def __init__(self, output_root):
        self.output_root = Path(output_root)
        self.sidecar_root = self.output_root.parent / "raw_features"

    def compact_path(self, document_path):
        document_path = Path(document_path)
        before_bytes = document_path.stat().st_size
        document = json.loads(document_path.read_text(encoding="utf-8"))
        result = self.compact_document(document)
        if result["status"] != "migrated":
            return result
        sidecar = self.sidecar_root / f"{result['track_id']}.npz"
        self._write_sidecar(sidecar, result.pop("arrays"))
        self._verify_sidecar(sidecar, result.pop("expected"))
        self._atomic_json_write(document_path, document)
        result["before_bytes"] = before_bytes
        result["after_bytes"] = document_path.stat().st_size
        return result

    def compact_document(self, document):
        analysis = document.get("analysis", {})
        fingerprints = analysis.get("fingerprints", [])
        track_id = document.get("system", {}).get("trackId")
        if analysis.get("rawFeatureStore", {}).get("version") == VERSION:
            return {"status": "already", "track_id": track_id}
        if not track_id or not fingerprints:
            return {"status": "skipped", "track_id": track_id}
        arrays, expected = {}, {}
        for index, fingerprint in enumerate(fingerprints):
            raw = fingerprint.get("raw_features", {})
            for field in RAW_ARRAY_FIELDS:
                values = raw.get(field, [])
                key = f"segment_{index}/{field}"
                arrays[key] = values
                expected[key] = values
            fingerprint["display_features"] = {
                "rms": resample(raw.get("rms", []), DISPLAY_BINS),
                "onset_strength": resample(raw.get("onset_strength", []), DISPLAY_BINS),
            }
            fingerprint["temporal_features"] = {
                field: resample(raw.get(field, []), TEMPORAL_BINS)
                for field in TEMPORAL_FIELDS
            }
            fingerprint["raw_features"] = {
                "lufs": raw.get("lufs"),
                "sidecar_segment": index,
            }
        analysis["rawFeatureStore"] = {
            "version": VERSION,
            "format": "npz",
            "path": f"raw_features/{track_id}.npz",
            "displayBins": DISPLAY_BINS,
            "temporalBins": TEMPORAL_BINS,
        }
        document["analysis"] = analysis
        return {
            "status": "migrated", "track_id": track_id, "arrays": arrays,
            "expected": expected,
        }

    def _write_sidecar(self, path, arrays):
        import numpy as np
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=f".{path.stem}-", suffix=".npz", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                np.savez_compressed(handle, **{key: np.asarray(values) for key, values in arrays.items()})
            Path(temporary).replace(path)
        except Exception:
            Path(temporary).unlink(missing_ok=True)
            raise

    @staticmethod
    def _verify_sidecar(path, expected):
        import numpy as np
        with np.load(path, allow_pickle=False) as sidecar:
            if set(sidecar.files) != set(expected):
                raise ValueError("raw-feature sidecar keys do not match")
            for key, values in expected.items():
                if not np.array_equal(sidecar[key], np.asarray(values)):
                    raise ValueError(f"raw-feature sidecar verification failed for {key}")

    @staticmethod
    def _atomic_json_write(path, document):
        encoded = json.dumps(document, indent=4, ensure_ascii=False)
        temporary = path.with_suffix(f"{path.suffix}.tmp")
        temporary.write_text(encoded, encoding="utf-8")
        temporary.replace(path)
