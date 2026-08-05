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
        self.assertEqual(InsightsHandler._meter("Low", "High"), {"percent": 100, "tone": "high", "state": "High"})

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

    def test_html_uses_block_meter_fills_and_bounded_charts(self):
        self.assertIn(".fill{display:block", HTML)
        self.assertIn(".chart{height:155px;width:100%;overflow:hidden", HTML)
        self.assertIn(".chart svg{display:block;width:100%;height:100%}", HTML)

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

    def test_chart_summaries_describe_shapes(self):
        self.assertIn("builds", InsightsHandler._rms_summary([1, 1, 1, 2, 2, 2]))
        self.assertIn("eases", InsightsHandler._rms_summary([2, 2, 2, 1, 1, 1]))
        self.assertIn("steady", InsightsHandler._rms_summary([1, 1, 1, 1, 1, 1]))
        self.assertIn("accented", InsightsHandler._onset_summary([1, 1, 1, 3, 1, 3, 1, 3, 1, 3, 1, 3]))
        self.assertIn("pronounced", InsightsHandler._onset_summary([1, 1, 1, 1, 1, 5]))
