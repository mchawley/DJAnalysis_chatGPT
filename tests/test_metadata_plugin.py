import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from models.track import Track
from modules.json_manager import JsonManager
from modules.metadata import MetadataExtractor
from modules.metadata_plugin import MetadataPlugin
from modules.pipeline import Pipeline


class FakeExtractor:
    def extract(self, path):
        return {"title": "Example", "source": path}


class MetadataPluginTest(unittest.TestCase):
    def setUp(self):
        self.plugin = MetadataPlugin(extractor=FakeExtractor())
        self.track = Track("/music/example.mp3", "example.mp3", ".mp3")

    def test_processes_document_without_metadata(self):
        document = {"metadata": {}, "system": {"modules": {}}}

        self.assertTrue(self.plugin.needs_processing(document, self.track))
        self.plugin.process(document, self.track)

        self.assertEqual(document["metadata"]["title"], "Example")
        status = document["system"]["modules"]["metadata"]
        self.assertEqual(status["version"], "1.0")
        self.assertTrue(status["completed"])
        self.assertTrue(status["timestamp"].endswith("Z"))
        self.assertFalse(self.plugin.needs_processing(document, self.track))

    def test_tag_lookup_skips_keys_rejected_by_a_format(self):
        class Tags(dict):
            def __getitem__(self, key):
                if key == "invalid":
                    raise ValueError("invalid Vorbis key")
                return super().__getitem__(key)

        class Audio:
            tags = Tags({"TITLE": ["Example"]})

        value = MetadataExtractor()._first(Audio(), ["invalid", "TITLE"])

        self.assertEqual(value, "Example")

    def test_reprocesses_when_version_is_outdated(self):
        document = {
            "metadata": {"title": "Old"},
            "system": {
                "modules": {
                    "metadata": {"version": "0.9", "completed": True}
                }
            },
        }

        self.assertTrue(self.plugin.needs_processing(document, self.track))


class PipelineTest(unittest.TestCase):
    @patch("modules.pipeline.MetadataPlugin")
    @patch("modules.pipeline.Registry.content_hash", return_value="track-1")
    @patch("modules.pipeline.Scanner")
    @patch("modules.pipeline.Config")
    def test_continues_when_metadata_extraction_fails(
        self, config_class, scanner_class, content_hash, plugin_class
    ):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            output_directory = root / "output" / "tracks"
            track = Track(str(root / "invalid.mp3"), "invalid.mp3", ".mp3")
            Path(track.path).write_bytes(b"not an mp3")
            config_class.return_value.data = {
                "musicRoot": str(root),
                "outputRoot": str(output_directory),
                "supportedFormats": [".mp3"],
            }
            scanner_class.return_value.scan.return_value = [track]
            plugin = Mock()
            plugin.needs_processing.return_value = True
            plugin.process.side_effect = ValueError("invalid audio")
            plugin_class.return_value = plugin

            Pipeline().run()

            document = JsonManager(output_directory).load("track-1")
            self.assertEqual(document["system"]["sourcePath"], track.path)
            self.assertFalse(document["metadata"])
            plugin.process.assert_called_once()


if __name__ == "__main__":
    unittest.main()
