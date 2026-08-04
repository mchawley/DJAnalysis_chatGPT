from dataclasses import dataclass
from math import sqrt
from .normalization import FingerprintNormalizer


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

    def __init__(self, weights=None, normalizer=None):
        self.weights = weights or self.DEFAULT_WEIGHTS
        self.normalizer = normalizer or FingerprintNormalizer()

    def fit(self, candidates):
        self.normalizer.fit([candidate["fingerprint"] for candidate in candidates], self.weights)
        return self

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
            a, b = self.normalizer.scalar(left, path), self.normalizer.scalar(right, path)
            if a is not None and b is not None: values.append((a, b, weight))
        temporal_left, temporal_right = self.normalizer.temporal(left), self.normalizer.temporal(right)
        values.extend((a, b, 0.35) for a, b in zip(temporal_left, temporal_right))
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
