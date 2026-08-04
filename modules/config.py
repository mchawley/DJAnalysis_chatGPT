import json
from pathlib import Path
class Config:
    def __init__(self,path='config/config.json'):
        self.data=json.loads(Path(path).read_text())

    def module_enabled(self, name, default=True):
        """Return a module's explicit configuration flag, defaulting safely."""
        return bool(self.data.get("modules", {}).get(name, default))
