from pathlib import Path
from models.track import Track


class Scanner:
    def __init__(self, roots, fmts):
        if isinstance(roots, (str, Path)):
            roots = [roots]
        self.roots = [Path(root) for root in roots]
        self.fmts = tuple(fmt.lower() for fmt in fmts)

    def scan(self):
        files = []
        seen_files = set()
        seen_roots = set()
        for root in self.roots:
            resolved_root = root.resolve()
            if resolved_root in seen_roots or not root.exists():
                continue
            seen_roots.add(resolved_root)
            for file_path in root.rglob("*"):
                if not file_path.is_file() or file_path.suffix.lower() not in self.fmts:
                    continue
                resolved_file = file_path.resolve()
                if resolved_file in seen_files:
                    continue
                seen_files.add(resolved_file)
                files.append(file_path)
        return [Track(str(file_path), file_path.name, file_path.suffix.lower()) for file_path in sorted(files)]
