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

    def test_first_source_reorder_maps_source_entry_ids_to_the_local_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PlaylistStore(Path(directory) / "output" / "tracks")
            store.save_sources([{"id": "rekordbox-0", "name": "Warmup", "source": "rekordbox", "trackIds": ["one", "two"]}])
            source_entries = store.entries(store.source_playlists()[0])
            copy = store.update("rekordbox-0", entry_ids=[source_entries[1]["id"], source_entries[0]["id"]])
            self.assertEqual(copy["trackIds"], ["two", "one"])
            self.assertEqual(store.source_playlists()[0]["trackIds"], ["one", "two"])

    def test_custom_playlist_preserves_selected_order(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PlaylistStore(Path(directory) / "output" / "tracks")
            playlist = store.create("Set", ["third", "first", "second"])
            self.assertEqual(playlist["trackIds"], ["third", "first", "second"])

    def test_segment_edit_creates_a_local_copy_and_translates_source_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PlaylistStore(Path(directory) / "output" / "tracks")
            store.save_sources([{"id": "rekordbox-0", "name": "Warmup", "source": "rekordbox", "trackIds": ["one", "two"]}])
            source_entry = store.entries(store.source_playlists()[0])[0]["id"]
            copy = store.set_segment_included("rekordbox-0", source_entry, 2, False)
            self.assertEqual(copy["source"], "rekordbox-copy")
            self.assertEqual(store.source_playlists()[0].get("segmentExclusions"), None)
            self.assertEqual(list(copy["segmentExclusions"].values()), [[2]])
            self.assertEqual([item["id"] for item in store.all_playlists()], [copy["id"]])

    def test_segment_exclusions_follow_duplicate_entries_through_reorder(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PlaylistStore(Path(directory) / "output" / "tracks")
            playlist = store.create("Set", ["one", "one"])
            first, second = [entry["id"] for entry in playlist["entries"]]
            store.set_segment_included(playlist["id"], first, 1, False)
            reordered = store.update(playlist["id"], entry_ids=[second, first])
            self.assertEqual(reordered["segmentExclusions"][first], [1])


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

    def _document(self, track_id, title, bpm, key, energy, bass, rhythm, brightness, duration=240):
        document = {
            "system": {"trackId": track_id}, "metadata": {"title": title, "artist": "DJ"},
            "library": {"bpm": bpm, "key": key},
            "analysis": {"fingerprints": [{"end_time": duration, "energy": {"overall": energy}, "bass": {"overall": bass}, "rhythm": {"density": rhythm}, "spectrum": {"spectral_centroid": brightness}}]},
        }
        (self.output / f"{track_id}.json").write_text(json.dumps(document))

    def test_detail_uses_only_playlist_tracks_and_keeps_raw_tempo(self):
        playlist_id = PlaylistStore(self.output).local_playlists()[0]["id"]
        detail = InsightsHandler._playlist_detail(InsightsHandler.__new__(InsightsHandler), playlist_id)
        self.assertEqual([track["id"] for track in detail["tracks"]], ["one", "two", "three"])
        self.assertEqual(detail["tracks"][2]["bpm"], 138)
        self.assertEqual(detail["tracks"][0]["duration"], 240)
        self.assertEqual(len(detail["trends"]["energy"]), 3)
        self.assertEqual(detail["tracks"][0]["segments"][0]["type"], "CUSTOM")
        self.assertEqual(detail["tracks"][0]["segments"][0]["normalized_energy"], 0.5)
        self.assertEqual(detail["tracks"][0]["segments"][0]["normalized_bass"], 0.5)
        self.assertEqual(detail["tracks"][0]["segments"][0]["normalized_rhythm"], 0.5)
        self.assertEqual(detail["tracks"][0]["segments"][0]["normalized_brightness"], 0.5)
        self.assertNotIn("transition_energy", detail["tracks"][0])

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

    def test_selected_segments_drive_duration_weighted_features_and_skip_state(self):
        document = json.loads((self.output / "one.json").read_text())
        document["analysis"]["fingerprints"] = [
            {"start_time": 0, "end_time": 10, "energy": {"overall": .1}, "bass": {"overall": .2}, "rhythm": {"density": 10}, "spectrum": {"spectral_centroid": 1000}},
            {"start_time": 10, "end_time": 30, "energy": {"overall": .7}, "bass": {"overall": .8}, "rhythm": {"density": 30}, "spectrum": {"spectral_centroid": 3000}},
        ]
        (self.output / "one.json").write_text(json.dumps(document))
        store = PlaylistStore(self.output)
        playlist_id = store.local_playlists()[0]["id"]
        entry_id = store.entries(store.local_playlists()[0])[0]["id"]
        store.set_segment_included(playlist_id, entry_id, 0, False)
        detail = InsightsHandler._playlist_detail(InsightsHandler.__new__(InsightsHandler), playlist_id)
        track = detail["tracks"][0]
        self.assertEqual(track["duration"], 20)
        self.assertAlmostEqual(track["features"]["energy"], .7)
        self.assertFalse(track["originalSegments"][0]["included"])
        self.assertTrue(track["originalSegments"][1]["included"])
        store.set_segment_included(playlist_id, entry_id, 1, False)
        detail = InsightsHandler._playlist_detail(InsightsHandler.__new__(InsightsHandler), playlist_id)
        self.assertFalse(detail["tracks"][0]["playable"])
        self.assertNotIn("one", [track["id"] for track in detail["chartTracks"]])
