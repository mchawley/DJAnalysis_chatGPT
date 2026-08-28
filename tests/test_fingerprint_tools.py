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
        engine.fit([target] + candidates)
        match = engine.nearest_neighbors(target, candidates)[0]
        self.assertEqual(match.track_id, "b")
        self.assertTrue(match.reasons)

    def test_excludes_all_segments_from_the_current_track(self):
        engine = FingerprintSimilarityEngine()
        target = {"track_id": "source", "segment_index": 0, "fingerprint": fingerprint()}
        candidates = [
            {"track_id": "source", "segment_index": 1, "fingerprint": fingerprint()},
            {"track_id": "other", "segment_index": 0, "fingerprint": fingerprint(0.5)},
        ]
        engine.fit([target] + candidates)

        matches = engine.nearest_neighbors(target, candidates)

        self.assertEqual([match.track_id for match in matches], ["other"])

    def test_beat_patterns_require_beats_and_return_binary_values(self):
        from modules.fingerprint.builder import FingerprintBuilder
        from modules.fingerprint.models import Segment
        import numpy as np

        builder = FingerprintBuilder(np.array([0.0, 1.0, 0.0, .5, 0.0, 1.0]), 4, beat_positions=[0.0, .5, 1.0])
        onset, kick = builder._beat_patterns(Segment("GROOVE", 0.0, 1.5))
        self.assertEqual(len(onset), 3)
        self.assertEqual(len(kick), 3)
        self.assertTrue(all(value in (0, 1) for value in onset + kick))
        self.assertEqual(FingerprintBuilder(np.array([0.0]), 4)._beat_patterns(Segment("GROOVE", 0.0, 1.0)), ([], []))

    def test_requires_rekordbox_phrases_and_beat_positions(self):
        from modules.fingerprint.plugin import FingerprintPlugin
        plugin = FingerprintPlugin()
        self.assertFalse(plugin.needs_processing({"analysis": {"phrases": [{}]}}))
        self.assertFalse(plugin.needs_processing({"analysis": {"beatPositions": [0.0]}}))
        self.assertTrue(plugin.needs_processing({"analysis": {"phrases": [{}], "beatPositions": [0.0]}}))

    def test_flags_missing_core_features(self):
        self.assertIn("energy.overall", FingerprintValidator().validate({}))
