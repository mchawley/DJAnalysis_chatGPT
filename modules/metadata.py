from mutagen import File

class MetadataExtractor:
    """
    Wrapper around Mutagen that works for MP3, FLAC, WAV, AIFF and M4A.
    Returns a normalized dictionary regardless of container format.
    """

    TAG_MAP = {
        "title": ["TIT2","TITLE","\xa9nam"],
        "artist":["TPE1","ARTIST","\xa9ART","aART"],
        "album":["TALB","ALBUM","\xa9alb"],
        "genre":["TCON","GENRE","\xa9gen"]
    }

    def _first(self,audio,keys):
        if audio is None or audio.tags is None:
            return None
        for key in keys:
            try:
                value = audio.tags[key]
            except (KeyError, TypeError, ValueError):
                continue
            try:
                if isinstance(value,list):
                    return str(value[0])
                if hasattr(value,"text"):
                    return str(value.text[0])
                return str(value)
            except Exception:
                return str(value)
        return None

    def extract(self,path):
        audio=File(path)
        if audio is None:
            return {}

        info=getattr(audio,"info",None)

        return {
            "title":self._first(audio,self.TAG_MAP["title"]),
            "artist":self._first(audio,self.TAG_MAP["artist"]),
            "album":self._first(audio,self.TAG_MAP["album"]),
            "genre":self._first(audio,self.TAG_MAP["genre"]),
            "duration":round(getattr(info,"length",0),2) if info else None,
            "bitrate":getattr(info,"bitrate",None),
            "sampleRate":getattr(info,"sample_rate",None),
            "channels":getattr(info,"channels",None),
            "codec":audio.__class__.__name__
        }
