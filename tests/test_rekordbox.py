import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from models.track import Track
from modules.rekordbox.importer import RekordboxImporter
from modules.rekordbox.analysis_importer import RekordboxAnalysisImporter
from modules.rekordbox.anlz import RekordboxAnlzParser
from modules.rekordbox.matcher import RekordboxMatcher
from modules.rekordbox.parser import RekordboxParser


XML = """<?xml version="1.0" encoding="UTF-8"?>
<DJ_PLAYLISTS Version="1.0.0">
  <COLLECTION Entries="1">
    <TRACK TrackID="42" Name="Track One" Artist="DJ Example" Album="Album" Genre="House"
           AverageBpm="122.0" Tonality="8A" Rating="5" Colour="Blue" Comments="Opening track"
           DateAdded="2026-01-02" PlayCount="34" LastPlayed="2026-02-03 04:05:06"
           Location="file://localhost/Users/DJ/Track%20One.mp3">
      <POSITION_MARK Name="Intro" Type="0" Start="12.5" Num="-1" Red="255" Green="0" Blue="0" />
      <POSITION_MARK Name="Drop" Type="1" Start="64.0" Num="2" Red="0" Green="0" Blue="255" />
      <TEMPO Inizio="0.0" Bpm="122.0" Battito="1" />
    </TRACK>
  </COLLECTION>
  <PLAYLISTS>
    <NODE Name="ROOT" Type="0">
      <NODE Name="Warmup" Type="1"><TRACK Key="42" /></NODE>
    </NODE>
  </PLAYLISTS>
</DJ_PLAYLISTS>
"""


class RekordboxParserTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = TemporaryDirectory()
        self.xml_path = Path(self.temporary_directory.name) / "rekordbox.xml"
        self.xml_path.write_text(XML, encoding="utf-8")
        self.track = RekordboxParser().parse(self.xml_path)[0]

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_parses_track_and_dj_metadata(self):
        self.assertEqual(self.track.location, "/Users/DJ/Track One.mp3")
        self.assertEqual(self.track.bpm, 122.0)
        self.assertEqual(self.track.key, "8A")
        self.assertEqual(self.track.play_count, 34)
        self.assertEqual(self.track.playlists, ["ROOT / Warmup"])
        self.assertEqual(self.track.memory_cues[0].name, "Intro")
        self.assertEqual(self.track.hot_cues[0].number, 2)
        self.assertEqual(self.track.beat_grid[0].bpm, 122.0)

    def test_matcher_uses_requested_confidence_order(self):
        matcher = RekordboxMatcher([self.track])
        path_match = matcher.match(Track("/Users/DJ/Track One.mp3", "Track One.mp3", ".mp3"))
        filename_match = matcher.match(Track("/elsewhere/Track One.mp3", "Track One.mp3", ".mp3"))
        title_artist_match = matcher.match(
            Track("/elsewhere/other.mp3", "other.mp3", ".mp3"),
            {"metadata": {"title": "Track One", "artist": "DJ Example"}},
        )

        self.assertEqual((path_match.confidence, path_match.method), (100, "Path"))
        self.assertEqual((filename_match.confidence, filename_match.method), (90, "Filename"))
        self.assertEqual((title_artist_match.confidence, title_artist_match.method), (80, "TitleArtist"))

    def test_importer_updates_only_library_section(self):
        document = {"metadata": {"title": "Existing"}, "energy": {"score": 8}}

        RekordboxImporter().import_track(document, self.track)

        self.assertEqual(document["metadata"], {"title": "Existing"})
        self.assertEqual(document["energy"], {"score": 8})
        self.assertEqual(document["library"]["provider"], "rekordbox")
        self.assertEqual(document["library"]["trackId"], "42")
        self.assertEqual(document["library"]["playlists"], ["ROOT / Warmup"])
        self.assertEqual(document["library"]["memoryCues"][0]["color"], "#FF0000")
        self.assertEqual(document["library"]["hotCues"][0]["number"], 2)


class RekordboxAnlzParserTest(unittest.TestCase):
    def test_reads_analysis_with_pyrekordbox_adapter(self):
        class FakeAnlz:
            def get(self, name):
                return {
                    "path": "/Users/DJ/Track One.mp3",
                    "beat_grid": ([1, 2], [122.0, 122.0], [0.0, 0.492]),
                    "wf_preview": ([3, 9, 12], [0, 0, 0]),
                    "wf_detail": ([7, 14], [0, 0]),
                    "structure": {"entries": [{"start": 0, "mood": "intro"}]},
                }.get(name)

        class FakeAnlzFile:
            @staticmethod
            def parse_file(path):
                return FakeAnlz()

        with TemporaryDirectory() as directory:
            anlz_path = Path(directory) / "ANLZ0000.DAT"
            anlz_path.write_bytes(b"fixture")
            analysis = RekordboxAnlzParser(FakeAnlzFile).parse_directory(directory)[
                "/Users/DJ/Track One.mp3"
            ]

        self.assertEqual(analysis.beat_positions, [0.0, 0.492])
        self.assertEqual(analysis.waveform_preview, [3, 9, 12])
        self.assertEqual(analysis.phrases, [{"start": 0, "mood": "intro"}])

        document = {"metadata": {"title": "Existing"}}
        RekordboxAnalysisImporter().import_analysis(document, analysis)
        self.assertEqual(document["metadata"], {"title": "Existing"})
        self.assertEqual(document["analysis"]["provider"], "rekordbox")
        self.assertEqual(document["analysis"]["waveformDetail"], [7, 14])

    def test_skips_unreadable_anlz_files(self):
        class FakeAnlzFile:
            @staticmethod
            def parse_file(path):
                raise IndexError("invalid analysis file")

        with TemporaryDirectory() as directory:
            anlz_path = Path(directory) / "ANLZ0000.DAT"
            anlz_path.write_bytes(b"fixture")
            parser = RekordboxAnlzParser(FakeAnlzFile)
            self.assertEqual(parser.parse_directory(directory), {})

        self.assertEqual(len(parser.errors), 1)
        self.assertEqual(parser.errors[0][0], anlz_path)

    def test_skips_anlz_files_with_unreadable_tags(self):
        class FakeAnlz:
            def get(self, name):
                raise IndexError("invalid tag")

        class FakeAnlzFile:
            @staticmethod
            def parse_file(path):
                return FakeAnlz()

        with TemporaryDirectory() as directory:
            anlz_path = Path(directory) / "ANLZ0000.DAT"
            anlz_path.write_bytes(b"fixture")
            parser = RekordboxAnlzParser(FakeAnlzFile)
            self.assertEqual(parser.parse_directory(directory), {})

        self.assertEqual(parser.errors[0][0], anlz_path)


if __name__ == "__main__":
    unittest.main()
