from pathlib import Path

from .anlz import RekordboxAnlzParser
from .models import HotCue, MemoryCue, RekordboxTrack
from .pssi import PssiParser
from .raw_anlz import RawAnlzParser


class RekordboxDatabaseAnalysisReader:
    """Read linked ANLZ files through Rekordbox's read-only MasterDatabase API."""

    ANALYSIS_TYPES = ("DAT", "EXT", "EX2")

    def __init__(self, database_factory=None):
        self.database_factory = database_factory
        self.errors = []

    def read(self):
        database = (self.database_factory or self._load_database_factory())()
        parser = RekordboxAnlzParser()
        analyses = {}
        self.errors = []

        for content in database.get_content():
            location = self._content_path(content)
            if not location:
                continue
            try:
                analysis_files = database.read_anlz_files(content)
            except (AttributeError, IndexError, KeyError, TypeError, ValueError):
                # pyrekordbox 0.4.x cannot decode several Rekordbox 7 tags.
                # Try every linked file independently; unsupported files are skipped.
                analysis_files = self._read_analysis_files(database, content)
            except Exception as error:
                self.errors.append((location, "ANLZ", error))
                analysis_files = {}
            for analysis_type, anlz in analysis_files.items():
                try:
                    if anlz is None:
                        continue
                    source_path = self._analysis_path(database, content, analysis_type)
                    analyses[location] = parser.extract(
                        anlz, location, source_path, analyses.get(location)
                    )
                except Exception as error:
                    if not self._is_unsupported_anlz_error(error):
                        self.errors.append((location, analysis_type, error))
            try:
                paths = database.get_anlz_paths(content)
                dat_path = paths.get("DAT")
                ext_path = paths.get("EXT")
                beat_grid = RawAnlzParser().parse_beat_grid(dat_path) if dat_path else None
                pssi = PssiParser().parse_file(ext_path) if ext_path else None
                if beat_grid or pssi:
                    analysis = analyses.setdefault(location, parser.extract(
                        None, location, dat_path or ext_path
                    ))
                    if beat_grid:
                        analysis.beat_numbers = beat_grid["beatNumbers"]
                        analysis.bpms = beat_grid["bpms"]
                        analysis.beat_positions = beat_grid["beatPositions"]
                    if pssi:
                        analysis.phrases = pssi["phrases"]
                        analysis.structure = {
                            "endBeat": pssi["endBeat"],
                            "entrySize": pssi["entrySize"],
                        }
            except Exception as error:
                self.errors.append((location, "PSSI", error))
        return analyses

    @staticmethod
    def _load_database_factory():
        try:
            from pyrekordbox import MasterDatabase
            return MasterDatabase
        except ImportError as master_error:
            try:
                from pyrekordbox import Rekordbox6Database
                return Rekordbox6Database
            except ImportError as legacy_error:
                raise RuntimeError(
                    "The installed pyrekordbox version does not expose a database handler. "
                    "Run: pip install --upgrade pyrekordbox "
                    f"(MasterDatabase: {master_error}; "
                    f"Rekordbox6Database: {legacy_error})"
                ) from legacy_error

    @classmethod
    def _read_analysis_files(cls, database, content):
        files = {}
        for analysis_type in ("DAT", "EXT", "2EX", "EX2"):
            try:
                files[analysis_type] = database.read_anlz_file(content, analysis_type)
            except Exception:
                # Rekordbox 7 analysis may contain tags unsupported by the
                # installed pyrekordbox version. Raw PSSI parsing still runs.
                continue
        return files

    @staticmethod
    def _is_unsupported_anlz_error(error):
        return isinstance(error, (IndexError, KeyError, TypeError, ValueError))

    @staticmethod
    def _analysis_path(database, content, analysis_type):
        try:
            paths = database.get_anlz_paths(content)
            return paths.get(analysis_type) or analysis_type
        except AttributeError:
            try:
                return database.get_anlz_path(content, analysis_type) or analysis_type
            except (AttributeError, KeyError, ValueError):
                return analysis_type

    @staticmethod
    def _content_path(content):
        path = getattr(content, "FolderPath", None) or getattr(content, "folder_path", None)
        filename = getattr(content, "Filename", None) or getattr(content, "FileName", None)
        if not path:
            return None
        if filename and Path(str(path)).name != filename:
            return str(Path(str(path)) / filename)
        return str(path)


class RekordboxDatabaseLibraryReader:
    """Read library metadata, playlists, and cues through Rekordbox's unlocked DB."""

    def __init__(self, database_factory=None):
        self.database_factory = database_factory

    def read(self):
        from sqlalchemy import text

        database = (self.database_factory or RekordboxDatabaseAnalysisReader._load_database_factory())()
        with database.engine.connect() as connection:
            tracks = self._tracks(connection, text)
            self._add_playlists(connection, text, tracks)
            self._add_cues(connection, text, tracks)
        return list(tracks.values())

    @staticmethod
    def _tracks(connection, text):
        rows = connection.execute(text("""
            SELECT c.ID AS track_id, c.FolderPath AS location, c.Title AS title,
                   COALESCE(a.Name, '') AS artist, al.Name AS album, g.Name AS genre,
                   c.BPM AS bpm, k.ScaleName AS musical_key, c.Rating AS rating,
                   color.Commnt AS color, c.Commnt AS comments, c.StockDate AS date_added,
                   c.DJPlayCount AS play_count
            FROM djmdContent c
            LEFT JOIN djmdArtist a ON a.ID = c.ArtistID
            LEFT JOIN djmdAlbum al ON al.ID = c.AlbumID
            LEFT JOIN djmdGenre g ON g.ID = c.GenreID
            LEFT JOIN djmdKey k ON k.ID = c.KeyID
            LEFT JOIN djmdColor color ON color.ID = c.ColorID
        """)).mappings()
        return {
            row["track_id"]: RekordboxTrack(
                track_id=str(row["track_id"]), location=row["location"] or "",
                title=row["title"] or "", artist=row["artist"] or "", album=row["album"],
                genre=row["genre"], bpm=(float(row["bpm"]) / 100 if row["bpm"] else None),
                key=row["musical_key"], rating=row["rating"], color=row["color"],
                comments=row["comments"], date_added=None, play_count=row["play_count"],
                last_played=None,
            )
            for row in rows
        }

    @staticmethod
    def _add_playlists(connection, text, tracks):
        rows = connection.execute(text("""
            SELECT song.ContentID AS content_id, playlist.Name AS playlist_name
            FROM djmdSongPlaylist song
            JOIN djmdPlaylist playlist ON playlist.ID = song.PlaylistID
        """)).mappings()
        for row in rows:
            track = tracks.get(row["content_id"])
            if track:
                track.playlists.append(row["playlist_name"])

    @staticmethod
    def _add_cues(connection, text, tracks):
        rows = connection.execute(text("""
            SELECT ContentID AS content_id, InMsec AS start_ms, OutMsec AS end_ms,
                   Kind AS kind, Comment AS comment, ColorTableIndex AS color
            FROM djmdCue
        """)).mappings()
        for row in rows:
            track = tracks.get(row["content_id"])
            if not track:
                continue
            cue_data = {
                "position": (row["start_ms"] or 0) / 1000,
                "end": (row["end_ms"] or 0) / 1000 or None,
                "name": row["comment"] or None,
                "color": str(row["color"]) if row["color"] is not None else None,
            }
            if row["kind"]:
                track.hot_cues.append(HotCue(**cue_data, number=None))
            else:
                track.memory_cues.append(MemoryCue(**cue_data))
