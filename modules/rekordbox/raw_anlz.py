from pathlib import Path
from struct import unpack


class RawAnlzParser:
    """Read stable ANLZ blocks without depending on pyrekordbox tag support."""

    def parse_beat_grid(self, file_path):
        """Return the PQTZ beat grid stored in a DAT file, if present."""
        data = Path(file_path).read_bytes()
        for offset, tag_name, header_length, tag_length in self._tags(data):
            if tag_name != b"PQTZ" or header_length < 24:
                continue
            count = unpack(">I", data[offset + 20 : offset + 24])[0]
            entries_offset = offset + header_length
            entries_end = entries_offset + count * 8
            if entries_end > offset + tag_length:
                return None
            entries = [
                unpack(">HHI", data[position : position + 8])
                for position in range(entries_offset, entries_end, 8)
            ]
            return {
                "beatNumbers": [beat for beat, _tempo, _time in entries],
                "bpms": [tempo / 100 for _beat, tempo, _time in entries],
                "beatPositions": [time / 1000 for _beat, _tempo, time in entries],
            }
        return None

    @staticmethod
    def _tags(data):
        if data[:4] != b"PMAI" or len(data) < 8:
            return
        offset = unpack(">I", data[4:8])[0]
        while offset + 12 <= len(data):
            tag_name = data[offset : offset + 4]
            header_length, tag_length = unpack(">II", data[offset + 4 : offset + 12])
            if header_length < 12 or tag_length < header_length or offset + tag_length > len(data):
                return
            yield offset, tag_name, header_length, tag_length
            offset += tag_length
