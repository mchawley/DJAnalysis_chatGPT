from modules.config import Config
from modules.logger import Logger
from modules.scanner import Scanner
from modules.registry import Registry
from modules.json_manager import JsonManager
from datetime import datetime

class Pipeline:
    def run(self):
        cfg=Config().data
        log=Logger()
        scanner=Scanner(cfg['musicRoot'],cfg['supportedFormats'])
        jm=JsonManager(cfg['outputRoot'])
        tracks=scanner.scan()
        processed=0
        log.info(f'Found {len(tracks)} tracks')
        for t in tracks:
            tid=Registry.content_hash(t.path)
            doc = jm.load(tid)
            system = doc.setdefault("system", {})
            system.setdefault("trackId", tid)
            system.setdefault("createdAt", datetime.utcnow().isoformat() + "Z")
            system["sourcePath"] = t.path
            system.setdefault("schemaVersion", "0.1")
            jm.save(tid,doc)
            processed+=1
        log.info(f'Documents updated : {processed}')
