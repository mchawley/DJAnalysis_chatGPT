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
            for analysis_type in self.ANALYSIS_TYPES:
                try:
                    anlz = database.read_anlz_file(content, analysis_type)
                    if anlz is None:
                        continue
                    source_path = database.get_anlz_path(content, analysis_type) or analysis_type
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
        except ImportError as error:
            raise RuntimeError(
                "Rekordbox database support requires pyrekordbox. "
                "Run: pip install -r requirements.txt"
            ) from error
        return MasterDatabase

    @staticmethod
    def _content_path(content):
        path = getattr(content, "FolderPath", None) or getattr(content, "folder_path", None)
        filename = getattr(content, "Filename", None) or getattr(content, "FileName", None)
        if not path:
            return None
        if filename and Path(str(path)).name != filename:
            return str(Path(str(path)) / filename)
        return str(path)
