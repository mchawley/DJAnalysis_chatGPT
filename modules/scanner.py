from pathlib import Path
from models.track import Track
class Scanner:
    def __init__(self,root,fmts):
        self.root=Path(root); self.fmts=tuple(f.lower() for f in fmts)
    def scan(self):
        if not self.root.exists(): return []
        return [Track(str(f),f.name,f.suffix.lower()) for f in self.root.rglob('*') if f.is_file() and f.suffix.lower() in self.fmts]
