from pathlib import Path

from .anlz import RekordboxAnlzParser


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
            except AttributeError:
                analysis_files = self._read_analysis_files(database, content)
            for analysis_type, anlz in analysis_files.items():
                try:
                    if anlz is None:
                        continue
                    source_path = self._analysis_path(database, content, analysis_type)
                    analyses[location] = parser.extract(
                        anlz, location, source_path, analyses.get(location)
                    )
                except Exception as error:
                    self.errors.append((location, analysis_type, error))
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
            except (KeyError, ValueError):
                continue
        return files

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
