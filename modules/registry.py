import hashlib
from pathlib import Path
class Registry:
    @staticmethod
    def content_hash(path):
        h=hashlib.sha256()
        with open(path,'rb') as f:
            for chunk in iter(lambda:f.read(1024*1024),b''):
                h.update(chunk)
        return h.hexdigest()
