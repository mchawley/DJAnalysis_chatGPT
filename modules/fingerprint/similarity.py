from dataclasses import dataclass
from math import sqrt


@dataclass
class SimilarityMatch:
    track_id: str
    segment_index: int
    score: float
    fingerprint: dict


class FingerprintSimilarityEngine:
    """Weighted cosine similarity across stable derived fingerprint features."""

    DEFAULT_WEIGHTS = {
        "tempo.bpm": 0.8, "energy.overall": 1.0, "energy.slope": 0.6,
        "bass.overall": 0.8, "bass.kick": 0.7, "rhythm.density": 0.7,
        "rhythm.groove": 0.5, "rhythm.syncopation": 0.5,
        "spectrum.spectral_centroid": 0.7, "spectrum.spectral_flatness": 0.5,
    }

    def __init__(self, weights=None):
        self.weights = weights or self.DEFAULT_WEIGHTS

    def nearest_neighbors(self, target, candidates, limit=10):
        """Return the closest segments, excluding the target itself."""
        target_id = target.get("track_id")
        target_segment = target.get("segment_index")
        matches = []
        for candidate in candidates:
            if candidate.get("track_id") == target_id and candidate.get("segment_index") == target_segment:
                continue
            score = self.score(target["fingerprint"], candidate["fingerprint"])
            if score is not None:
                matches.append(SimilarityMatch(candidate["track_id"], candidate["segment_index"], score, candidate["fingerprint"]))
        return sorted(matches, key=lambda match: match.score, reverse=True)[:limit]

    def score(self, left, right):
        values = []
        for path, weight in self.weights.items():
            a, b = self._value(left, path), self._value(right, path)
            if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                values.append((float(a), float(b), weight))
        if not values:
            return None
        dot = sum(a * b * weight for a, b, weight in values)
        left_norm = sqrt(sum(a * a * weight for a, _b, weight in values))
        right_norm = sqrt(sum(b * b * weight for _a, b, weight in values))
        return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0

    @staticmethod
    def _value(fingerprint, path):
        value = fingerprint
        for part in path.split("."):
            if not isinstance(value, dict): return None
            value = value.get(part)
        return value
