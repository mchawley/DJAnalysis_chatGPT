from modules.config import Config
from modules.logger import Logger
from modules.scanner import Scanner
from modules.registry import Registry
from modules.json_manager import JsonManager
from modules.manifest import ManifestManager
from modules.metadata_plugin import MetadataPlugin
from modules.rekordbox.importer import RekordboxImporter
from modules.rekordbox.matcher import RekordboxMatcher
from modules.rekordbox.parser import RekordboxParser
from modules.rekordbox.analysis_importer import RekordboxAnalysisImporter
from modules.rekordbox.database import (
    RekordboxDatabaseAnalysisReader,
    RekordboxDatabaseLibraryReader,
)
from datetime import datetime, timezone
from pathlib import Path
from tqdm import tqdm

class Pipeline:
    REKORDBOX_LIBRARY_VERSION = "3.0"
    REKORDBOX_ANALYSIS_VERSION = "5.0"

    def run(self):
        cfg=Config().data
        log=Logger()
        scanner=Scanner(cfg['musicRoot'],cfg['supportedFormats'])
        jm=JsonManager(cfg['outputRoot'])
        manifest_manager = ManifestManager(cfg['outputRoot'])
        metadata_plugin = MetadataPlugin()
        rekordbox_library_enabled = cfg.get("rekordboxDatabaseLibrary", False)
        rekordbox_matcher = None
        rekordbox_xml_loaded = False
        rekordbox_importer = RekordboxImporter()
        rekordbox_analysis_enabled = cfg.get("rekordboxDatabaseAnalysis", False)
        analysis_importer = RekordboxAnalysisImporter()
        previous_tracks = manifest_manager.load()['tracks']
        log.info("Scanning music library...")
        tracks=scanner.scan()
        current_tracks = {}
        track_ids_by_path = {}
        documents_updated = 0
        metadata_updated = 0
        metadata_failed = 0
        rekordbox_imported = 0
        rekordbox_unmatched = 0
        rekordbox_skipped = 0
        analysis_imported = 0
        analysis_skipped = 0
        duplicates = 0
        states = {"new": 0, "modified": 0, "moved": 0, "unchanged": 0}
        replaced_track_ids = set()
        previous_ids_by_path = {
            entry.get("path"): track_id
            for track_id, entry in previous_tracks.items()
        }
        log.info(f'Found {len(tracks)} tracks')
        log.info("Updating track documents and library metadata...")
        with tqdm(tracks, desc="Processing tracks", unit="track") as progress:
            for t in progress:
                progress.set_postfix_str(Path(t.path).name, refresh=False)
                tid=Registry.content_hash(t.path)
                if tid in current_tracks:
                    duplicates += 1
                    progress.write(
                        f"[INFO] Duplicate skipped: {t.path} "
                        f"(same content as {current_tracks[tid]['path']})"
                    )
                    continue

                entry = manifest_manager.build_entry(tid, t.path, jm.get_json_path(tid))
                state = manifest_manager.get_track_state(previous_tracks.get(tid), entry)

                if state == "new":
                    previous_id = previous_ids_by_path.get(entry["path"])
                    if previous_id is not None and previous_id != tid:
                        state = "modified"
                        replaced_track_ids.add(previous_id)

                json_path = jm.get_json_path(tid)
                document_exists = json_path.exists()
                doc = jm.load(tid)
                document_changed = not document_exists
                system = doc.setdefault("system", {})
                if "trackId" not in system:
                    system["trackId"] = tid
                    document_changed = True
                if "createdAt" not in system:
                    system["createdAt"] = datetime.now(timezone.utc).isoformat().replace(
                        "+00:00", "Z"
                    )
                    document_changed = True
                if system.get("sourcePath") != t.path:
                    system["sourcePath"] = t.path
                    document_changed = True
                if "schemaVersion" not in system:
                    system["schemaVersion"] = "0.1"
                    document_changed = True
                if metadata_plugin.needs_processing(doc, t):
                    try:
                        metadata_plugin.process(doc, t)
                        metadata_updated += 1
                        document_changed = True
                    except Exception as error:
                        metadata_failed += 1
                        progress.write(
                            f"[ERROR] Metadata failed for {t.path}: "
                            f"{type(error).__name__}: {error}"
                        )
                if rekordbox_library_enabled and not self._module_is_current(
                    doc, "rekordbox_library", self.REKORDBOX_LIBRARY_VERSION
                ):
                    if not rekordbox_xml_loaded:
                        rekordbox_matcher = self._load_rekordbox_database_matcher(log)
                        rekordbox_xml_loaded = True
                    if rekordbox_matcher:
                        rekordbox_match = rekordbox_matcher.match(t, doc)
                        if rekordbox_match.track:
                            rekordbox_importer.import_track(doc, rekordbox_match.track)
                            self._mark_module_complete(
                                doc, "rekordbox_library", self.REKORDBOX_LIBRARY_VERSION
                            )
                            rekordbox_imported += 1
                            document_changed = True
                        else:
                            rekordbox_unmatched += 1
                elif rekordbox_library_enabled:
                    rekordbox_skipped += 1
                if document_changed:
                    jm.save(tid,doc)
                    documents_updated += 1
                current_tracks[tid] = entry
                track_ids_by_path[self._normalise_path(t.path)] = tid
                states[state] += 1

        if rekordbox_analysis_enabled:
            imported, skipped = self._import_rekordbox_analyses(
                track_ids_by_path, jm, analysis_importer, log
            )
            analysis_imported += imported
            analysis_skipped += skipped
            documents_updated += imported

        deleted = set(previous_tracks) - set(current_tracks) - replaced_track_ids
        if current_tracks != previous_tracks:
            manifest_manager.save(current_tracks)

        log.info(f'Documents updated : {documents_updated}')
        log.info(f'Metadata updated   : {metadata_updated}')
        log.info(f'Metadata failed    : {metadata_failed}')
        if rekordbox_library_enabled:
            log.info(f'Rekordbox imported: {rekordbox_imported}')
            log.info(f'Rekordbox unmatched: {rekordbox_unmatched}')
            log.info(f'Rekordbox skipped  : {rekordbox_skipped}')
        if rekordbox_analysis_enabled:
            log.info(f'Rekordbox analysis: {analysis_imported}')
            log.info(f'Analysis skipped   : {analysis_skipped}')
        log.info(f'Duplicates         : {duplicates}')
        log.info(f'New               : {states["new"]}')
        log.info(f'Modified          : {states["modified"]}')
        log.info(f'Moved             : {states["moved"]}')
        log.info(f'Unchanged         : {states["unchanged"]}')
        log.info(f'Deleted           : {len(deleted)}')

    @staticmethod
    def _load_rekordbox_matcher(xml_path, log):
        if not xml_path:
            return None
        try:
            rekordbox_tracks = RekordboxParser().parse(xml_path)
        except Exception as error:
            log.error(
                f"Could not read Rekordbox XML at {xml_path}: "
                f"{type(error).__name__}: {error}"
            )
            return None

        log.info(f"Loaded {len(rekordbox_tracks)} Rekordbox tracks")
        return RekordboxMatcher(rekordbox_tracks)

    @staticmethod
    def _load_rekordbox_database_matcher(log):
        log.info("Loading Rekordbox library metadata...")
        try:
            rekordbox_tracks = RekordboxDatabaseLibraryReader().read()
        except Exception as error:
            log.error(
                "Could not read Rekordbox library through MasterDatabase: "
                f"{type(error).__name__}: {error}"
            )
            return None
        log.info(f"Loaded {len(rekordbox_tracks)} Rekordbox tracks from MasterDatabase")
        return RekordboxMatcher(rekordbox_tracks)

    @classmethod
    def _import_rekordbox_analyses(cls, track_ids_by_path, json_manager, importer, log):
        """Stream analysis records and persist matching documents immediately."""
        imported = 0
        skipped = 0
        try:
            reader = RekordboxDatabaseAnalysisReader()
            analyses = reader.iter_analyses()
            log.info("Streaming Rekordbox analysis...")
            with tqdm(analyses, desc="Importing Rekordbox analysis", unit="track") as progress:
                for location, analysis in progress:
                    progress.set_postfix_str(Path(location).name, refresh=False)
                    track_id = track_ids_by_path.get(cls._normalise_path(location))
                    if track_id is None:
                        continue
                    document = json_manager.load(track_id)
                    if cls._module_is_current(
                        document, "rekordbox_analysis", cls.REKORDBOX_ANALYSIS_VERSION
                    ):
                        skipped += 1
                        continue
                    importer.import_analysis(document, analysis)
                    cls._mark_module_complete(
                        document, "rekordbox_analysis", cls.REKORDBOX_ANALYSIS_VERSION
                    )
                    json_manager.save(track_id, document)
                    imported += 1
        except Exception as error:
            log.error(
                "Could not read Rekordbox analysis through MasterDatabase: "
                f"{type(error).__name__}: {error}"
            )
            return imported, skipped

        for location, analysis_type, error in reader.errors:
            log.error(
                f"Could not read Rekordbox {analysis_type} analysis for {location}: "
                f"{type(error).__name__}: {error}"
            )
        log.info(f"Rekordbox analysis streamed: {imported + skipped}")
        return imported, skipped

    @staticmethod
    def _normalise_path(path):
        return str(Path(path)).replace("\\", "/").casefold()

    @staticmethod
    def _module_is_current(document, module_name, version):
        status = document.get("system", {}).get("modules", {}).get(module_name, {})
        return status.get("completed") is True and status.get("version") == version

    @staticmethod
    def _mark_module_complete(document, module_name, version):
        modules = document.setdefault("system", {}).setdefault("modules", {})
        modules[module_name] = {
            "version": version,
            "completed": True,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
