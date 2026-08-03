from .anlz import RekordboxAnalysis


class RekordboxAnalysisImporter:
    """Copy Rekordbox musical analysis into a document's analysis section only."""

    def import_analysis(self, document, analysis: RekordboxAnalysis):
        section = document.setdefault("analysis", {})
        section.update(
            {
                "provider": "rekordbox",
                "beatPositions": analysis.beat_positions,
                "beatNumbers": analysis.beat_numbers,
                "bpms": analysis.bpms,
                "waveformPreview": analysis.waveform_preview,
                "waveformDetail": analysis.waveform_detail,
                "phrases": analysis.phrases,
                "structure": analysis.structure,
                "sourceFiles": analysis.source_files,
            }
        )
        return document
