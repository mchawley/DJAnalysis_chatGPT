# Sprint 3 Design Notes

Metadata extraction is now introduced.

Supported:
- MP3 (ID3)
- FLAC (Vorbis)
- WAV
- AIFF
- M4A / AAC / ALAC (MP4 atoms)

Recommendation:
Do NOT access Mutagen directly elsewhere.
Always go through MetadataExtractor so every format is normalized into
the same JSON schema.

Next pipeline step:

Scanner
    ↓
Registry
    ↓
MetadataExtractor
    ↓
JSON Manager
