"""Local, read-only browser UI for fingerprint validation and similarity."""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from modules.fingerprint import FingerprintSimilarityEngine


HTML = r"""<!doctype html>
<html><head><meta charset="utf-8"><title>CrateIQ Insights</title><style>
:root{--bg:#0b1020;--panel:#151d32;--line:#28334f;--muted:#9aa6bf;--text:#edf2ff;--cyan:#54d5ff;--low:#54d5ff;--mid:#f6c967;--high:#ff7285;--neutral:#526079}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px system-ui}.shell{width:min(1600px,96vw);margin:auto;padding:28px 0 60px}.top{display:flex;justify-content:space-between;align-items:end;border-bottom:1px solid var(--line);padding-bottom:22px}.eyebrow{color:var(--cyan);font-size:12px;letter-spacing:.13em;text-transform:uppercase}h1{margin:4px 0;font-size:34px}.picker{position:relative;min-width:420px}input,button{background:#1b2740;color:var(--text);border:1px solid #3c4d72;border-radius:8px;padding:10px 12px}input{width:100%}button{cursor:pointer;background:var(--cyan);color:#06101b;font-weight:700}.results{position:absolute;z-index:5;top:calc(100% + 6px);left:0;right:0;max-height:320px;overflow:auto;padding:6px;background:#10182a;border:1px solid #3c4d72;border-radius:10px;box-shadow:0 14px 32px #0008}.results[hidden]{display:none}.track-option{display:block;width:100%;padding:10px;text-align:left;background:transparent;color:var(--text);border:0;border-radius:6px}.track-option:hover,.track-option.active{background:#263858}.track-option small{display:block;color:var(--muted);margin-top:2px}.no-results{padding:12px;color:var(--muted)}.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px;margin-top:20px}.hero{display:flex;justify-content:space-between;gap:20px}.title{font-size:22px;font-weight:700}.muted{color:var(--muted)}.stats{display:flex;gap:28px}.stats b{display:block;font-size:20px}.timeline{display:flex;width:100%;height:94px;margin:22px 0 8px;border-radius:8px;overflow:hidden;background:#202a40}.part{min-width:3px;border-right:2px solid #0b1020;padding:9px 8px;color:#0b1020;font-size:11px;font-weight:800;overflow:hidden;cursor:pointer}.part.selected{outline:3px solid white;z-index:1}.INTRO{background:#74b6ff}.GROOVE{background:#71d69b}.BUILD{background:#f6c967}.DROP{background:#ff808d}.BREAKDOWN{background:#ba8df5}.OUTRO{background:#a9b4c8}.CUSTOM{background:#72809a}.legend{display:flex;gap:14px;color:var(--muted);font-size:12px}.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:5px}.deck{display:grid;grid-template-columns:1.3fr .7fr;gap:20px}.charts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.chart-card{min-width:0}.chart-card>p:first-child{margin:12px 0}.chart{height:155px;width:100%;overflow:hidden;background:#0f1628;border-radius:10px}.chart svg{display:block;width:100%;height:100%}.chart-note{min-height:55px;font-size:12px;line-height:1.4;margin:10px 2px 0;overflow-wrap:anywhere}.chart-note b{color:var(--text)}.metric-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}.metric{background:#10182a;border-radius:10px;padding:13px}.metric h3{margin:0 0 10px;font-size:13px}.row{display:grid;grid-template-columns:80px minmax(0,1fr) 50px;gap:8px;align-items:center;font-size:12px;margin:8px 0}.bar{height:8px;background:#28334f;border-radius:99px;overflow:hidden}.fill{display:block;height:100%;border-radius:99px}.fill.low{background:var(--low)}.fill.mid{background:var(--mid)}.fill.high{background:var(--high)}.fill.neutral{background:var(--neutral)}.tag{grid-column:2/4;color:var(--muted);font-size:11px}.matches{display:grid;gap:10px;margin-top:12px}.match{display:flex;justify-content:space-between;gap:16px;background:#10182a;border-radius:10px;padding:13px;cursor:pointer}.match:hover{outline:1px solid var(--cyan)}@media(max-width:850px){.deck,.charts{grid-template-columns:1fr}.top,.hero{display:block}.stats{margin-top:15px}.picker{min-width:0;margin-top:18px}}
</style></head><body><main class="shell"><header class="top"><div><div class="eyebrow">Track analysis deck</div><h1>CrateIQ Insights</h1><div id="summary" class="muted">Loading library…</div></div><div class="picker"><input id="track-search" type="search" autocomplete="off" role="combobox" aria-expanded="false" aria-controls="track-results" placeholder="Search title or artist"><div id="track-results" class="results" role="listbox" hidden></div></div></header><section id="deck"></section></main><script>
let selected=0,currentTrack='',tracks=[],resultIndex=-1;const $=id=>document.getElementById(id);const fmt=v=>typeof v==='number'?(Math.abs(v)>=100?Math.round(v).toString():v.toFixed(2)):'—';const time=v=>typeof v==='number'?v.toFixed(1):'—';const escape=value=>String(value??'').replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));const label=item=>item.artist?`${item.title} · ${item.artist}`:item.title;const search=$('track-search'),results=$('track-results');
function matches(){let query=search.value.trim().toLowerCase();return tracks.filter(item=>!query||`${item.title} ${item.artist||''}`.toLowerCase().includes(query)).slice(0,30)}
function showResults(){let list=matches();resultIndex=-1;results.hidden=false;search.setAttribute('aria-expanded','true');results.innerHTML=list.length?list.map((item,index)=>`<button class="track-option" role="option" data-index="${index}"><strong>${escape(item.title)}</strong>${item.artist?`<small>${escape(item.artist)}</small>`:''}</button>`).join(''):'<div class="no-results">No tracks match this search.</div>';results._items=list}
function hideResults(){results.hidden=true;search.setAttribute('aria-expanded','false');resultIndex=-1}
function chooseTrack(item,segment=0){if(!item)return;currentTrack=item.id;selected=segment;search.value=label(item);hideResults();load()}
search.addEventListener('focus',showResults);search.addEventListener('input',showResults);search.addEventListener('keydown',event=>{let items=results._items||matches();if(event.key==='Escape'){hideResults();return}if(event.key==='ArrowDown'||event.key==='ArrowUp'){event.preventDefault();if(!items.length)return;resultIndex=(resultIndex+(event.key==='ArrowDown'?1:items.length-1))%items.length;results.querySelectorAll('.track-option').forEach((node,index)=>node.classList.toggle('active',index===resultIndex));return}if(event.key==='Enter'){event.preventDefault();chooseTrack(items[resultIndex<0?0:resultIndex])}});results.addEventListener('mousedown',event=>{let button=event.target.closest('.track-option');if(button)chooseTrack((results._items||[])[Number(button.dataset.index)])});document.addEventListener('mousedown',event=>{if(!event.target.closest('.picker'))hideResults()});
fetch('/api/tracks').then(response=>response.json()).then(items=>{tracks=items;currentTrack=tracks[0]?.id||'';search.value=tracks[0]?label(tracks[0]):'';if(currentTrack)load()});fetch('/api/summary').then(response=>response.json()).then(data=>$('summary').textContent=`${data.tracks} analyzed tracks · select a section to compare`);
function meter(labelName,item,key){let value=item.features[key],meter=item.meters[key]||{percent:0,tone:'neutral'};return `<div class="row"><span>${labelName}</span><span class="bar"><span class="fill ${meter.tone}" style="width:${meter.percent}%"></span></span><b>${fmt(value?.value)}</b><span class="tag">${value?.track??'—'} track · ${value?.absolute??'—'} absolute</span></div>`}
function chart(values,color){let width=400,height=150,max=Math.max(...values,1),last=Math.max(values.length-1,1),points=values.map((value,index)=>`${index*width/last},${height-value/max*(height-10)-5}`).join(' ');return `<svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none"><polyline fill="none" stroke="${color}" stroke-width="3" points="${points}"/></svg>`}
function chartPanel(labelName,values,color,meaning,summary){return `<div class="chart-card"><p class="muted">${labelName}</p><div class="chart">${chart(values,color)}</div><p class="muted chart-note"><b>${escape(summary)}</b><br>${meaning}</p></div>`}
function load(index=selected){selected=index;if(!currentTrack)return;fetch(`/api/track?track_id=${encodeURIComponent(currentTrack)}&segment_index=${index}`).then(response=>response.json()).then(data=>{let segment=data.segment,timeline=data.timeline,end=Math.max(...timeline.map(item=>item.end),1);let line=timeline.map((item,itemIndex)=>`<div class="part ${item.type} ${itemIndex===selected?'selected':''}" data-segment="${itemIndex}" style="width:${100*(item.end-item.start)/end}%" title="${item.type}: ${time(item.start)}–${time(item.end)} seconds">${item.duration>10?item.type:''}<br>${time(item.start)}s</div>`).join('');$('deck').innerHTML=`<section class="panel"><div class="hero"><div><div class="title">${escape(data.title||'Untitled')} <span class="muted">· ${escape(data.artist||'Unknown artist')}</span></div><div class="muted">${fmt(data.bpm)} BPM · ${escape(data.key||'—')} · ${timeline.length} sections</div></div><div class="stats"><div><span class="muted">Selected</span><b>${segment.type}</b></div><div><span class="muted">Timing</span><b>${time(segment.start)}–${time(segment.end)}s</b></div><div><span class="muted">Bars</span><b>${fmt(segment.bars)}</b></div></div></div><div id="timeline" class="timeline">${line}</div><div class="legend"><span><i class="dot INTRO"></i>Intro</span><span><i class="dot GROOVE"></i>Groove</span><span><i class="dot BUILD"></i>Build</span><span><i class="dot DROP"></i>Drop</span><span><i class="dot BREAKDOWN"></i>Breakdown</span><span><i class="dot OUTRO"></i>Outro</span></div></section><section class="deck"><div><section class="panel"><div class="eyebrow">Energy & momentum</div><div class="charts">${chartPanel('RMS energy',segment.charts.rms,'#54d5ff','Loudness over time: a rising line builds energy, a flat line stays steady, and dips ease down.',segment.charts.rms_summary)}${chartPanel('Onset strength',segment.charts.onset,'#f6c967','Transient activity over time: frequent peaks suggest dense percussion; isolated peaks are accents or hits.',segment.charts.onset_summary)}</div></section><section class="panel"><div class="eyebrow">Segment profile</div><div class="metric-grid"><div class="metric"><h3>Energy</h3>${meter('Overall',segment,'energy')}${meter('Slope',segment,'slope')}${meter('Crest',segment,'crest')}</div><div class="metric"><h3>Bass</h3>${meter('Bass',segment,'bass')}${meter('Kick',segment,'kick')}${meter('Transient',segment,'transient')}</div><div class="metric"><h3>Rhythm</h3>${meter('Density',segment,'rhythm')}${meter('Groove',segment,'groove')}${meter('Syncopation',segment,'syncopation')}</div><div class="metric"><h3>Spectrum & harmony</h3>${meter('Brightness',segment,'brightness')}<div class="row"><span>Key</span><b>${escape(segment.harmony.key||'—')}</b></div><div class="row"><span>Mode</span><b>${escape(segment.harmony.mode||'—')}</b></div></div></div></section></div><aside><section class="panel"><div class="eyebrow">Similarity decision</div><p>Compare this <b>${segment.type}</b> segment against the library.</p><button id="similar">Find similar segments</button><div id="matches" class="matches"><p class="muted">Matches load on demand.</p></div></section></aside></section>`;$('timeline').addEventListener('click',event=>{let part=event.target.closest('.part');if(part)load(Number(part.dataset.segment))});$('similar').addEventListener('click',similar)})}
function similar(){let box=$('matches');box.innerHTML='<p class="muted">Comparing normalized fingerprints…</p>';fetch(`/api/similar?track_id=${encodeURIComponent(currentTrack)}&segment_index=${selected}`).then(response=>response.json()).then(items=>{box.innerHTML=items.map((item,index)=>`<div class="match" data-index="${index}"><div><b>${escape(item.title||'Untitled')}</b><br><span class="muted">${escape(item.segment)} · ${escape(item.reasons.join(', '))}</span></div><b>${fmt(item.score)}</b></div>`).join('');box.querySelectorAll('.match').forEach(node=>node.addEventListener('click',()=>chooseTrack(tracks.find(item=>item.id===items[Number(node.dataset.index)].track_id),items[Number(node.dataset.index)].segment_index)))})}
</script></body></html>"""


class InsightsHandler(BaseHTTPRequestHandler):
    output_root = Path("output/tracks")
    similarity_cache = None

    def do_GET(self):
        request = urlparse(self.path)
        if request.path == "/":
            return self._send(HTML, "text/html")
        if request.path == "/api/summary":
            return self._json({"tracks": len(self._catalog())})
        if request.path == "/api/tracks":
            return self._json(self._catalog())
        if request.path == "/api/segments":
            track_id = parse_qs(request.query).get("track_id", [""])[0]
            path = self.output_root / f"{track_id}.json"
            if not path.exists():
                return self._json([])
            doc = json.loads(path.read_text())
            return self._json([{"index": i, "type": value.get("segment", "CUSTOM")} for i, value in enumerate(doc.get("analysis", {}).get("fingerprints", []))])
        if request.path == "/api/track":
            query = parse_qs(request.query)
            track_id = query.get("track_id", [""])[0]
            index = int(query.get("segment_index", ["0"])[0])
            path = self.output_root / f"{track_id}.json"
            if not path.exists():
                return self._json({})
            doc = json.loads(path.read_text())
            fingerprints = doc.get("analysis", {}).get("fingerprints", [])
            selected = fingerprints[index] if 0 <= index < len(fingerprints) else {}
            paths = {"energy": "energy.overall", "slope": "energy.slope", "crest": "energy.crest_factor", "bass": "bass.overall", "kick": "bass.kick", "transient": "bass.transient_strength", "rhythm": "rhythm.density", "groove": "rhythm.groove", "syncopation": "rhythm.syncopation", "confidence": "harmonic.confidence", "brightness": "spectrum.spectral_centroid", "flatness": "spectrum.spectral_flatness"}
            features = {name: {"value": self._round(self._value(selected, feature_path)), "track": self._range_label(selected, fingerprints, feature_path), "absolute": self._absolute_label(name, self._value(selected, feature_path))} for name, feature_path in paths.items()}
            rms = self._downsample(selected.get("raw_features", {}).get("rms", []))
            onset = self._downsample(selected.get("raw_features", {}).get("onset_strength", []))
            return self._json({"title": doc.get("metadata", {}).get("title"), "artist": doc.get("metadata", {}).get("artist"), "bpm": doc.get("library", {}).get("bpm"), "key": doc.get("library", {}).get("key"), "segment": {"type": selected.get("segment", "CUSTOM"), "start": selected.get("start_time", 0), "end": selected.get("end_time", 0), "bars": selected.get("bars", 0), "harmony": selected.get("harmonic", {}), "features": features, "meters": {name: self._meter(value["track"], value["absolute"]) for name, value in features.items()}, "charts": {"rms": rms, "onset": onset, "rms_summary": self._rms_summary(rms), "onset_summary": self._onset_summary(onset)}}, "timeline": [{"type": item.get("segment", "CUSTOM"), "start": item.get("start_time", 0), "end": item.get("end_time", 0), "duration": item.get("duration", 0)} for item in fingerprints]})
        if request.path == "/api/similar":
            items, documents = self._items()
            query = parse_qs(request.query)
            track_id = query.get("track_id", [""])[0]
            index = int(query.get("segment_index", ["0"])[0])
            target = next((item for item in items if item["track_id"] == track_id and item["segment_index"] == index), None)
            if target is None:
                return self._json([])
            engine = FingerprintSimilarityEngine().fit(items)
            return self._json([{"score": match.score, "track_id": match.track_id, "segment_index": match.segment_index, "segment": match.fingerprint.get("segment"), "reasons": match.reasons, "title": documents[match.track_id].get("metadata", {}).get("title", match.track_id)} for match in engine.nearest_neighbors(target, items)])
        self.send_error(404)

    def _items(self):
        if self.similarity_cache is not None:
            return self.similarity_cache
        documents, items = {}, []
        for path in self.output_root.glob("*.json"):
            doc = json.loads(path.read_text())
            track_id = doc["system"]["trackId"]
            documents[track_id] = doc
            items.extend({"track_id": track_id, "segment_index": index, "fingerprint": fingerprint} for index, fingerprint in enumerate(doc.get("analysis", {}).get("fingerprints", [])))
        self.similarity_cache = (items, documents)
        return self.similarity_cache

    def _catalog(self):
        manifest = self.output_root.parent / "tracks_manifest.json"
        if manifest.exists():
            tracks = json.loads(manifest.read_text()).get("tracks", {})
            return sorted(({"id": track_id, "title": entry.get("title") or Path(entry.get("path", track_id)).stem, "artist": entry.get("artist") or ""} for track_id, entry in tracks.items()), key=lambda entry: (entry["title"].lower(), entry["artist"].lower()))
        return [{"id": path.stem, "title": path.stem, "artist": ""} for path in self.output_root.glob("*.json")]

    @staticmethod
    def _range_label(selected, fingerprints, path):
        def value(item):
            for key in path.split("."):
                item = item.get(key) if isinstance(item, dict) else None
            return item
        current = value(selected)
        values = sorted(value(item) for item in fingerprints if isinstance(value(item), (int, float)))
        if current is None or not values:
            return "—"
        rank = sum(number <= current for number in values) / len(values)
        return "Low" if rank < .33 else "High" if rank > .67 else "Mid"

    @staticmethod
    def _value(item, path):
        for key in path.split("."):
            item = item.get(key) if isinstance(item, dict) else None
        return item

    @staticmethod
    def _absolute_label(name, value):
        if not isinstance(value, (int, float)):
            return "—"
        if name == "slope":
            return "Falling" if value < -0.001 else "Rising" if value > 0.001 else "Stable"
        if name == "crest":
            return "Compact" if value < 1.25 else "Dynamic" if value > 2.0 else "Balanced"
        thresholds = {"energy": (.03, .1), "bass": (.15, .35), "kick": (.08, .25), "transient": (.05, .2), "rhythm": (.1, .5), "groove": (.33, .67), "syncopation": (.33, .67), "brightness": (1200, 2500), "flatness": (.1, .35), "confidence": (.33, .67)}
        if name not in thresholds:
            return "—"
        low, high = thresholds[name]
        return "Low" if value < low else "High" if value > high else "Mid"

    @staticmethod
    def _meter(track, absolute):
        state = absolute if absolute != "—" else track
        meters = {"Low": (33, "low"), "Falling": (33, "low"), "Compact": (33, "low"), "Mid": (66, "mid"), "Stable": (66, "mid"), "Balanced": (66, "mid"), "High": (100, "high"), "Rising": (100, "high"), "Dynamic": (100, "high")}
        percent, tone = meters.get(state, (0, "neutral"))
        return {"percent": percent, "tone": tone, "state": state}

    @staticmethod
    def _round(value):
        return round(value, 3) if isinstance(value, (int, float)) else None

    @staticmethod
    def _downsample(values, size=120):
        if not values:
            return [0.0] * size
        if len(values) <= size:
            return [float(value) for value in values]
        return [float(values[round(index * (len(values) - 1) / (size - 1))]) for index in range(size)]

    @staticmethod
    def _rms_summary(values):
        if not values or max(values, default=0) == 0:
            return "No RMS energy data is available for this segment."
        third = max(1, len(values) // 3)
        start = sum(values[:third]) / third
        end = sum(values[-third:]) / third
        change = (end - start) / max(start, 1e-9)
        if change > .15:
            return "Energy builds across this segment."
        if change < -.15:
            return "Energy eases down across this segment."
        return "Energy remains broadly steady across this segment."

    @staticmethod
    def _onset_summary(values):
        if not values or max(values, default=0) == 0:
            return "No onset activity data is available for this segment."
        average = sum(values) / len(values)
        peaks = sum(value > average * 1.5 for value in values)
        if peaks >= max(3, len(values) // 12):
            return "Dense, accented rhythmic activity with frequent peaks."
        if max(values) >= average * 3:
            return "Mostly steady activity with a few pronounced accents."
        return "Consistent rhythmic activity without pronounced accents."

    def _json(self, value):
        self._send(json.dumps(value), "application/json")

    def _send(self, content, content_type):
        encoded = content.encode()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, *_):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="output/tracks")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    InsightsHandler.output_root = Path(args.output)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), InsightsHandler)
    print(f"CrateIQ Insights: http://127.0.0.1:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
