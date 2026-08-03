import unittest

from models.track import Track
from modules.metadata import MetadataExtractor
from modules.metadata_plugin import MetadataPlugin


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


if __name__ == "__main__":
    unittest.main()
