from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RekordboxAnalysis:
    location: str
    beat_positions: list[float] = field(default_factory=list)
    beat_numbers: list[int] = field(default_factory=list)
    bpms: list[float] = field(default_factory=list)
    waveform_preview: list[int] = field(default_factory=list)
    waveform_detail: list[int] = field(default_factory=list)
    phrases: list[dict] = field(default_factory=list)
    structure: dict = field(default_factory=dict)
    source_files: list[str] = field(default_factory=list)


class RekordboxAnlzParser:
    """Read Rekordbox ANLZ files through pyrekordbox without database access."""

    EXTENSIONS = {".DAT", ".EXT", ".2EX"}

    def __init__(self, anlz_file_class=None):
        self.anlz_file_class = anlz_file_class
        self.errors = []

    def parse_directory(self, root_path):
        root = Path(root_path)
        parser = self.anlz_file_class or self._load_parser()
        analyses = {}
        self.errors = []
        for file_path in sorted(root.rglob("ANLZ*")):
            if not file_path.is_file() or file_path.suffix.upper() not in self.EXTENSIONS:
                continue
            try:
                anlz = parser.parse_file(file_path)
                location = self._tag(anlz, "path")
                if not location:
                    continue
                analyses[str(location)] = self.extract(
                    anlz, location, file_path, analyses.get(str(location))
                )
            except Exception as error:
                self.errors.append((file_path, error))
                continue
        return analyses

    def extract(self, anlz, location, source_file, analysis=None):
        """Merge one parsed ANLZ object into a track analysis record."""
        analysis = analysis or RekordboxAnalysis(location=str(location))
        analysis.source_files.append(str(source_file))
        self._merge_beat_grid(
            analysis, self._tag(anlz, "beat_grid") or self._tag(anlz, "beat_grid2")
        )
        self._merge_waveform(analysis, self._tag(anlz, "wf_preview"), "waveform_preview")
        self._merge_waveform(analysis, self._tag(anlz, "wf_detail"), "waveform_detail")
        structure = self._tag(anlz, "structure")
        if structure is not None:
            analysis.structure = self._serialise(structure)
            analysis.phrases = self._extract_phrases(analysis.structure)
        return analysis

    @staticmethod
    def _load_parser():
        try:
            from pyrekordbox.anlz import AnlzFile
        except ImportError as error:
            raise RuntimeError(
                "ANLZ support requires pyrekordbox. Run: pip install -r requirements.txt"
            ) from error
        return AnlzFile

    @staticmethod
    def _tag(anlz, name):
        try:
            return anlz.get(name)
        except (KeyError, AttributeError):
            return None

    @staticmethod
    def _merge_beat_grid(analysis, beat_grid):
        if not beat_grid or analysis.beat_positions:
            return
        beats, bpms, positions = beat_grid
        analysis.beat_numbers = [int(value) for value in beats]
        analysis.bpms = [float(value) for value in bpms]
        analysis.beat_positions = [float(value) for value in positions]

    @staticmethod
    def _merge_waveform(analysis, waveform, attribute):
        if waveform is None or getattr(analysis, attribute):
            return
        samples = waveform[0] if isinstance(waveform, tuple) else waveform
        setattr(analysis, attribute, [int(value) for value in samples])

    @classmethod
    def _serialise(cls, value):
        if hasattr(value, "items"):
            return {str(key): cls._serialise(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [cls._serialise(item) for item in value]
        if hasattr(value, "tolist"):
            return cls._serialise(value.tolist())
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)

    @staticmethod
    def _extract_phrases(structure):
        entries = structure.get("entries", []) if isinstance(structure, dict) else []
        return [entry for entry in entries if isinstance(entry, dict)]
