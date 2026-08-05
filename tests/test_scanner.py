import tempfile
import unittest
from pathlib import Path

from modules.scanner import Scanner


class ScannerTest(unittest.TestCase):
    def test_scans_supported_files_from_multiple_roots(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "first"
            second = root / "second"
            first.mkdir()
            second.mkdir()
            (first / "one.mp3").touch()
            (second / "two.flac").touch()
            (second / "ignored.txt").touch()

            tracks = Scanner([first, second], [".mp3", ".flac"]).scan()

        self.assertEqual([track.filename for track in tracks], ["one.mp3", "two.flac"])

    def test_remains_compatible_with_one_root_and_ignores_duplicate_roots(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "one.mp3").touch()

            single = Scanner(str(root), [".mp3"]).scan()
            repeated = Scanner([root, root], [".mp3"]).scan()

        self.assertEqual(len(single), 1)
        self.assertEqual(len(repeated), 1)
