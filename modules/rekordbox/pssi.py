from pathlib import Path
from struct import unpack


class PssiParser:
    """Read the stable header and phrase-entry fields of a PSSI ANLZ tag."""

    TAG_NAME = b"PSSI"

    def parse_file(self, file_path):
        data = Path(file_path).read_bytes()
        if data[:4] != b"PMAI":
            return None
        offset = unpack(">I", data[4:8])[0]
        while offset + 12 <= len(data):
            tag_name = data[offset : offset + 4]
            header_length, tag_length = unpack(">II", data[offset + 4 : offset + 12])
            if tag_length < header_length or offset + tag_length > len(data):
                return None
            if tag_name == self.TAG_NAME:
                return self._parse_tag(data[offset : offset + tag_length], header_length)
            offset += tag_length
        return None

    @staticmethod
    def _parse_tag(data, header_length):
        if header_length < 32 or len(data) < header_length:
            return None
        entry_size = unpack(">I", data[12:16])[0]
        if entry_size < 6:
            return None
        end_beat = unpack(">I", data[24:28])[0]
        phrases = []
        for offset in range(header_length, len(data) - entry_size + 1, entry_size):
            index, start_beat, kind = unpack(">HHH", data[offset : offset + 6])
            phrases.append(
                {"index": index, "startBeat": start_beat, "kind": kind}
            )
        return {"endBeat": end_beat, "entrySize": entry_size, "phrases": phrases}
