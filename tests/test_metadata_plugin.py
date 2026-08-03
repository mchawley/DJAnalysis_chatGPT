import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from models.track import Track
from modules.json_manager import JsonManager
from modules.metadata import MetadataExtractor
from modules.metadata_plugin import MetadataPlugin
from modules.pipeline import Pipeline
from modules.rekordbox.models import RekordboxTrack


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

    @patch("modules.pipeline.MetadataPlugin")
    @patch("modules.pipeline.Registry.content_hash", return_value="track-1")
    @patch("modules.pipeline.Scanner")
    @patch("modules.pipeline.Config")
    def test_processes_only_one_document_for_duplicate_content(
        self, config_class, scanner_class, content_hash, plugin_class
    ):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            output_directory = root / "output" / "tracks"
            first = Track(str(root / "first.mp3"), "first.mp3", ".mp3")
            duplicate = Track(str(root / "duplicate.mp3"), "duplicate.mp3", ".mp3")
            Path(first.path).write_bytes(b"same content")
            Path(duplicate.path).write_bytes(b"same content")
            config_class.return_value.data = {
                "musicRoot": str(root),
                "outputRoot": str(output_directory),
                "supportedFormats": [".mp3"],
            }
            scanner_class.return_value.scan.return_value = [first, duplicate]
            plugin = Mock()
            plugin.needs_processing.return_value = False
            plugin_class.return_value = plugin

            Pipeline().run()

            document = JsonManager(output_directory).load("track-1")
            self.assertEqual(document["system"]["sourcePath"], first.path)
            self.assertEqual(len(plugin.process.call_args_list), 0)

    @patch("modules.pipeline.RekordboxParser")
    @patch("modules.pipeline.MetadataPlugin")
    @patch("modules.pipeline.Registry.content_hash", return_value="track-1")
    @patch("modules.pipeline.Scanner")
    @patch("modules.pipeline.Config")
    def test_imports_matching_rekordbox_metadata(
        self, config_class, scanner_class, content_hash, plugin_class, parser_class
    ):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            output_directory = root / "output" / "tracks"
            track = Track(str(root / "song.mp3"), "song.mp3", ".mp3")
            Path(track.path).write_bytes(b"audio")
            config_class.return_value.data = {
                "musicRoot": str(root),
                "outputRoot": str(output_directory),
                "rekordboxXmlPath": str(root / "rekordbox.xml"),
                "supportedFormats": [".mp3"],
            }
            scanner_class.return_value.scan.return_value = [track]
            plugin_class.return_value.needs_processing.return_value = False
            parser_class.return_value.parse.return_value = [
                RekordboxTrack(
                    track_id="42", location=track.path, title="Song", artist="DJ",
                    album=None, genre=None, bpm=122.0, key="8A", rating=5,
                    color="Blue", comments="Test", date_added=None, play_count=1,
                    last_played=None,
                )
            ]

            Pipeline().run()
            document_path = JsonManager(output_directory).get_json_path("track-1")
            first_modified = document_path.stat().st_mtime_ns
            Pipeline().run()

            document = JsonManager(output_directory).load("track-1")
            self.assertEqual(document["library"]["provider"], "rekordbox")
            self.assertEqual(document["library"]["trackId"], "42")
            self.assertTrue(
                Pipeline._module_is_current(document, "rekordbox_library", "1.0")
            )
            parser_class.return_value.parse.assert_called_once()
            self.assertEqual(document_path.stat().st_mtime_ns, first_modified)


if __name__ == "__main__":
    unittest.main()
