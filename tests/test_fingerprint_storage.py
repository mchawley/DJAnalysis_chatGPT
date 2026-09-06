import json
import tempfile
import unittest
from pathlib import Path

from modules.fingerprint.normalization import FingerprintNormalizer
from modules.fingerprint.storage import FingerprintCompactor, load_raw_features


def document(track_id="track"):
    return {
        "system": {"trackId": track_id},
        "analysis": {"fingerprints": [{
            "segment": "GROOVE", "raw_features": {
                "rms": [.1, .2, .3], "lufs": -12.0,
                "mfcc": [[1.0, 2.0], [3.0, 4.0]], "chroma": [[.2, .4]],
                "spectral_contrast": [[.1, .3]], "tonnetz": [[.4, .5]],
                "zero_crossing_rate": [.01, .02], "spectral_flux": [.3, .4],
                "onset_strength": [.5, .6], "beat_positions": [0.0, .5],
            },
        }]},
    }


class FingerprintStorageTest(unittest.TestCase):
    def test_compaction_preserves_exact_raw_arrays_and_compact_vectors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "output" / "tracks"; root.mkdir(parents=True)
            path = root / "track.json"; source = document(); path.write_text(json.dumps(source))
            before = FingerprintNormalizer().temporal(source["analysis"]["fingerprints"][0])
            result = FingerprintCompactor(root).compact_path(path)
            compact = json.loads(path.read_text())
            fingerprint = compact["analysis"]["fingerprints"][0]
            self.assertEqual(result["status"], "migrated")
            self.assertEqual(compact["analysis"]["rawFeatureStore"]["format"], "npz")
            self.assertEqual(fingerprint["raw_features"], {"lufs": -12.0, "sidecar_segment": 0})
            self.assertEqual(len(fingerprint["display_features"]["rms"]), 120)
            self.assertEqual(FingerprintNormalizer().temporal(fingerprint), before)
            self.assertEqual(load_raw_features(compact, fingerprint, root)["beat_positions"], [0.0, .5])
            import numpy as np
            with np.load(root.parent / "raw_features" / "track.npz", allow_pickle=False) as sidecar:
                self.assertTrue(np.array_equal(sidecar["segment_0/mfcc"], [[1.0, 2.0], [3.0, 4.0]]))
            self.assertEqual(FingerprintCompactor(root).compact_path(path)["status"], "already")

    def test_failed_sidecar_verification_leaves_main_document_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "output" / "tracks"; root.mkdir(parents=True)
            path = root / "track.json"; path.write_text(json.dumps(document()))
            original = path.read_text()
            compactor = FingerprintCompactor(root)
            compactor._verify_sidecar = lambda *_: (_ for _ in ()).throw(ValueError("bad sidecar"))
            with self.assertRaises(ValueError):
                compactor.compact_path(path)
            self.assertEqual(path.read_text(), original)
