from .models import RawAudioFeatures, Segment


class FingerprintExtractor:
    """Extract non-compressed raw audio features for one already-decoded segment."""

    def __init__(self, sample_rate: int, librosa_module=None, loudness_meter_factory=None):
        self.sample_rate = sample_rate; self.librosa_module = librosa_module; self.loudness_meter_factory = loudness_meter_factory

    def extract(self, audio, segment: Segment) -> RawAudioFeatures:
        import numpy as np
        librosa = self._librosa()
        start, end = round(segment.start_time * self.sample_rate), round(segment.end_time * self.sample_rate)
        y = audio[max(0, start):max(0, end)]
        if not len(y): return RawAudioFeatures()
        rms = librosa.feature.rms(y=y)[0]; onset = librosa.onset.onset_strength(y=y, sr=self.sample_rate)
        flux = np.maximum(0, np.diff(np.abs(librosa.stft(y)), axis=1)).sum(axis=0)
        try: lufs = float(self._meter().integrated_loudness(np.asarray(y, dtype=np.float64)))
        except ValueError: lufs = None
        return RawAudioFeatures(
            rms=rms.tolist(), lufs=lufs, mfcc=librosa.feature.mfcc(y=y, sr=self.sample_rate, n_mfcc=13).tolist(),
            chroma=librosa.feature.chroma_stft(y=y, sr=self.sample_rate).tolist(),
            spectral_contrast=librosa.feature.spectral_contrast(y=y, sr=self.sample_rate).tolist(),
            tonnetz=librosa.feature.tonnetz(y=y, sr=self.sample_rate).tolist(),
            zero_crossing_rate=librosa.feature.zero_crossing_rate(y).tolist()[0], spectral_flux=flux.tolist(), onset_strength=onset.tolist(),
        )

    def _librosa(self):
        if self.librosa_module: return self.librosa_module
        import librosa
        return librosa
    def _meter(self):
        if self.loudness_meter_factory: return self.loudness_meter_factory(self.sample_rate)
        import pyloudnorm
        return pyloudnorm.Meter(self.sample_rate)
