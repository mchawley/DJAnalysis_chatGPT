import unittest

from models.track import Track
from modules.energy_plugin import EnergyPlugin


class EnergyPluginTest(unittest.TestCase):
    def test_processes_rekordbox_phrase_data_without_touching_analysis(self):
        class Extractor:
            def extract(self, path, analysis):
                self.path = path
                self.analysis = analysis
                return {"provider": "cratiq", "version": "1.0", "phrases": [{"rms": 0.2}]}

        extractor = Extractor()
        plugin = EnergyPlugin(extractor)
        track = Track("/music/track.mp3", "track.mp3", ".mp3")
        document = {"analysis": {"phrases": [{"startBeat": 1}]}}

        self.assertTrue(plugin.needs_processing(document, track))
        plugin.process(document, track)

        self.assertEqual(extractor.path, track.path)
        self.assertEqual(document["analysis"]["phrases"], [{"startBeat": 1}])
        self.assertEqual(document["energy"]["phrases"][0]["rms"], 0.2)
        self.assertTrue(document["system"]["modules"]["energy"]["completed"])
        self.assertFalse(plugin.needs_processing(document, track))

    def test_skips_tracks_without_rekordbox_phrases(self):
        plugin = EnergyPlugin()
        track = Track("/music/track.mp3", "track.mp3", ".mp3")

        self.assertFalse(plugin.needs_processing({"analysis": {}}, track))
