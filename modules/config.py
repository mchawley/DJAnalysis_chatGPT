import json
from pathlib import Path
class Config:
    def __init__(self,path='config/config.json'):
        self.data=json.loads(Path(path).read_text())
