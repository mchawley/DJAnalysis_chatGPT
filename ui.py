"""Local, read-only browser UI for fingerprint validation and similarity."""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from modules.fingerprint import FingerprintSimilarityEngine, FingerprintValidator


HTML = """<!doctype html><html><head><meta charset=utf-8><title>CrateIQ Insights</title>
<style>body{font:16px system-ui;margin:2rem;max-width:1100px}select,button{padding:.5rem;margin:.25rem}table{border-collapse:collapse;width:100%}td,th{padding:.6rem;border-bottom:1px solid #ddd;text-align:left}.score{font-weight:700}.card{background:#f5f5f7;padding:1rem;border-radius:.6rem;margin:1rem 0}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:.5rem}.label{color:#666;font-size:.8rem}.timeline{display:flex;width:100%;height:64px;margin:1rem 0}.part{min-width:2px;border-right:2px solid white;padding:6px;box-sizing:border-box;font-size:11px;overflow:hidden;cursor:pointer}.part.selected{outline:3px solid #111;z-index:1}.INTRO{background:#bfd7ff}.GROOVE{background:#c9efd4}.BUILD{background:#ffe5a8}.DROP{background:#ffb9b9}.BREAKDOWN{background:#e3cdf7}.OUTRO{background:#cbd0d8}.CUSTOM{background:#ddd}</style></head>
<body><h1>CrateIQ Insights</h1><p id=summary>Loading…</p><h2>Track Inspector</h2><select id=track></select><div id=inspector class=card>Select a track.</div><h2>Find similar segments</h2><button onclick=search()>Find matches</button><table><thead><tr><th>Score</th><th>Track</th><th>Segment</th><th>Type</th><th>Why similar</th></tr></thead><tbody id=matches></tbody></table>
<script>
let tracks=[],selectedSegment=0;fetch('/api/tracks').then(r=>r.json()).then(x=>{tracks=x;let s=track; x.forEach(t=>s.add(new Option(t.title,t.id)));loadSegments();});
fetch('/api/summary').then(r=>r.json()).then(x=>summary.textContent=`${x.tracks} tracks · load a track to inspect its segments`);
track.onchange=loadSegments;function loadSegments(){selectedSegment=0;inspect()}
function inspect(index=selectedSegment){selectedSegment=index;fetch(`/api/track?track_id=${track.value}&segment_index=${index}`).then(r=>r.json()).then(x=>{let f=x.fingerprint||{}, end=Math.max(...x.timeline.map(s=>s.end_time),1), line=x.timeline.map((s,i)=>`<div onclick="inspect(${i})" class="part ${s.segment} ${i===selectedSegment?'selected':''}" style="width:${100*(s.end_time-s.start_time)/end}%" title="${s.segment}: ${s.start_time.toFixed(1)}s–${s.end_time.toFixed(1)}s">${s.segment}<br>${s.start_time.toFixed(0)}s</div>`).join(''); inspector.innerHTML=`<b>${x.title||''}</b> · ${x.artist||''}<div class=timeline>${line}</div><div class=grid><div><span class=label>BPM</span><br>${x.bpm??'—'}</div><div><span class=label>Key</span><br>${x.key??'—'}</div><div><span class=label>Segment</span><br>${f.segment??'—'} · ${f.duration?.toFixed(1)??'—'}s</div><div><span class=label>Energy</span><br>${f.energy?.overall?.toFixed(3)??'—'}</div><div><span class=label>Bass</span><br>${f.bass?.overall?.toFixed(3)??'—'}</div><div><span class=label>Brightness</span><br>${f.spectrum?.spectral_centroid?.toFixed(0)??'—'} Hz</div></div>`})}
function search(){fetch(`/api/similar?track_id=${track.value}&segment_index=${selectedSegment}`).then(r=>r.json()).then(x=>matches.innerHTML=x.map(m=>`<tr><td class=score>${m.score.toFixed(3)}</td><td>${m.title}</td><td>#${m.segment_index}</td><td>${m.segment}</td><td>${m.reasons.join(', ')}</td></tr>`).join(''))}
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
        if request.path == "/api/track":
            query = parse_qs(request.query); track_id = query.get("track_id", [""])[0]; index = int(query.get("segment_index", ["0"])[0])
            path = self.output_root / f"{track_id}.json"
            if not path.exists(): return self._json({})
            doc = json.loads(path.read_text()); fingerprints = doc.get("analysis", {}).get("fingerprints", [])
            return self._json({"title": doc.get("metadata", {}).get("title"), "artist": doc.get("metadata", {}).get("artist"), "bpm": doc.get("library", {}).get("bpm"), "key": doc.get("library", {}).get("key"), "fingerprint": fingerprints[index] if 0 <= index < len(fingerprints) else {}, "timeline": [{"segment": item.get("segment", "CUSTOM"), "start_time": item.get("start_time", 0), "end_time": item.get("end_time", 0)} for item in fingerprints]})
        if request.path == "/api/similar":
            items, documents = self._items()
            query = parse_qs(request.query); track_id = query.get("track_id", [""])[0]; index = int(query.get("segment_index", ["0"])[0])
            target = next((item for item in items if item["track_id"] == track_id and item["segment_index"] == index), None)
            if target is None: return self._json([])
            engine = FingerprintSimilarityEngine().fit(items)
            return self._json([{"score": match.score, "track_id": match.track_id, "segment_index": match.segment_index, "segment": match.fingerprint.get("segment"), "reasons": match.reasons, "title": documents[match.track_id].get("metadata", {}).get("title", match.track_id)} for match in engine.nearest_neighbors(target, items)])
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
