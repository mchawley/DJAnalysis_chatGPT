import json
from pathlib import Path
class JsonManager:
    def __init__(self,out):
        self.out=Path(out); self.out.mkdir(parents=True,exist_ok=True)
    def exists(self,track_id):
        return (self.out/f'{track_id}.json').exists()
    def save(self,track_id,data):
        (self.out/f'{track_id}.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
