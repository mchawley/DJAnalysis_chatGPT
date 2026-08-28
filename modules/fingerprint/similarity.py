from dataclasses import dataclass
from math import sqrt
from .normalization import FingerprintNormalizer


@dataclass
class SimilarityMatch:
    track_id: str
    segment_index: int
    score: float
    fingerprint: dict
    reasons: list[str]


class FingerprintSimilarityEngine:
    """Weighted cosine similarity across stable derived fingerprint features."""

    DEFAULT_WEIGHTS = {
        "tempo.bpm": 0.8, "energy.overall": 1.0, "energy.slope": 0.6,
        "bass.overall": 0.8, "bass.kick": 0.7, "rhythm.density": 0.7,
        "rhythm.groove": 0.5, "rhythm.syncopation": 0.5,
        "spectrum.spectral_centroid": 0.7, "spectrum.spectral_flatness": 0.5,
        "harmonic.key": 0.8,
    }

    def __init__(self, weights=None, normalizer=None):
        self.weights = weights or self.DEFAULT_WEIGHTS
        self.normalizer = normalizer or FingerprintNormalizer()

    def fit(self, candidates):
        self.normalizer.fit([candidate["fingerprint"] for candidate in candidates], self.weights)
        return self

    def nearest_neighbors(self, target, candidates, limit=10):
        """Return closest segments from other tracks only."""
        target_id = target.get("track_id")
        matches = []
        for candidate in candidates:
            if candidate.get("track_id") == target_id:
                continue
            score = self.score(target["fingerprint"], candidate["fingerprint"])
            if score is not None:
                matches.append(SimilarityMatch(candidate["track_id"], candidate["segment_index"], score, candidate["fingerprint"], self.explain(target["fingerprint"], candidate["fingerprint"])))
        return sorted(matches, key=lambda match: match.score, reverse=True)[:limit]

    def score(self, left, right):
        values = []
        for path, weight in self.weights.items():
            if path == "harmonic.key":
                compatibility = self._harmonic_score(left, right)
                if compatibility is not None: values.append((1.0, compatibility, weight))
                continue
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

    def explain(self, left, right, limit=3):
        labels = {"tempo.bpm": "similar tempo", "energy.overall": "similar energy", "energy.slope": "similar energy movement", "bass.overall": "similar bass level", "bass.kick": "similar kick intensity", "rhythm.density": "similar rhythmic density", "rhythm.groove": "similar groove", "rhythm.syncopation": "similar syncopation", "spectrum.spectral_centroid": "similar brightness", "spectrum.spectral_flatness": "similar texture"}
        matches = []
        for path in self.weights:
            a, b = self.normalizer.scalar(left, path), self.normalizer.scalar(right, path)
            if a is not None and b is not None:
                matches.append((abs(a - b), labels[path]))
        reasons = [label for _distance, label in sorted(matches)[:limit]]
        if self._harmonic_score(left, right) and len(reasons) < limit:
            reasons.append("compatible key")
        return reasons

    @staticmethod
    def _harmonic_score(left, right):
        left_key = left.get("harmonic", {}).get("camelot") or left.get("harmonic", {}).get("key")
        right_key = right.get("harmonic", {}).get("camelot") or right.get("harmonic", {}).get("key")
        if not left_key or not right_key: return None
        if left_key == right_key: return 1.0
        try:
            left_number, left_mode = int(str(left_key)[:-1]), str(left_key)[-1].upper()
            right_number, right_mode = int(str(right_key)[:-1]), str(right_key)[-1].upper()
        except ValueError: return 0.0
        if left_number == right_number and left_mode != right_mode: return 0.8
        if left_mode == right_mode and (left_number - right_number) % 12 in (1, 11): return 0.7
        return 0.0

    @staticmethod
    def _value(fingerprint, path):
        value = fingerprint
        for part in path.split("."):
            if not isinstance(value, dict): return None
            value = value.get(part)
        return value
