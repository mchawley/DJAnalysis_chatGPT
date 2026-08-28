from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass
class Segment:
    segment_type: str
    start_time: float
    end_time: float
    bars: int = 0
    phrases: list[int] = field(default_factory=list)
    confidence: float = 0.0
    previous_segment: Optional[str] = None
    next_segment: Optional[str] = None
    bpm: Optional[float] = None
    key: Optional[str] = None

    @property
    def duration(self) -> float:
        return max(0.0, self.end_time - self.start_time)


@dataclass
class TempoFeatures:
    bpm: Optional[float] = None
    tempo_stability: Optional[float] = None
    swing: Optional[float] = None


@dataclass
class HarmonicFeatures:
    key: Optional[str] = None
    camelot: Optional[str] = None
    mode: Optional[str] = None
    confidence: Optional[float] = None


@dataclass
class EnergyFeatures:
    overall: float = 0.0; start: float = 0.0; end: float = 0.0; peak: float = 0.0
    minimum: float = 0.0; variance: float = 0.0; slope: float = 0.0; crest_factor: float = 0.0


@dataclass
class BassFeatures:
    overall: float = 0.0; sub: float = 0.0; kick: Optional[float] = None
    consistency: float = 0.0; transient_strength: Optional[float] = None; kick_pattern: list[int] = field(default_factory=list)


@dataclass
class RhythmFeatures:
    density: Optional[float] = None; groove: Optional[float] = None; syncopation: Optional[float] = None
    percussion_complexity: Optional[float] = None; beat_strength: Optional[float] = None; onset_pattern: list[int] = field(default_factory=list)


@dataclass
class SpectrumFeatures:
    brightness: float = 0.0; warmth: float = 0.0; air: float = 0.0; mid_presence: float = 0.0
    spectral_centroid: float = 0.0; spectral_rolloff: float = 0.0; spectral_bandwidth: float = 0.0
    spectral_flatness: float = 0.0


@dataclass
class VocalFeatures:
    presence: Optional[float] = None; density: Optional[float] = None
    male_probability: Optional[float] = None; female_probability: Optional[float] = None
    instrumental_probability: Optional[float] = None


@dataclass
class StructuralFeatures:
    segment_type: str; confidence: float; previous_segment: Optional[str] = None; next_segment: Optional[str] = None


@dataclass
class RawAudioFeatures:
    rms: list[float] = field(default_factory=list); lufs: Optional[float] = None
    mfcc: list[list[float]] = field(default_factory=list); chroma: list[list[float]] = field(default_factory=list)
    spectral_contrast: list[list[float]] = field(default_factory=list); tonnetz: list[list[float]] = field(default_factory=list)
    zero_crossing_rate: list[float] = field(default_factory=list); spectral_flux: list[float] = field(default_factory=list)
    onset_strength: list[float] = field(default_factory=list); beat_positions: list[float] = field(default_factory=list)


@dataclass
class Fingerprint:
    segment: str; start_time: float; end_time: float; duration: float; bars: int; phrases: list[int]
    tempo: TempoFeatures; harmonic: HarmonicFeatures; energy: EnergyFeatures; bass: BassFeatures
    rhythm: RhythmFeatures; spectrum: SpectrumFeatures; vocals: VocalFeatures; structure: StructuralFeatures
    raw_features: RawAudioFeatures

    def to_dict(self) -> dict:
        return asdict(self)
