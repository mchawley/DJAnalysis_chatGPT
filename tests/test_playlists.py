import json
import tempfile
import unittest
from pathlib import Path

from modules.playlist_store import PlaylistStore
from ui import InsightsHandler


class PlaylistStoreTest(unittest.TestCase):
    def test_source_playlist_stays_unchanged_when_first_edited(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PlaylistStore(Path(directory) / "output" / "tracks")
            store.save_sources([{"id": "rekordbox-0", "name": "Warmup", "source": "rekordbox", "trackIds": ["one", "two"]}])
            copy = store.update("rekordbox-0", track_ids=["two", "one"])
            self.assertEqual(copy["source"], "rekordbox-copy")
            self.assertEqual(store.source_playlists()[0]["trackIds"], ["one", "two"])
            self.assertEqual(store.restore(copy["id"])["trackIds"], ["one", "two"])

    def test_custom_playlist_preserves_selected_order(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PlaylistStore(Path(directory) / "output" / "tracks")
            playlist = store.create("Set", ["third", "first", "second"])
            self.assertEqual(playlist["trackIds"], ["third", "first", "second"])


class PlaylistApiTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.output = Path(self.directory.name) / "output" / "tracks"
        self.output.mkdir(parents=True)
        self.original = InsightsHandler.output_root
        InsightsHandler.output_root = self.output
        self._document("one", "First", 120, "8A", .10, .12, 12, 1200)
        self._document("two", "Second", 122, "9A", .12, .13, 15, 1300)
        self._document("three", "Odd", 138, "2B", .90, .92, 90, 4800)
        PlaylistStore(self.output).create("Set", ["one", "two", "three"])

    def tearDown(self):
        InsightsHandler.output_root = self.original
        self.directory.cleanup()

    def _document(self, track_id, title, bpm, key, energy, bass, rhythm, brightness):
        document = {
            "system": {"trackId": track_id}, "metadata": {"title": title, "artist": "DJ"},
            "library": {"bpm": bpm, "key": key},
            "analysis": {"fingerprints": [{"energy": {"overall": energy}, "bass": {"overall": bass}, "rhythm": {"density": rhythm}, "spectrum": {"spectral_centroid": brightness}}]},
        }
        (self.output / f"{track_id}.json").write_text(json.dumps(document))

    def test_detail_uses_only_playlist_tracks_and_keeps_raw_tempo(self):
        playlist_id = PlaylistStore(self.output).local_playlists()[0]["id"]
        detail = InsightsHandler._playlist_detail(InsightsHandler.__new__(InsightsHandler), playlist_id)
        self.assertEqual([track["id"] for track in detail["tracks"]], ["one", "two", "three"])
        self.assertEqual(detail["tracks"][2]["bpm"], 138)
        self.assertEqual(len(detail["trends"]["energy"]), 3)

    def test_outlier_and_transition_have_explanations(self):
        playlist_id = PlaylistStore(self.output).local_playlists()[0]["id"]
        track = InsightsHandler._playlist_detail(InsightsHandler.__new__(InsightsHandler), playlist_id)["tracks"][2]
        self.assertTrue(track["transition"]["reasons"])
        self.assertTrue(track["outlier"]["reasons"])

    def test_camelot_plus_one_is_compatible(self):
        self.assertTrue(InsightsHandler._compatible_keys("11A", "12A"))
        self.assertTrue(InsightsHandler._compatible_keys("12A", "1A"))
        self.assertTrue(InsightsHandler._compatible_keys("11A", "1A"))
        self.assertFalse(InsightsHandler._compatible_keys("11A", "5A"))

    def test_transition_compares_only_the_previous_track(self):
        playlist_id = PlaylistStore(self.output).local_playlists()[0]["id"]
        tracks = InsightsHandler._playlist_detail(InsightsHandler.__new__(InsightsHandler), playlist_id)["tracks"]
        self.assertEqual(tracks[0]["transition"]["label"], "No transition data")

    def test_missing_document_remains_visible(self):
        playlist_id = PlaylistStore(self.output).local_playlists()[0]["id"]
        PlaylistStore(self.output).update(playlist_id, track_ids=["one", "missing"])
        detail = InsightsHandler._playlist_detail(InsightsHandler.__new__(InsightsHandler), playlist_id)
        self.assertFalse(detail["tracks"][1]["available"])
