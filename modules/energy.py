import math


class EnergyExtractor:
    """Calculate audio features for Rekordbox-defined phrase boundaries."""

    BASS_CUTOFF_HZ = 200

    def __init__(self, audio_loader=None, librosa_module=None, loudness_meter_factory=None):
        self.audio_loader = audio_loader
        self.librosa_module = librosa_module
        self.loudness_meter_factory = loudness_meter_factory

    def extract(self, path, analysis):
        phrases = analysis.get("phrases", [])
        if not phrases:
            return {"provider": "cratiq", "version": "1.1", "phrases": []}

        audio, sample_rate = self._load_audio(path)
        meter = self._loudness_meter(sample_rate)
        beat_positions = analysis.get("beatPositions", [])
        end_beat = analysis.get("structure", {}).get("endBeat")
        result = []

        for index, phrase in enumerate(phrases):
            start_beat = phrase.get("startBeat")
            next_phrase = phrases[index + 1] if index + 1 < len(phrases) else None
            end = next_phrase.get("startBeat") if next_phrase else end_beat
            start_seconds = self._beat_time(beat_positions, start_beat)
            end_seconds = self._beat_time(beat_positions, end)
            if start_seconds is None or end_seconds is None or end_seconds <= start_seconds:
                continue
            segment = audio[
                max(0, round(start_seconds * sample_rate)):
                min(len(audio), round(end_seconds * sample_rate))
            ]
            if not len(segment):
                continue
            result.append({
                "index": phrase.get("index"),
                "kind": phrase.get("kind"),
                "startBeat": start_beat,
                "endBeat": end,
                "startSeconds": round(float(start_seconds), 3),
                "endSeconds": round(float(end_seconds), 3),
                **self._features(segment, sample_rate, meter),
            })

        return {"provider": "cratiq", "version": "1.1", "phrases": result}

    @staticmethod
    def _beat_time(beat_positions, absolute_beat):
        """PQTZ beat values are bar-relative; array position is the absolute beat."""
        if not isinstance(absolute_beat, int) or not 1 <= absolute_beat <= len(beat_positions):
            return None
        return beat_positions[absolute_beat - 1]

    def _load_audio(self, path):
        if self.audio_loader:
            return self.audio_loader(path)
        librosa = self._librosa()
        return librosa.load(path, sr=None, mono=True)

    def _features(self, segment, sample_rate, meter):
        import numpy as np

        rms = float(np.sqrt(np.mean(np.square(segment))))
        peak = float(np.max(np.abs(segment)))
        spectrum = np.abs(np.fft.rfft(segment)) ** 2
        frequencies = np.fft.rfftfreq(len(segment), d=1 / sample_rate)
        total_energy = float(np.sum(spectrum))
        bass_energy = (
            float(np.sum(spectrum[frequencies <= self.BASS_CUTOFF_HZ])) / total_energy
            if total_energy else 0.0
        )
        centroid = float(self._librosa().feature.spectral_centroid(y=segment, sr=sample_rate).mean())
        try:
            lufs = float(meter.integrated_loudness(segment))
        except ValueError:
            lufs = None
        dynamic_range = 20 * math.log10(peak / rms) if rms and peak else 0.0
        return {
            "rms": round(rms, 6),
            "lufs": round(lufs, 3) if lufs is not None else None,
            "spectralCentroidHz": round(centroid, 3),
            "bassEnergy": round(bass_energy, 6),
            "dynamicRangeDb": round(dynamic_range, 3),
        }

    def _librosa(self):
        if self.librosa_module is not None:
            return self.librosa_module
        try:
            import librosa
        except ImportError as error:
            raise RuntimeError("Energy analysis requires librosa. Run: pip install -r requirements.txt") from error
        return librosa

    def _loudness_meter(self, sample_rate):
        if self.loudness_meter_factory:
            return self.loudness_meter_factory(sample_rate)
        try:
            import pyloudnorm
        except ImportError as error:
            raise RuntimeError("Energy analysis requires pyloudnorm. Run: pip install -r requirements.txt") from error
        return pyloudnorm.Meter(sample_rate)
