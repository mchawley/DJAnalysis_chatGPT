from modules.config import Config
from modules.logger import Logger
from modules.scanner import Scanner
from modules.registry import Registry
from modules.json_manager import JsonManager
from modules.manifest import ManifestManager
from datetime import datetime

class Pipeline:
    def run(self):
        cfg=Config().data
        log=Logger()
        scanner=Scanner(cfg['musicRoot'],cfg['supportedFormats'])
        jm=JsonManager(cfg['outputRoot'])
        manifest_manager = ManifestManager(cfg['outputRoot'])
        previous_tracks = manifest_manager.load()['tracks']
        tracks=scanner.scan()
        current_tracks = {}
        processed=0
        states = {"new": 0, "modified": 0, "moved": 0, "unchanged": 0}
        replaced_track_ids = set()
        previous_ids_by_path = {
            entry.get("path"): track_id
            for track_id, entry in previous_tracks.items()
        }
        log.info(f'Found {len(tracks)} tracks')
        for t in tracks:
            tid=Registry.content_hash(t.path)
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
            system.setdefault("createdAt", datetime.utcnow().isoformat() + "Z")
            system["sourcePath"] = t.path
            system.setdefault("schemaVersion", "0.1")
            jm.save(tid,doc)
            current_tracks[tid] = entry
            states[state] += 1
            processed+=1

        deleted = set(previous_tracks) - set(current_tracks) - replaced_track_ids
        manifest_manager.save(current_tracks)

        log.info(f'Documents updated : {processed}')
        log.info(f'New               : {states["new"]}')
        log.info(f'Modified          : {states["modified"]}')
        log.info(f'Moved             : {states["moved"]}')
        log.info(f'Unchanged         : {states["unchanged"]}')
        log.info(f'Deleted           : {len(deleted)}')
