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
from modules.rekordbox.anlz import RekordboxAnlzParser
from datetime import datetime, timezone
from pathlib import Path
from tqdm import tqdm

class Pipeline:
    REKORDBOX_LIBRARY_VERSION = "1.0"
    REKORDBOX_ANALYSIS_VERSION = "1.0"

    def run(self):
        cfg=Config().data
        log=Logger()
        scanner=Scanner(cfg['musicRoot'],cfg['supportedFormats'])
        jm=JsonManager(cfg['outputRoot'])
        manifest_manager = ManifestManager(cfg['outputRoot'])
        metadata_plugin = MetadataPlugin()
        rekordbox_xml_path = cfg.get("rekordboxXmlPath")
        rekordbox_matcher = None
        rekordbox_xml_loaded = False
        rekordbox_importer = RekordboxImporter()
        rekordbox_analyses = self._load_rekordbox_analyses(cfg.get("rekordboxAnlzRoot"), log)
        analysis_importer = RekordboxAnalysisImporter()
        previous_tracks = manifest_manager.load()['tracks']
        tracks=scanner.scan()
        current_tracks = {}
        processed=0
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

                doc = jm.load(tid)
                system = doc.setdefault("system", {})
                system.setdefault("trackId", tid)
                system.setdefault(
                    "createdAt",
                    datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                )
                system["sourcePath"] = t.path
                system.setdefault("schemaVersion", "0.1")
                if metadata_plugin.needs_processing(doc, t):
                    try:
                        metadata_plugin.process(doc, t)
                        metadata_updated += 1
                    except Exception as error:
                        metadata_failed += 1
                        progress.write(
                            f"[ERROR] Metadata failed for {t.path}: "
                            f"{type(error).__name__}: {error}"
                        )
                if rekordbox_xml_path and not self._module_is_current(
                    doc, "rekordbox_library", self.REKORDBOX_LIBRARY_VERSION
                ):
                    if not rekordbox_xml_loaded:
                        rekordbox_matcher = self._load_rekordbox_matcher(rekordbox_xml_path, log)
                        rekordbox_xml_loaded = True
                    if rekordbox_matcher:
                        rekordbox_match = rekordbox_matcher.match(t, doc)
                        if rekordbox_match.track:
                            rekordbox_importer.import_track(doc, rekordbox_match.track)
                            self._mark_module_complete(
                                doc, "rekordbox_library", self.REKORDBOX_LIBRARY_VERSION
                            )
                            rekordbox_imported += 1
                        else:
                            rekordbox_unmatched += 1
                elif rekordbox_xml_path:
                    rekordbox_skipped += 1
                analysis = rekordbox_analyses.get(self._normalise_path(t.path))
                if analysis and not self._module_is_current(
                    doc, "rekordbox_analysis", self.REKORDBOX_ANALYSIS_VERSION
                ):
                    analysis_importer.import_analysis(doc, analysis)
                    self._mark_module_complete(
                        doc, "rekordbox_analysis", self.REKORDBOX_ANALYSIS_VERSION
                    )
                    analysis_imported += 1
                elif analysis:
                    analysis_skipped += 1
                jm.save(tid,doc)
                current_tracks[tid] = entry
                states[state] += 1
                processed+=1

        deleted = set(previous_tracks) - set(current_tracks) - replaced_track_ids
        manifest_manager.save(current_tracks)

        log.info(f'Documents updated : {processed}')
        log.info(f'Metadata updated   : {metadata_updated}')
        log.info(f'Metadata failed    : {metadata_failed}')
        if rekordbox_xml_path:
            log.info(f'Rekordbox imported: {rekordbox_imported}')
            log.info(f'Rekordbox unmatched: {rekordbox_unmatched}')
            log.info(f'Rekordbox skipped  : {rekordbox_skipped}')
        if rekordbox_analyses:
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

    @classmethod
    def _load_rekordbox_analyses(cls, anlz_root, log):
        if not anlz_root:
            return {}
        path = Path(anlz_root).expanduser()
        if not path.is_dir():
            log.error(f"Rekordbox ANLZ directory does not exist: {anlz_root}")
            return {}
        try:
            parser = RekordboxAnlzParser()
            analyses = parser.parse_directory(path)
        except Exception as error:
            log.error(
                f"Could not read Rekordbox ANLZ files at {anlz_root}: "
                f"{type(error).__name__}: {error}"
            )
            return {}

        for file_path, error in parser.errors:
            log.error(
                f"Could not read Rekordbox ANLZ file {file_path}: "
                f"{type(error).__name__}: {error}"
            )
        log.info(f"Loaded {len(analyses)} Rekordbox analysis records")
        return {cls._normalise_path(path): analysis for path, analysis in analyses.items()}

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
