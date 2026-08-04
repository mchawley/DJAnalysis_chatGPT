from statistics import median


class FingerprintNormalizer:
    """Versioned robust scalar and fixed-length temporal normalization."""
    VERSION = "1.0"
    TEMPORAL_FIELDS = ("rms", "onset_strength", "spectral_flux", "zero_crossing_rate")

    def __init__(self, bins=32, profile=None):
        self.bins = bins
        self.profile = profile or {}

    def fit(self, fingerprints, paths):
        self.profile = {}
        for path in paths:
            values = [self._value(fingerprint, path) for fingerprint in fingerprints]
            values = sorted(float(value) for value in values if isinstance(value, (int, float)))
            if not values:
                continue
            low, high = values[len(values) // 4], values[(len(values) * 3) // 4]
            self.profile[path] = {"median": median(values), "iqr": max(high - low, 1e-9)}
        return self

    def scalar(self, fingerprint, path):
        value, stats = self._value(fingerprint, path), self.profile.get(path)
        if not isinstance(value, (int, float)) or not stats:
            return None
        return max(-3.0, min(3.0, (float(value) - stats["median"]) / stats["iqr"]))

    def temporal(self, fingerprint):
        raw = fingerprint.get("raw_features", {})
        return [value for field in self.TEMPORAL_FIELDS for value in self._resample(raw.get(field, []))]

    def to_dict(self):
        return {"version": self.VERSION, "bins": self.bins, "profile": self.profile}

    @classmethod
    def from_dict(cls, data):
        return cls(data.get("bins", 32), data.get("profile", {}))

    def _resample(self, values):
        if not values: return [0.0] * self.bins
        if len(values) == 1: return [float(values[0])] * self.bins
        result = []
        for index in range(self.bins):
            position = index * (len(values) - 1) / max(self.bins - 1, 1); left = int(position); right = min(left + 1, len(values) - 1)
            result.append(float(values[left]) + (float(values[right]) - float(values[left])) * (position - left))
        scale = max(max(abs(value) for value in result), 1e-9)
        return [value / scale for value in result]

    @staticmethod
    def _value(fingerprint, path):
        value = fingerprint
        for part in path.split("."):
            value = value.get(part) if isinstance(value, dict) else None
        return value
