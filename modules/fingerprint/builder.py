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
        onset_pattern, kick_pattern = self._beat_patterns(segment)
        bass.kick_pattern = kick_pattern
        onset = raw.onset_strength or [0.0]
        beat_strength = self._beat_strength(onset, raw.beat_positions)
        rhythm = RhythmFeatures(density=len(onset) / max(segment.duration, 1), groove=self._groove(onset),
            syncopation=self._syncopation(onset, raw.beat_positions), percussion_complexity=statistics.pstdev(onset) if len(onset) > 1 else 0.0,
            beat_strength=beat_strength, onset_pattern=onset_pattern)
        mode = "minor" if segment.key and segment.key.upper().endswith("A") else "major" if segment.key else None
        return Fingerprint(segment=segment.segment_type, start_time=segment.start_time, end_time=segment.end_time,
            duration=segment.duration, bars=segment.bars, phrases=segment.phrases,
            tempo=TempoFeatures(bpm=segment.bpm, tempo_stability=self._tempo_stability(raw.beat_positions), swing=self._swing(onset, raw.beat_positions)), harmonic=HarmonicFeatures(key=segment.key, camelot=segment.key, mode=mode, confidence=1.0 if segment.key else 0.0),
            energy=EnergyFeatures(overall, start, end, peak, minimum, variance, slope, crest), bass=bass,
            rhythm=rhythm, spectrum=spectrum,
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
        low = ratio(20, 150); envelope = np.abs(y); transient = float(np.max(np.diff(envelope, prepend=envelope[0])))
        return BassFeatures(overall=ratio(0, 200), sub=ratio(20, 60), kick=low, consistency=1 - min(1, float(np.std(envelope) / (np.mean(envelope) + 1e-9))), transient_strength=transient)

    def _beat_patterns(self, segment):
        """Binary onset and low-frequency kick activity at Rekordbox beat positions."""
        import numpy as np
        beats = [beat for beat in self.beat_positions if segment.start_time <= beat < segment.end_time]
        if not beats:
            return [], []
        onset_scores, kick_scores = [], []
        for index, beat in enumerate(beats):
            end = beats[index + 1] if index + 1 < len(beats) else min(segment.end_time, beat + .5)
            audio = self.audio[round(beat * self.sample_rate):round(end * self.sample_rate)]
            if len(audio) < 2:
                onset_scores.append(0.0); kick_scores.append(0.0); continue
            onset_scores.append(float(np.mean(np.abs(np.diff(audio)))))
            power = np.abs(np.fft.rfft(audio)) ** 2
            frequencies = np.fft.rfftfreq(len(audio), 1 / self.sample_rate)
            total = power.sum()
            kick_scores.append(float(power[(frequencies >= 20) & (frequencies < 150)].sum() / total) if total else 0.0)
        def binary(scores):
            threshold = float(np.median(scores))
            return [int(score > threshold and score > 0) for score in scores]
        return binary(onset_scores), binary(kick_scores)

    @staticmethod
    def _tempo_stability(beats):
        if len(beats) < 3: return 0.0
        intervals = [b - a for a, b in zip(beats, beats[1:])]
        return max(0.0, 1 - statistics.pstdev(intervals) / (statistics.fmean(intervals) + 1e-9))
    @staticmethod
    def _groove(onset):
        return 1 - min(1.0, statistics.pstdev(onset) / (statistics.fmean(onset) + 1e-9)) if len(onset) > 1 else 0.0
    @staticmethod
    def _syncopation(onset, beats):
        return min(1.0, statistics.pstdev(onset) / (max(onset) + 1e-9)) if beats else 0.0
    @staticmethod
    def _swing(onset, beats):
        return min(1.0, statistics.pstdev(onset) / (statistics.fmean(onset) + 1e-9)) if beats and len(onset) > 1 else 0.0
    @staticmethod
    def _beat_strength(onset, beats):
        return statistics.fmean(onset) if beats else 0.0

    def _segment(self, segment):
        return self.audio[round(segment.start_time * self.sample_rate):round(segment.end_time * self.sample_rate)]
