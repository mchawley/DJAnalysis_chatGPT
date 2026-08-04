import unittest

from modules.fingerprint.similarity import FingerprintSimilarityEngine
from modules.fingerprint.validation import FingerprintValidator


def fingerprint(energy=0.5):
    return {"tempo": {"bpm": 120}, "energy": {"overall": energy, "slope": 0.1}, "bass": {"overall": 0.4, "kick": 0.3}, "rhythm": {"density": 0.2, "groove": 0.2, "syncopation": 0.1}, "spectrum": {"spectral_centroid": 1200, "spectral_flatness": 0.2}}


class FingerprintToolsTest(unittest.TestCase):
    def test_returns_closest_fingerprint_first(self):
        engine = FingerprintSimilarityEngine()
        target = {"track_id": "a", "segment_index": 0, "fingerprint": fingerprint()}
        candidates = [{"track_id": "b", "segment_index": 0, "fingerprint": fingerprint(0.5)}, {"track_id": "c", "segment_index": 0, "fingerprint": fingerprint(0.1)}]
        self.assertEqual(engine.nearest_neighbors(target, candidates)[0].track_id, "b")

    def test_flags_missing_core_features(self):
        self.assertIn("energy.overall", FingerprintValidator().validate({}))
