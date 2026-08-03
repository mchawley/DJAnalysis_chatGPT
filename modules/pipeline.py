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
        skipped=0
        log.info(f'Found {len(tracks)} tracks')
        for t in tracks:
            tid=Registry.content_hash(t.path)
            if jm.exists(tid):
                skipped+=1
                continue
            doc={
                "metadata":{},
                "rekordbox":{},
                "audio":{},
                "structure":{},
                "features":{},
                "energy":{},
                "dj":{},
                "system":{
                    "trackId":tid,
                    "sourcePath":t.path,
                    "createdAt":datetime.utcnow().isoformat()+"Z",
                    "schemaVersion":"0.1"
                }
            }
            jm.save(tid,doc)
            processed+=1
        log.info(f'New JSONs : {processed}')
        log.info(f'Skipped   : {skipped}')
