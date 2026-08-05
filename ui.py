"""Local, read-only browser UI for fingerprint validation and similarity."""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from modules.fingerprint import FingerprintSimilarityEngine, FingerprintValidator


HTML = """<!doctype html><html><head><meta charset=utf-8><title>CrateIQ Insights</title><style>
:root{--bg:#0b1020;--panel:#151d32;--line:#28334f;--muted:#9aa6bf;--text:#edf2ff;--cyan:#54d5ff;--low:#54d5ff;--mid:#f6c967;--high:#ff7285;--neutral:#526079}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px system-ui}.shell{width:min(1600px,96vw);margin:auto;padding:28px 0 60px}.top{display:flex;justify-content:space-between;align-items:end;border-bottom:1px solid var(--line);padding-bottom:22px}.eyebrow{color:var(--cyan);font-size:12px;letter-spacing:.13em;text-transform:uppercase}h1{margin:4px 0;font-size:34px}select,button{background:#1b2740;color:var(--text);border:1px solid #3c4d72;border-radius:8px;padding:10px 12px}select{min-width:340px}button{cursor:pointer;background:var(--cyan);color:#06101b;font-weight:700}.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px;margin-top:20px}.hero{display:flex;justify-content:space-between;gap:20px}.title{font-size:22px;font-weight:700}.muted{color:var(--muted)}.stats{display:flex;gap:28px}.stats b{display:block;font-size:20px}.timeline{display:flex;width:100%;height:94px;margin:22px 0 8px;border-radius:8px;overflow:hidden;background:#202a40}.part{min-width:3px;border-right:2px solid #0b1020;padding:9px 8px;color:#0b1020;font-size:11px;font-weight:800;overflow:hidden;cursor:pointer}.part.selected{outline:3px solid white;z-index:1}.INTRO{background:#74b6ff}.GROOVE{background:#71d69b}.BUILD{background:#f6c967}.DROP{background:#ff808d}.BREAKDOWN{background:#ba8df5}.OUTRO{background:#a9b4c8}.CUSTOM{background:#72809a}.legend{display:flex;gap:14px;color:var(--muted);font-size:12px}.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:5px}.deck{display:grid;grid-template-columns:1.3fr .7fr;gap:20px}.chart{height:155px;width:100%;background:#0f1628;border-radius:10px}.chart-note{font-size:12px;line-height:1.4;margin:8px 2px 0}.chart-note b{color:var(--text)}.charts{display:grid;grid-template-columns:1fr 1fr;gap:14px}.metric-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}.metric{background:#10182a;border-radius:10px;padding:13px}.metric h3{margin:0 0 10px;font-size:13px}.row{display:grid;grid-template-columns:80px 1fr 50px;gap:8px;align-items:center;font-size:12px;margin:8px 0}.bar{height:8px;background:#28334f;border-radius:99px;overflow:hidden}.fill{height:100%;border-radius:99px}.fill.low{background:var(--low)}.fill.mid{background:var(--mid)}.fill.high{background:var(--high)}.fill.neutral{background:var(--neutral)}.tag{grid-column:2/4;color:var(--muted);font-size:11px}.matches{display:grid;gap:10px;margin-top:12px}.match{display:flex;justify-content:space-between;gap:16px;background:#10182a;border-radius:10px;padding:13px;cursor:pointer}.match:hover{outline:1px solid var(--cyan)}@media(max-width:850px){.deck,.charts{grid-template-columns:1fr}.top,.hero{display:block}.stats{margin-top:15px}select{width:100%}}
</style></head><body><main class=shell><header class=top><div><div class=eyebrow>Track analysis deck</div><h1>CrateIQ Insights</h1><div id=summary class=muted>Loading library…</div></div><select id=track></select></header><section id=deck></section></main><script>
let selected=0;const $=id=>document.getElementById(id);const fmt=v=>typeof v==='number'?(Math.abs(v)>=100?Math.round(v).toString():v.toFixed(2)):'—';const time=v=>typeof v==='number'?v.toFixed(1):'—';fetch('/api/tracks').then(r=>r.json()).then(xs=>{xs.forEach(x=>$('track').add(new Option(x.title,x.id)));load()});fetch('/api/summary').then(r=>r.json()).then(x=>$('summary').textContent=`${x.tracks} analyzed tracks · select a section to compare`);$('track').onchange=()=>{selected=0;load()};function meter(label,item,key){let v=item.features[key],m=item.meters[key]||{percent:0,tone:'neutral'};return `<div class=row><span>${label}</span><span class=bar><span class="fill ${m.tone}" style="width:${m.percent}%"></span></span><b>${fmt(v?.value)}</b><span class=tag>${v?.track??'—'} track · ${v?.absolute??'—'} absolute</span></div>`}function chart(values,color){let w=400,h=150,max=Math.max(...values,1),last=Math.max(values.length-1,1),pts=values.map((v,i)=>`${i*w/last},${h-v/max*(h-10)-5}`).join(' ');return `<svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none"><polyline fill="none" stroke="${color}" stroke-width="3" points="${pts}"/></svg>`}function chartPanel(label,values,color,meaning,summary){return `<div><p class=muted>${label}</p><div class=chart>${chart(values,color)}</div><p class="muted chart-note"><b>${summary}</b><br>${meaning}</p></div>`}function load(i=selected){selected=i;fetch(`/api/track?track_id=${$('track').value}&segment_index=${i}`).then(r=>r.json()).then(x=>{let s=x.segment,t=x.timeline,end=Math.max(...t.map(a=>a.end),1);let line=t.map((a,n)=>`<div onclick="load(${n})" class="part ${a.type} ${n===selected?'selected':''}" style="width:${100*(a.end-a.start)/end}%" title="${a.type}: ${time(a.start)}–${time(a.end)} seconds">${a.duration>10?a.type:''}<br>${time(a.start)}s</div>`).join('');$('deck').innerHTML=`<section class=panel><div class=hero><div><div class=title>${x.title||'Untitled'} <span class=muted>· ${x.artist||'Unknown artist'}</span></div><div class=muted>${fmt(x.bpm)} BPM · ${x.key??'—'} · ${t.length} sections</div></div><div class=stats><div><span class=muted>Selected</span><b>${s.type}</b></div><div><span class=muted>Timing</span><b>${time(s.start)}–${time(s.end)}s</b></div><div><span class=muted>Bars</span><b>${fmt(s.bars)}</b></div></div></div><div class=timeline>${line}</div><div class=legend><span><i class="dot INTRO"></i>Intro</span><span><i class="dot GROOVE"></i>Groove</span><span><i class="dot BUILD"></i>Build</span><span><i class="dot DROP"></i>Drop</span><span><i class="dot BREAKDOWN"></i>Breakdown</span><span><i class="dot OUTRO"></i>Outro</span></div></section><section class=deck><div><section class=panel><div class=eyebrow>Energy & momentum</div><div class=charts>${chartPanel('RMS energy',s.charts.rms,'#54d5ff','Loudness over time: a rising line builds energy, a flat line stays steady, and dips ease down.',s.charts.rms_summary)}${chartPanel('Onset strength',s.charts.onset,'#f6c967','Transient activity over time: frequent peaks suggest dense percussion; isolated peaks are accents or hits.',s.charts.onset_summary)}</div></section><section class=panel><div class=eyebrow>Segment profile</div><div class=metric-grid><div class=metric><h3>Energy</h3>${meter('Overall',s,'energy')}${meter('Slope',s,'slope')}${meter('Crest',s,'crest')}</div><div class=metric><h3>Bass</h3>${meter('Bass',s,'bass')}${meter('Kick',s,'kick')}${meter('Transient',s,'transient')}</div><div class=metric><h3>Rhythm</h3>${meter('Density',s,'rhythm')}${meter('Groove',s,'groove')}${meter('Syncopation',s,'syncopation')}</div><div class=metric><h3>Spectrum & harmony</h3>${meter('Brightness',s,'brightness')}<div class=row><span>Key</span><b>${s.harmony.key||'—'}</b></div><div class=row><span>Mode</span><b>${s.harmony.mode||'—'}</b></div></div></div></section></div><aside><section class=panel><div class=eyebrow>Similarity decision</div><p>Compare this <b>${s.type}</b> segment against the library.</p><button onclick="similar()">Find similar segments</button><div id=matches class=matches><p class=muted>Matches load on demand.</p></div></section></aside></section>`})}function similar(){let box=$('matches');box.innerHTML='<p class=muted>Comparing normalized fingerprints…</p>';fetch(`/api/similar?track_id=${$('track').value}&segment_index=${selected}`).then(r=>r.json()).then(xs=>box.innerHTML=xs.map(m=>`<div class=match onclick="$('track').value='${m.track_id}';selected=${m.segment_index};load()"><div><b>${m.title||'Untitled'}</b><br><span class=muted>${m.segment} · ${m.reasons.join(', ')}</span></div><b>${fmt(m.score)}</b></div>`).join(''))}</script></body></html>"""


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
            selected = fingerprints[index] if 0 <= index < len(fingerprints) else {}
            paths = {"energy": "energy.overall", "slope": "energy.slope", "crest": "energy.crest_factor", "bass": "bass.overall", "kick": "bass.kick", "transient": "bass.transient_strength", "rhythm": "rhythm.density", "groove": "rhythm.groove", "syncopation": "rhythm.syncopation", "confidence": "harmonic.confidence", "brightness": "spectrum.spectral_centroid", "flatness": "spectrum.spectral_flatness"}
            features = {name: {"value": self._round(self._value(selected, path)), "track": self._range_label(selected, fingerprints, path), "absolute": self._absolute_label(name, self._value(selected, path))} for name, path in paths.items()}
            rms = self._downsample(selected.get("raw_features", {}).get("rms", []))
            onset = self._downsample(selected.get("raw_features", {}).get("onset_strength", []))
            return self._json({"title": doc.get("metadata", {}).get("title"), "artist": doc.get("metadata", {}).get("artist"), "bpm": doc.get("library", {}).get("bpm"), "key": doc.get("library", {}).get("key"), "segment": {"type": selected.get("segment", "CUSTOM"), "start": selected.get("start_time", 0), "end": selected.get("end_time", 0), "bars": selected.get("bars", 0), "harmony": selected.get("harmonic", {}), "features": features, "meters": {name: self._meter(value["track"], value["absolute"]) for name, value in features.items()}, "charts": {"rms": rms, "onset": onset, "rms_summary": self._rms_summary(rms), "onset_summary": self._onset_summary(onset)}}, "timeline": [{"type": item.get("segment", "CUSTOM"), "start": item.get("start_time", 0), "end": item.get("end_time", 0), "duration": item.get("duration", 0)} for item in fingerprints]})
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
    @staticmethod
    def _range_label(selected, fingerprints, path):
        def value(item):
            for key in path.split("."): item = item.get(key) if isinstance(item, dict) else None
            return item
        current = value(selected); values = sorted(value(item) for item in fingerprints if isinstance(value(item), (int, float)))
        if current is None or not values: return "—"
        rank = sum(number <= current for number in values) / len(values)
        return "Low" if rank < .33 else "High" if rank > .67 else "Mid"
    @staticmethod
    def _value(item, path):
        for key in path.split("."): item = item.get(key) if isinstance(item, dict) else None
        return item
    @staticmethod
    def _absolute_label(name, value):
        if not isinstance(value, (int, float)): return "—"
        if name == "slope":
            return "Falling" if value < -0.001 else "Rising" if value > 0.001 else "Stable"
        if name == "crest":
            return "Compact" if value < 1.25 else "Dynamic" if value > 2.0 else "Balanced"
        thresholds = {"energy": (.03, .1), "bass": (.15, .35), "kick": (.08, .25), "transient": (.05, .2), "rhythm": (.1, .5), "groove": (.33, .67), "syncopation": (.33, .67), "brightness": (1200, 2500), "flatness": (.1, .35), "confidence": (.33, .67)}
        if name not in thresholds: return "—"
        low, high = thresholds[name]
        return "Low" if value < low else "High" if value > high else "Mid"
    @staticmethod
    def _meter(track, absolute):
        state = absolute if absolute != "—" else track
        meters = {
            "Low": (33, "low"), "Falling": (33, "low"), "Compact": (33, "low"),
            "Mid": (66, "mid"), "Stable": (66, "mid"), "Balanced": (66, "mid"),
            "High": (100, "high"), "Rising": (100, "high"), "Dynamic": (100, "high"),
        }
        percent, tone = meters.get(state, (0, "neutral"))
        return {"percent": percent, "tone": tone, "state": state}
    @staticmethod
    def _round(value):
        return round(value, 3) if isinstance(value, (int, float)) else None
    @staticmethod
    def _downsample(values, size=120):
        if not values: return [0.0] * size
        if len(values) <= size: return [float(value) for value in values]
        return [float(values[round(index * (len(values) - 1) / (size - 1))]) for index in range(size)]
    @staticmethod
    def _rms_summary(values):
        if not values or max(values, default=0) == 0: return "No RMS energy data is available for this segment."
        third = max(1, len(values) // 3)
        start = sum(values[:third]) / third
        end = sum(values[-third:]) / third
        change = (end - start) / max(start, 1e-9)
        if change > .15: return "Energy builds across this segment."
        if change < -.15: return "Energy eases down across this segment."
        return "Energy remains broadly steady across this segment."
    @staticmethod
    def _onset_summary(values):
        if not values or max(values, default=0) == 0: return "No onset activity data is available for this segment."
        average = sum(values) / len(values)
        peaks = sum(value > average * 1.5 for value in values)
        if peaks >= max(3, len(values) // 12): return "Dense, accented rhythmic activity with frequent peaks."
        if max(values) >= average * 3: return "Mostly steady activity with a few pronounced accents."
        return "Consistent rhythmic activity without pronounced accents."
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
