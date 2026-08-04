"""Local, read-only browser UI for fingerprint validation and similarity."""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from modules.fingerprint import FingerprintSimilarityEngine, FingerprintValidator


HTML = """<!doctype html><html><head><meta charset=utf-8><title>CrateIQ Insights</title>
<style>body{font:16px system-ui;margin:2rem;max-width:1000px}select,button{padding:.5rem;margin:.25rem}table{border-collapse:collapse;width:100%}td,th{padding:.6rem;border-bottom:1px solid #ddd;text-align:left}.score{font-weight:700}</style></head>
<body><h1>CrateIQ Insights</h1><p id=summary>Loading…</p><h2>Find similar segments</h2><select id=track></select><select id=segment></select><button onclick=search()>Find matches</button><table><thead><tr><th>Score</th><th>Track</th><th>Segment</th><th>Type</th></tr></thead><tbody id=matches></tbody></table>
<script>
let tracks=[];fetch('/api/tracks').then(r=>r.json()).then(x=>{tracks=x;let s=track; x.forEach(t=>s.add(new Option(t.title,t.id)));loadSegments();});
fetch('/api/summary').then(r=>r.json()).then(x=>summary.textContent=`${x.tracks} tracks · load a track to inspect its segments`);
track.onchange=loadSegments;function loadSegments(){fetch(`/api/segments?track_id=${track.value}`).then(r=>r.json()).then(x=>{segment.innerHTML='';x.forEach(s=>segment.add(new Option(`#${s.index} · ${s.type}`,s.index)))})}
function search(){fetch(`/api/similar?track_id=${track.value}&segment_index=${segment.value}`).then(r=>r.json()).then(x=>matches.innerHTML=x.map(m=>`<tr><td class=score>${m.score.toFixed(3)}</td><td>${m.title}</td><td>#${m.segment_index}</td><td>${m.segment}</td></tr>`).join(''))}
</script></body></html>"""


class InsightsHandler(BaseHTTPRequestHandler):
    output_root = Path("output/tracks")
    similarity_cache = None

    def do_GET(self):
        request = urlparse(self.path)
        if request.path == "/": return self._send(HTML, "text/html")
        if request.path == "/api/summary":
            return self._json({"tracks": len(self._catalog())})
        if request.path == "/api/tracks":
            return self._json(self._catalog())
        if request.path == "/api/segments":
            track_id = parse_qs(request.query).get("track_id", [""])[0]
            path = self.output_root / f"{track_id}.json"
            if not path.exists(): return self._json([])
            doc = json.loads(path.read_text())
            return self._json([{"index": i, "type": value.get("segment", "CUSTOM")} for i, value in enumerate(doc.get("analysis", {}).get("fingerprints", []))])
        if request.path == "/api/similar":
            items, documents = self._items()
            query = parse_qs(request.query); track_id = query.get("track_id", [""])[0]; index = int(query.get("segment_index", ["0"])[0])
            target = next((item for item in items if item["track_id"] == track_id and item["segment_index"] == index), None)
            if target is None: return self._json([])
            engine = FingerprintSimilarityEngine().fit(items)
            return self._json([{"score": match.score, "track_id": match.track_id, "segment_index": match.segment_index, "segment": match.fingerprint.get("segment"), "title": documents[match.track_id].get("metadata", {}).get("title", match.track_id)} for match in engine.nearest_neighbors(target, items)])
        self.send_error(404)

    def _items(self):
        if self.similarity_cache is not None: return self.similarity_cache
        documents, items = {}, []
        for path in self.output_root.glob("*.json"):
            doc = json.loads(path.read_text()); track_id = doc["system"]["trackId"]; documents[track_id] = doc
            items.extend({"track_id": track_id, "segment_index": index, "fingerprint": fingerprint} for index, fingerprint in enumerate(doc.get("analysis", {}).get("fingerprints", [])))
        self.similarity_cache = (items, documents)
        return self.similarity_cache
    def _catalog(self):
        manifest = self.output_root.parent / "tracks_manifest.json"
        if manifest.exists():
            tracks = json.loads(manifest.read_text()).get("tracks", {})
            return [{"id": track_id, "title": Path(entry.get("path", track_id)).stem} for track_id, entry in tracks.items()]
        return [{"id": path.stem, "title": path.stem} for path in self.output_root.glob("*.json")]
    def _json(self, value): self._send(json.dumps(value), "application/json")
    def _send(self, content, content_type):
        encoded = content.encode(); self.send_response(200); self.send_header("Content-Type", content_type); self.send_header("Content-Length", str(len(encoded))); self.end_headers(); self.wfile.write(encoded)
    def log_message(self, *_): pass


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--output", default="output/tracks"); parser.add_argument("--port", type=int, default=8765); args = parser.parse_args()
    InsightsHandler.output_root = Path(args.output)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), InsightsHandler)
    print(f"CrateIQ Insights: http://127.0.0.1:{args.port}")
    server.serve_forever()


if __name__ == "__main__": main()
