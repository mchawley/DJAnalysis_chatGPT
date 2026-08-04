import math
import statistics

from .extractor import FingerprintExtractor
from .models import (BassFeatures, EnergyFeatures, Fingerprint, HarmonicFeatures,
                     RhythmFeatures, Segment, SpectrumFeatures, StructuralFeatures,
                     TempoFeatures, VocalFeatures)


class FingerprintBuilder:
    """Build same-schema fingerprints from one decoded track audio buffer."""

    def __init__(self, audio, sample_rate: int, extractor=None, beat_positions=None):
        self.audio = audio; self.sample_rate = sample_rate; self.extractor = extractor or FingerprintExtractor(sample_rate)
        self.beat_positions = beat_positions or []

    def build(self, segment: Segment) -> Fingerprint:
        raw = self.extractor.extract(self.audio, segment)
        raw.beat_positions = [p for p in self.beat_positions if segment.start_time <= p < segment.end_time]
        rms = raw.rms or [0.0]; overall = statistics.fmean(rms); peak = max(rms); minimum = min(rms)
        start, end = rms[0], rms[-1]; variance = statistics.pvariance(rms) if len(rms) > 1 else 0.0
        slope = (end - start) / segment.duration if segment.duration else 0.0
        crest = peak / overall if overall else 0.0
        centroid = self._mean_feature("spectral_centroid", segment); spectrum = SpectrumFeatures(
            brightness=centroid, warmth=0.0, air=0.0, mid_presence=0.0, spectral_centroid=centroid,
            spectral_rolloff=self._mean_feature("spectral_rolloff", segment), spectral_bandwidth=self._mean_feature("spectral_bandwidth", segment),
            spectral_flatness=self._mean_feature("spectral_flatness", segment))
        bass = self._bass(segment)
        return Fingerprint(segment=segment.segment_type, start_time=segment.start_time, end_time=segment.end_time,
            duration=segment.duration, bars=segment.bars, phrases=segment.phrases,
            tempo=TempoFeatures(bpm=segment.bpm), harmonic=HarmonicFeatures(key=segment.key, camelot=segment.key),
            energy=EnergyFeatures(overall, start, end, peak, minimum, variance, slope, crest), bass=bass,
            rhythm=RhythmFeatures(density=statistics.fmean(raw.onset_strength) if raw.onset_strength else 0.0), spectrum=spectrum,
            vocals=VocalFeatures(), structure=StructuralFeatures(segment.segment_type, segment.confidence, segment.previous_segment, segment.next_segment), raw_features=raw)

    def _mean_feature(self, name, segment):
        try:
            function = getattr(self.extractor._librosa().feature, name)
            kwargs = {"y": self._segment(segment)}
            if name != "spectral_flatness":
                kwargs["sr"] = self.sample_rate
            values = function(**kwargs)
            return float(values.mean())
        except AttributeError: return 0.0

    def _bass(self, segment):
        import numpy as np
        y = self._segment(segment)
        if not len(y): return BassFeatures()
        power = np.abs(np.fft.rfft(y)) ** 2; frequencies = np.fft.rfftfreq(len(y), 1 / self.sample_rate); total = power.sum()
        ratio = lambda low, high: float(power[(frequencies >= low) & (frequencies < high)].sum() / total) if total else 0.0
        return BassFeatures(overall=ratio(0, 200), sub=ratio(20, 60), consistency=0.0)

    def _segment(self, segment):
        return self.audio[round(segment.start_time * self.sample_rate):round(segment.end_time * self.sample_rate)]
