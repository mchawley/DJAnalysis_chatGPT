import json
import tempfile
import unittest
from pathlib import Path

from ui import HTML, InsightsHandler


class InsightsHandlerTest(unittest.TestCase):
    def test_downsamples_chart_data_to_fixed_size(self):
        values = list(range(500))
        result = InsightsHandler._downsample(values, 25)
        self.assertEqual(len(result), 25)
        self.assertEqual(result[0], 0.0)
        self.assertEqual(result[-1], 499.0)

    def test_range_meter_prefers_absolute_label(self):
        self.assertEqual(InsightsHandler._meter("Low", "High"), {"percent": 100, "tone": "high", "state": "High", "track": {"state": "Low", "tone": "low"}, "absolute": {"state": "High", "tone": "high"}})

    def test_absolute_labels_cover_profile_metrics(self):
        self.assertEqual(InsightsHandler._absolute_label("transient", 0.12), "Mid")
        self.assertEqual(InsightsHandler._absolute_label("groove", 0.1), "Low")
        self.assertEqual(InsightsHandler._absolute_label("syncopation", 0.9), "High")
        self.assertEqual(InsightsHandler._absolute_label("slope", -0.01), "Falling")
        self.assertEqual(InsightsHandler._absolute_label("crest", 1.5), "Balanced")

    def test_meter_uses_distinct_visual_states(self):
        self.assertEqual(InsightsHandler._meter("Low", "Low")["tone"], "low")
        self.assertEqual(InsightsHandler._meter("Mid", "Mid")["percent"], 66)
        self.assertEqual(InsightsHandler._meter("High", "High")["percent"], 100)
        self.assertEqual(InsightsHandler._meter("—", "—")["tone"], "neutral")

    def test_equal_track_values_are_not_ranked_high(self):
        fingerprints = [{"energy": {"overall": 0.0}}] * 3
        self.assertEqual(InsightsHandler._range_label(fingerprints[0], fingerprints, "energy.overall"), "Even")

    def test_waveform_prefers_detail_and_normalizes_samples(self):
        waveform = InsightsHandler._waveform_view({"waveformPreview": [1, 2], "waveformDetail": [2, 4, 8]})
        self.assertTrue(waveform["available"])
        self.assertEqual(waveform["source"], "detail")
        self.assertEqual(waveform["samples"], [0.25, 0.5, 1.0])
        self.assertEqual(InsightsHandler._waveform_view({})["available"], False)

    def test_camelot_and_segment_envelope_views(self):
        self.assertEqual(InsightsHandler._camelot("D minor"), "7A")
        self.assertEqual(InsightsHandler._camelot("Dm"), "7A")
        self.assertEqual(InsightsHandler._camelot("C# major"), "3B")
        self.assertEqual(InsightsHandler._camelot("8a"), "8A")
        envelope = InsightsHandler._envelope([{"start_time": 0, "end_time": 10, "energy": {"overall": .2}, "bass": {"overall": .3}}])
        self.assertEqual(envelope, [{"start": 0, "end": 10, "energy": .2, "bass": .3}])

    def test_html_uses_block_meter_fills_and_bounded_charts(self):
        self.assertIn(".fill{display:block", HTML)
        self.assertIn(".chart{height:155px;width:100%;overflow:hidden", HTML)
        self.assertIn(".chart svg{display:block;width:100%;height:100%}", HTML)
        self.assertIn(".waveform{position:relative;height:80px", HTML)
        self.assertIn("Track: ${meter.track.state}", HTML)

    def test_catalog_returns_manifest_title_and_artist_with_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            output_root = Path(directory) / "output" / "tracks"
            output_root.mkdir(parents=True)
            manifest = output_root.parent / "tracks_manifest.json"
            manifest.write_text(json.dumps({"tracks": {
                "new": {"path": "/music/Filename Song.mp3", "title": "Document Title", "artist": "Known Artist"},
                "old": {"path": "/music/Fallback Song.mp3"},
            }}))
            original = InsightsHandler.output_root
            try:
                InsightsHandler.output_root = output_root
                catalog = InsightsHandler._catalog(InsightsHandler)
            finally:
                InsightsHandler.output_root = original
        self.assertIn({"id": "new", "title": "Document Title", "artist": "Known Artist"}, catalog)
        self.assertIn({"id": "old", "title": "Fallback Song", "artist": ""}, catalog)

    def test_html_includes_keyboard_search_picker(self):
        self.assertIn('id="track-search"', HTML)
        self.assertIn("ArrowDown", HTML)
        self.assertIn("No tracks match this search.", HTML)
        self.assertIn("search.addEventListener('focus',()=>showResults(true))", HTML)
        self.assertIn("padStart(2,'0')", HTML)
        self.assertNotIn("● Rhythm", HTML)

    def test_html_supports_preview_then_promote_similarity_workflow(self):
        self.assertIn('id="comparison"', HTML)
        self.assertIn("function previewMatch", HTML)
        self.assertIn("node.addEventListener('click',()=>previewMatch", HTML)
        self.assertIn("node.addEventListener('dblclick',()=>chooseTrack", HTML)
        self.assertIn("function comparisonTimeline", HTML)

    def test_playlist_ui_uses_separate_smoothed_charts_and_real_badge_labels(self):
        from modules.playlist_ui import PLAYLIST_HTML
        self.assertIn('id="charts" class="charts"', PLAYLIST_HTML)
        self.assertIn("function smoothPath", PLAYLIST_HTML)
        self.assertIn("function featureGradient", PLAYLIST_HTML)
        self.assertIn("function curveBias", PLAYLIST_HTML)
        self.assertIn("length-.5)*12", PLAYLIST_HTML)
        self.assertIn("detail?.tracks?.[index]?.duration", PLAYLIST_HTML)
        self.assertIn("cyan = low · amber = medium · coral = high", PLAYLIST_HTML)
        self.assertIn("['energy','bass','rhythm','brightness'].includes(key)", PLAYLIST_HTML)
        self.assertIn('url(#playlist-${key}-${index})', PLAYLIST_HTML)
        self.assertIn('stroke-width="6"', PLAYLIST_HTML)
        self.assertIn("raw_trends", Path("ui.py").read_text(encoding="utf-8"))
        self.assertIn("`<span class=\"badge ok\">${esc(item.label)}</span>`", PLAYLIST_HTML)
        self.assertNotIn("Smoothed display; every track is retained", PLAYLIST_HTML)
        self.assertIn('r="16" fill="transparent"', PLAYLIST_HTML)
        self.assertIn('`${track.title||`Track ${index+1}`}: ${fmt(raw[index])}${units}`', PLAYLIST_HTML)

    def test_playlist_ui_uses_phase_a_colored_segment_strips_without_global_flow(self):
        from modules.playlist_ui import PLAYLIST_HTML
        self.assertIn("function segmentStrip", PLAYLIST_HTML)
        self.assertIn('class="segment-strip"', PLAYLIST_HTML)
        self.assertIn('data-energy="${level}"', PLAYLIST_HTML)
        self.assertIn('.segment[data-energy="low"]', PLAYLIST_HTML)
        self.assertNotIn('id="toggle-flow"', PLAYLIST_HTML)
        self.assertNotIn("function playlistSegmentCurve", PLAYLIST_HTML)
        self.assertIn("segment_index=${node.dataset.segment}", PLAYLIST_HTML)

    def test_pattern_summary_returns_one_dominant_four_beat_bar(self):
        summary = InsightsHandler._pattern_summary([1, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0, 0])
        self.assertEqual(summary["pattern"], [1, 0, 0, 1])
        self.assertEqual(summary["bars"], 3)
        self.assertEqual(summary["consistency"], 67)
        self.assertFalse(InsightsHandler._pattern_summary([1, 0])["available"])

    def test_html_renders_compact_beat_summary_not_raw_beat_strings(self):
        self.assertIn("Dominant activity per four-beat bar", HTML)
        self.assertIn("function beatSummary", HTML)
        self.assertNotIn("function pattern(values)", HTML)

    def test_chart_summaries_describe_shapes(self):
        self.assertIn("builds", InsightsHandler._rms_summary([1, 1, 1, 2, 2, 2]))
        self.assertIn("eases", InsightsHandler._rms_summary([2, 2, 2, 1, 1, 1]))
        self.assertIn("steady", InsightsHandler._rms_summary([1, 1, 1, 1, 1, 1]))
        self.assertIn("accented", InsightsHandler._onset_summary([1, 1, 1, 3, 1, 3, 1, 3, 1, 3, 1, 3]))
        self.assertIn("pronounced", InsightsHandler._onset_summary([1, 1, 1, 1, 1, 5]))
