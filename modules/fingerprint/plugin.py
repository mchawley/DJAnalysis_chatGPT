from datetime import datetime, timezone

from .builder import FingerprintBuilder
from .models import Segment


class FingerprintPlugin:
    NAME = "fingerprint"; VERSION = "1.4"
    KIND_TYPES = {1: "INTRO", 2: "GROOVE", 3: "BUILD", 4: "DROP", 5: "BREAKDOWN", 6: "OUTRO"}

    def needs_processing(self, document):
        status = document.get("system", {}).get("modules", {}).get(self.NAME, {})
        analysis = document.get("analysis", {})
        has_segments = bool(analysis.get("phrases")) and bool(analysis.get("beatPositions"))
        return has_segments and not (status.get("completed") and status.get("version") == self.VERSION)

    def process(self, document, path):
        document.setdefault("analysis", {})["fingerprints"] = build_fingerprints(
            path, document["analysis"], document.get("library", {})
        )
        self.mark_complete(document)

    def mark_complete(self, document):
        document.setdefault("system", {}).setdefault("modules", {})[self.NAME] = {"version": self.VERSION, "completed": True, "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}

    def _segments(self, analysis, library):
        return self.segments(analysis, library)

    @classmethod
    def segments(cls, analysis, library):
        positions = analysis.get("beatPositions", []); phrases = analysis.get("phrases", []); end_beat = analysis.get("structure", {}).get("endBeat")
        segments = []
        for index, phrase in enumerate(phrases):
            start_beat = phrase.get("startBeat"); finish_beat = phrases[index + 1].get("startBeat") if index + 1 < len(phrases) else end_beat
            if not all(isinstance(value, int) and 1 <= value <= len(positions) for value in (start_beat, finish_beat)): continue
            segment_type = cls.KIND_TYPES.get(phrase.get("kind"), "CUSTOM")
            segments.append(Segment(segment_type, positions[start_beat - 1], positions[finish_beat - 1], bars=max(0, (finish_beat - start_beat) // 4), phrases=[phrase.get("index", index + 1)], confidence=0.6, previous_segment=segments[-1].segment_type if segments else None, bpm=library.get("bpm"), key=library.get("key")))
        for index, segment in enumerate(segments[:-1]): segment.next_segment = segments[index + 1].segment_type
        return segments


def build_fingerprints(path, analysis, library):
    """Worker-safe function: decode one track and return its fingerprints."""
    import librosa
    audio, sample_rate = librosa.load(path, sr=None, mono=True)
    segments = FingerprintPlugin.segments(analysis, library)
    builder = FingerprintBuilder(audio, sample_rate, beat_positions=analysis.get("beatPositions", []))
    return [builder.build(segment).to_dict() for segment in segments]
