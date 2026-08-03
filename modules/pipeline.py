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
from datetime import datetime, timezone
from pathlib import Path
from tqdm import tqdm

class Pipeline:
    def run(self):
        cfg=Config().data
        log=Logger()
        scanner=Scanner(cfg['musicRoot'],cfg['supportedFormats'])
        jm=JsonManager(cfg['outputRoot'])
        manifest_manager = ManifestManager(cfg['outputRoot'])
        metadata_plugin = MetadataPlugin()
        rekordbox_matcher = self._load_rekordbox_matcher(cfg.get("rekordboxXmlPath"), log)
        rekordbox_importer = RekordboxImporter()
        previous_tracks = manifest_manager.load()['tracks']
        tracks=scanner.scan()
        current_tracks = {}
        processed=0
        metadata_updated = 0
        metadata_failed = 0
        rekordbox_imported = 0
        rekordbox_unmatched = 0
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
                if rekordbox_matcher:
                    rekordbox_match = rekordbox_matcher.match(t, doc)
                    if rekordbox_match.track:
                        rekordbox_importer.import_track(doc, rekordbox_match.track)
                        rekordbox_imported += 1
                    else:
                        rekordbox_unmatched += 1
                jm.save(tid,doc)
                current_tracks[tid] = entry
                states[state] += 1
                processed+=1

        deleted = set(previous_tracks) - set(current_tracks) - replaced_track_ids
        manifest_manager.save(current_tracks)

        log.info(f'Documents updated : {processed}')
        log.info(f'Metadata updated   : {metadata_updated}')
        log.info(f'Metadata failed    : {metadata_failed}')
        if rekordbox_matcher:
            log.info(f'Rekordbox imported: {rekordbox_imported}')
            log.info(f'Rekordbox unmatched: {rekordbox_unmatched}')
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
