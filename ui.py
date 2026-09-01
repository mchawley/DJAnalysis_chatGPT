"""Local, read-only browser UI for fingerprint validation and similarity."""

import argparse
import json
from statistics import median
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from modules.fingerprint import FingerprintSimilarityEngine
from modules.playlist_store import PlaylistStore
from modules.playlist_ui import PLAYLIST_HTML


HTML = r"""<!doctype html>
<html><head><meta charset="utf-8"><title>CrateIQ Insights</title><style>
:root{--bg:#0b1020;--panel:#151d32;--line:#28334f;--muted:#9aa6bf;--text:#edf2ff;--cyan:#54d5ff;--low:#54d5ff;--mid:#f6c967;--high:#ff7285;--neutral:#526079;--compare:#ba8df5}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px system-ui}.shell{width:min(1600px,96vw);margin:auto;padding:28px 0 60px}.top{display:flex;justify-content:space-between;align-items:end;border-bottom:1px solid var(--line);padding-bottom:22px}.eyebrow{color:var(--cyan);font-size:12px;letter-spacing:.13em;text-transform:uppercase}h1{margin:4px 0;font-size:34px}.picker{position:relative;min-width:420px}input,button{background:#1b2740;color:var(--text);border:1px solid #3c4d72;border-radius:8px;padding:10px 12px}input{width:100%}button{cursor:pointer;background:var(--cyan);color:#06101b;font-weight:700}.results{position:absolute;z-index:5;top:calc(100% + 6px);left:0;right:0;max-height:320px;overflow:auto;padding:6px;background:#10182a;border:1px solid #3c4d72;border-radius:10px;box-shadow:0 14px 32px #0008}.results[hidden]{display:none}.track-option{display:block;width:100%;padding:10px;text-align:left;background:transparent;color:var(--text);border:0;border-radius:6px}.track-option:hover,.track-option.active{background:#263858}.track-option small{display:block;color:var(--muted);margin-top:2px}.no-results{padding:12px;color:var(--muted)}.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px;margin-top:20px}.hero{display:flex;justify-content:space-between;gap:20px}.title{font-size:22px;font-weight:700}.muted{color:var(--muted)}.stats{display:flex;gap:28px}.stats b{display:block;font-size:20px}.waveform{position:relative;height:80px;margin-top:16px;overflow:hidden;background:#0f1628;border-radius:8px}.waveform svg{display:block;width:100%;height:100%}.wave-selection{position:absolute;top:0;bottom:0;background:#54d5ff24;border:1px solid var(--cyan);pointer-events:none}.waveform.compare .wave-selection{background:#ba8df524;border-color:var(--compare)}.waveform-empty{display:grid;place-items:center;height:100%;color:var(--muted);font-size:12px}.timeline{display:flex;width:100%;height:94px;margin:12px 0 8px;border-radius:8px;overflow:hidden;background:#202a40}.part{min-width:3px;border-right:2px solid #0b1020;padding:9px 8px;color:#0b1020;font-size:11px;font-weight:800;overflow:hidden;cursor:pointer}.part.selected{outline:3px solid white;z-index:1}.INTRO{background:#74b6ff}.GROOVE{background:#71d69b}.BUILD{background:#f6c967}.DROP{background:#ff808d}.BREAKDOWN{background:#ba8df5}.OUTRO{background:#a9b4c8}.CUSTOM{background:#72809a}.legend{display:flex;gap:14px;color:var(--muted);font-size:12px}.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:5px}.beat-summary{display:flex;align-items:center;gap:10px;margin:10px 0;color:var(--muted);font-size:12px}.beat-group{display:flex;gap:4px}.beat{width:18px;height:12px;border-radius:3px;background:#2b3856}.beat.on{background:var(--cyan)}.beat.kick.on{background:var(--high)}.deck{display:grid;grid-template-columns:1.3fr .7fr;gap:20px}.charts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.chart-card{min-width:0}.chart-card>p:first-child{margin:12px 0}.chart{height:155px;width:100%;overflow:hidden;background:#0f1628;border-radius:10px}.chart svg{display:block;width:100%;height:100%}.chart-note{min-height:55px;font-size:12px;line-height:1.4;margin:10px 2px 0;overflow-wrap:anywhere}.chart-note b{color:var(--text)}.metric-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}.metric{background:#10182a;border-radius:10px;padding:13px}.metric h3{margin:0 0 10px;font-size:13px}.row{display:grid;grid-template-columns:80px minmax(0,1fr) 50px;gap:8px;align-items:center;font-size:12px;margin:8px 0}.bar{height:8px;background:#28334f;border-radius:99px;overflow:hidden}.fill{display:block;height:100%;border-radius:99px}.fill.low{background:var(--low)}.fill.mid{background:var(--mid)}.fill.high{background:var(--high)}.fill.neutral{background:var(--neutral)}.references{grid-column:2/4;display:flex;gap:7px;flex-wrap:wrap;font-size:10px}.reference{color:var(--muted)}.reference:before{content:'';display:inline-block;width:6px;height:6px;margin-right:4px;border-radius:50%;background:var(--neutral)}.reference.low:before{background:var(--low)}.reference.mid:before{background:var(--mid)}.reference.high:before{background:var(--high)}.matches{display:grid;gap:10px;margin-top:12px}.match{display:flex;justify-content:space-between;gap:16px;background:#10182a;border-radius:10px;padding:13px;cursor:pointer}.match:hover,.match.selected{outline:1px solid var(--compare)}.comparison .eyebrow{color:var(--compare)}@media(max-width:850px){.deck,.charts{grid-template-columns:1fr}.top,.hero{display:block}.stats{margin-top:15px}.picker{min-width:0;margin-top:18px}}
</style></head><body><main class="shell"><header class="top"><div><div class="eyebrow">Track analysis deck</div><h1>CrateIQ Insights</h1><div id="summary" class="muted">Loading library…</div></div><div><a href="/playlists" style="color:var(--cyan);display:block;margin-bottom:10px">Playlist analysis</a><div class="picker"><input id="track-search" type="search" autocomplete="off" role="combobox" aria-expanded="false" aria-controls="track-results" placeholder="Search title or artist"><div id="track-results" class="results" role="listbox" hidden></div></div></div></header><section id="deck"></section></main><script>
let selected=0,currentTrack='',tracks=[],resultIndex=-1,comparison=null;const $=id=>document.getElementById(id);const fmt=v=>{if(typeof v!=='number'||!Number.isFinite(v))return '—';if(v!==0&&Math.abs(v)<.005)return v<0?'−<0.01':'<0.01';return Math.abs(v)>=100?Math.round(v).toString():v.toFixed(2)};const time=v=>{if(typeof v!=='number'||!Number.isFinite(v))return '—';let total=Math.max(0,Math.round(v));return `${Math.floor(total/60)}:${String(total%60).padStart(2,'0')}`};const escape=value=>String(value??'').replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));const label=item=>item.artist?`${item.title} · ${item.artist}`:item.title;const search=$('track-search'),results=$('track-results');
function matches(showAll=false){let query=showAll?'':search.value.trim().toLowerCase();return tracks.filter(item=>!query||`${item.title} ${item.artist||''}`.toLowerCase().includes(query)).slice(0,30)}
function showResults(showAll=false){let list=matches(showAll);resultIndex=-1;results.hidden=false;search.setAttribute('aria-expanded','true');results.innerHTML=list.length?list.map((item,index)=>`<button class="track-option" role="option" data-index="${index}"><strong>${escape(item.title)}</strong>${item.artist?`<small>${escape(item.artist)}</small>`:''}</button>`).join(''):'<div class="no-results">No tracks match this search.</div>';results._items=list}
function hideResults(){results.hidden=true;search.setAttribute('aria-expanded','false');resultIndex=-1}
function chooseTrack(item,segment=0){if(!item)return;comparison=null;currentTrack=item.id;selected=segment;search.value=label(item);hideResults();load()}
search.addEventListener('focus',()=>showResults(true));search.addEventListener('input',()=>showResults());search.addEventListener('keydown',event=>{let items=results._items||matches();if(event.key==='Escape'){hideResults();return}if(event.key==='ArrowDown'||event.key==='ArrowUp'){event.preventDefault();if(!items.length)return;resultIndex=(resultIndex+(event.key==='ArrowDown'?1:items.length-1))%items.length;results.querySelectorAll('.track-option').forEach((node,index)=>node.classList.toggle('active',index===resultIndex));return}if(event.key==='Enter'){event.preventDefault();chooseTrack(items[resultIndex<0?0:resultIndex])}});results.addEventListener('mousedown',event=>{let button=event.target.closest('.track-option');if(button)chooseTrack((results._items||[])[Number(button.dataset.index)])});document.addEventListener('mousedown',event=>{if(!event.target.closest('.picker'))hideResults()});
fetch('/api/tracks').then(response=>response.json()).then(items=>{tracks=items;let query=new URLSearchParams(location.search),requested=query.get('track_id');currentTrack=tracks.find(item=>item.id===requested)?.id||tracks[0]?.id||'';selected=Number(query.get('segment_index')||0);let current=tracks.find(item=>item.id===currentTrack);search.value=current?label(current):'';if(currentTrack)load()});fetch('/api/summary').then(response=>response.json()).then(data=>$('summary').textContent=`${data.tracks} analyzed tracks · select a section to compare`);
function meter(labelName,item,key){let value=item.features[key],meter=item.meters[key]||{percent:0,tone:'neutral',track:{state:'—',tone:'neutral'},absolute:{state:'—',tone:'neutral'}};return `<div class="row"><span>${labelName}</span><span class="bar"><span class="fill ${meter.tone}" style="width:${meter.percent}%"></span></span><b>${fmt(value?.value)}</b><span class="references"><span class="reference ${meter.track.tone}">Track: ${meter.track.state}</span><span class="reference ${meter.absolute.tone}">Absolute: ${meter.absolute.state}</span></span></div>`}
function chart(values,color){let width=400,height=150,max=Math.max(...values,1),last=Math.max(values.length-1,1),points=values.map((value,index)=>`${index*width/last},${height-value/max*(height-10)-5}`).join(' ');return `<svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none"><polyline fill="none" stroke="${color}" stroke-width="3" points="${points}"/></svg>`}
function chartPanel(labelName,values,color,meaning,summary){return `<div class="chart-card"><p class="muted">${labelName}</p><div class="chart">${chart(values,color)}</div><p class="muted chart-note"><b>${escape(summary)}</b><br>${meaning}</p></div>`}
function waveform(view,start,end,duration,compare=false){if(!view.available)return '<div class="waveform waveform-empty">Rekordbox waveform unavailable for this track.</div>';let width=800,height=80,half=height/2,last=Math.max(view.samples.length-1,1),top=view.samples.map((value,index)=>`${index*width/last},${half-value*(half-5)}`).join(' '),bottom=view.samples.slice().reverse().map((value,index)=>`${(last-index)*width/last},${half+value*(half-5)}`).join(' '),left=100*start/duration,span=100*(end-start)/duration,color=compare?'#ba8df5':'#54d5ff';return `<div class="waveform ${compare?'compare':''}" title="Rekordbox ${view.source} waveform"><svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none"><polygon points="${top} ${bottom}" fill="${color}66" stroke="${color}" stroke-width="2"/></svg><span class="wave-selection" style="left:${left}%;width:${span}%"></span></div>`}
function beatSummary(labelName,summary,type=''){if(!summary.available)return '';let cells=summary.pattern.map(value=>`<i class="beat ${type} ${value?'on':''}"></i>`).join('');return `<div class="beat-summary"><b>${labelName}</b><span class="beat-group" title="Dominant four-beat bar">${cells}</span><span>${summary.consistency}% of ${summary.bars} bars</span></div>`}
function envelope(values,duration){if(!values?.length)return '';let width=800,height=34,line=key=>{let maximum=Math.max(...values.map(value=>value[key]),1e-9);return values.map(value=>`${(value.start/duration)*width},${height-value[key]/maximum*(height-5)}`).join(' ')+` ${(values.at(-1).end/duration)*width},${height-values.at(-1)[key]/maximum*(height-5)}`};return `<svg class="envelope" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" title="Each color is normalized independently"><polyline points="${line('energy')}" fill="none" stroke="#54d5ff"/><polyline points="${line('bass')}" fill="none" stroke="#ff7285"/></svg><div class="legend"><span style="color:#54d5ff">● Energy</span><span style="color:#ff7285">● Bass</span></div>`}
function load(index=selected){selected=index;comparison=null;if(!currentTrack)return;fetch(`/api/track?track_id=${encodeURIComponent(currentTrack)}&segment_index=${index}`).then(response=>response.json()).then(data=>{let segment=data.segment,timeline=data.timeline,end=Math.max(...timeline.map(item=>item.end),1);let line=timeline.map((item,itemIndex)=>`<div class="part ${item.type} ${itemIndex===selected?'selected':''}" data-segment="${itemIndex}" style="width:${100*(item.end-item.start)/end}%" title="${item.type}: ${time(item.start)}–${time(item.end)} seconds">${item.duration>10?item.type:''}<br>${time(item.start)}s</div>`).join('');$('deck').innerHTML=`<section class="panel"><div class="hero"><div><div class="title">${escape(data.title||'Untitled')} <span class="muted">· ${escape(data.artist||'Unknown artist')}</span></div><div class="muted">${fmt(data.bpm)} BPM · ${escape(data.camelot||data.key||'—')} · ${timeline.length} sections</div></div><div class="stats"><div><span class="muted">Selected</span><b>${segment.type}</b></div><div><span class="muted">Timing</span><b>${time(segment.start)}–${time(segment.end)}s</b></div><div><span class="muted">Bars</span><b>${fmt(segment.bars)}</b></div></div></div>${waveform(data.waveform,segment.start,segment.end,end)}${envelope(data.envelope,end)}<div id="timeline" class="timeline">${line}</div><div class="beat-summary"><span class="muted">Dominant activity per four-beat bar</span></div>${beatSummary('Onset',segment.patterns.onset)}${beatSummary('Kick',segment.patterns.kick,'kick')}<div class="legend"><span><i class="dot INTRO"></i>Intro</span><span><i class="dot GROOVE"></i>Groove</span><span><i class="dot BUILD"></i>Build</span><span><i class="dot DROP"></i>Drop</span><span><i class="dot BREAKDOWN"></i>Breakdown</span><span><i class="dot OUTRO"></i>Outro</span></div></section><section id="comparison"></section><section class="deck"><div><section class="panel"><div class="eyebrow">Energy & momentum</div><div class="charts">${chartPanel('RMS energy',segment.charts.rms,'#54d5ff','Loudness over time: a rising line builds energy, a flat line stays steady, and dips ease down.',segment.charts.rms_summary)}${chartPanel('Onset strength',segment.charts.onset,'#f6c967','Transient activity over time: frequent peaks suggest dense percussion; isolated peaks are accents or hits.',segment.charts.onset_summary)}</div></section><section class="panel"><div class="eyebrow">Segment profile</div><div class="metric-grid"><div class="metric"><h3>Energy</h3>${meter('Overall',segment,'energy')}${meter('Slope',segment,'slope')}${meter('Crest',segment,'crest')}</div><div class="metric"><h3>Bass</h3>${meter('Bass',segment,'bass')}${meter('Kick',segment,'kick')}${meter('Transient',segment,'transient')}</div><div class="metric"><h3>Rhythm</h3>${meter('Density',segment,'rhythm')}${meter('Groove',segment,'groove')}${meter('Syncopation',segment,'syncopation')}</div><div class="metric"><h3>Spectrum & harmony</h3>${meter('Brightness',segment,'brightness')}<div class="row"><span>Key</span><b>${escape(segment.harmony.camelot||segment.harmony.key||'—')}</b></div><div class="row"><span>Mode</span><b>${escape(segment.harmony.mode||'—')}</b></div></div></div></section></div><aside><section class="panel"><div class="eyebrow">Similarity decision</div><p>Compare this <b>${segment.type}</b> segment against the library.</p><button id="similar">Find similar segments</button><div id="matches" class="matches"><p class="muted">Matches load on demand.</p></div></section></aside></section>`;$('timeline').addEventListener('click',event=>{let part=event.target.closest('.part');if(part)load(Number(part.dataset.segment))});$('similar').addEventListener('click',similar)})}
function comparisonTimeline(timeline,matchIndex,end){return timeline.map((item,index)=>`<div class="part ${item.type} ${index===matchIndex?'selected':''}" style="width:${100*(item.end-item.start)/end}%" title="${item.type}: ${time(item.start)}–${time(item.end)} seconds">${item.duration>10?item.type:''}<br>${time(item.start)}s</div>`).join('')}
function previewMatch(match,node){comparison={trackId:match.track_id,segmentIndex:match.segment_index};document.querySelectorAll('.match').forEach(card=>card.classList.remove('selected'));node.classList.add('selected');let sourceTrack=currentTrack,request=comparison;fetch(`/api/track?track_id=${encodeURIComponent(match.track_id)}&segment_index=${match.segment_index}`).then(response=>response.json()).then(data=>{if(currentTrack!==sourceTrack||comparison!==request)return;let segment=data.segment,timeline=data.timeline,end=Math.max(...timeline.map(item=>item.end),1),target=$('comparison');target.innerHTML=`<section class="panel comparison"><div class="hero"><div><div class="eyebrow">Selected similar segment · ${fmt(match.score)} match</div><div class="title">${escape(data.title||'Untitled')} <span class="muted">· ${escape(data.artist||'Unknown artist')}</span></div><div class="muted">${fmt(data.bpm)} BPM · ${escape(data.key||'—')} · ${escape(match.reasons.join(', '))}</div></div><div class="stats"><div><span class="muted">Matched segment</span><b>${segment.type}</b></div><div><span class="muted">Timing</span><b>${time(segment.start)}–${time(segment.end)}s</b></div></div></div>${waveform(data.waveform,segment.start,segment.end,end,true)}<div class="timeline">${comparisonTimeline(timeline,match.segment_index,end)}</div><div class="muted">Double-click this match in the list to make it the main track.</div></section>`})}
function similar(){let box=$('matches');box.innerHTML='<p class="muted">Comparing normalized fingerprints…</p>';fetch(`/api/similar?track_id=${encodeURIComponent(currentTrack)}&segment_index=${selected}`).then(response=>response.json()).then(items=>{box.innerHTML=items.map((item,index)=>`<div class="match" data-index="${index}"><div><b>${escape(item.title||'Untitled')}</b><br><span class="muted">${escape(item.segment)} · ${escape(item.reasons.join(', '))}</span></div><b>${fmt(item.score)}</b></div>`).join('');box.querySelectorAll('.match').forEach(node=>{let item=items[Number(node.dataset.index)];node.addEventListener('click',()=>previewMatch(item,node));node.addEventListener('dblclick',()=>chooseTrack(tracks.find(track=>track.id===item.track_id),item.segment_index))})})}
</script></body></html>"""


class InsightsHandler(BaseHTTPRequestHandler):
    output_root = Path("output/tracks")
    similarity_cache = None

    def do_GET(self):
        request = urlparse(self.path)
        if request.path == "/":
            return self._send(HTML, "text/html")
        if request.path == "/playlists":
            return self._send(PLAYLIST_HTML, "text/html")
        if request.path == "/api/summary":
            return self._json({"tracks": len(self._catalog())})
        if request.path == "/api/tracks":
            return self._json(self._catalog())
        if request.path == "/api/playlists":
            return self._json(self._playlist_catalog())
        if request.path == "/api/playlist":
            playlist_id = parse_qs(request.query).get("playlist_id", [""])[0]
            return self._json(self._playlist_detail(playlist_id))
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
            return self._json({"title": doc.get("metadata", {}).get("title"), "artist": doc.get("metadata", {}).get("artist"), "bpm": doc.get("library", {}).get("bpm"), "key": doc.get("library", {}).get("key"), "camelot": self._camelot(doc.get("library", {}).get("key")), "waveform": self._waveform_view(doc.get("analysis", {})), "envelope": self._envelope(fingerprints), "segment": {"type": selected.get("segment", "CUSTOM"), "start": selected.get("start_time", 0), "end": selected.get("end_time", 0), "bars": selected.get("bars", 0), "harmony": selected.get("harmonic", {}), "patterns": {"onset": self._pattern_summary(selected.get("rhythm", {}).get("onset_pattern", [])), "kick": self._pattern_summary(selected.get("bass", {}).get("kick_pattern", []))}, "features": features, "meters": {name: self._meter(value["track"], value["absolute"]) for name, value in features.items()}, "charts": {"rms": rms, "onset": onset, "rms_summary": self._rms_summary(rms), "onset_summary": self._onset_summary(onset)}}, "timeline": [{"type": item.get("segment", "CUSTOM"), "start": item.get("start_time", 0), "end": item.get("end_time", 0), "duration": item.get("duration", 0)} for item in fingerprints]})
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

    def do_POST(self):
        if urlparse(self.path).path != "/api/playlists":
            self.send_error(404)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(size) or b"{}")
        except (ValueError, OSError):
            return self._json({"error": "Invalid playlist request"})
        store = PlaylistStore(self.output_root)
        action = payload.get("action")
        if action == "create":
            return self._json(store.create(payload.get("name", ""), payload.get("track_ids", [])))
        if action == "update":
            return self._json(store.update(payload.get("playlist_id", ""), payload.get("name"), payload.get("track_ids")) or {})
        if action == "restore":
            return self._json(store.restore(payload.get("playlist_id", "")) or {})
        if action == "set_segment_included":
            return self._json(store.set_segment_included(
                payload.get("playlist_id", ""), payload.get("entry_id", ""),
                payload.get("segment_index"), bool(payload.get("included")),
            ) or {})
        if action == "restore_segments":
            return self._json(store.restore_segments(payload.get("playlist_id", ""), payload.get("entry_id", "")) or {})
        if action == "delete":
            return self._json({"deleted": store.delete(payload.get("playlist_id", ""))})
        return self._json({"error": "Unknown playlist action"})

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

    def _playlist_catalog(self):
        return [{
            "id": item["id"], "name": item["name"], "source": item.get("source", "custom"),
            "trackCount": len(item.get("trackIds", [])), "unmatchedCount": item.get("unmatchedCount", 0),
        } for item in PlaylistStore(self.output_root).all_playlists()]

    def _playlist_detail(self, playlist_id):
        playlist = next((item for item in PlaylistStore(self.output_root).all_playlists() if item["id"] == playlist_id), None)
        if playlist is None:
            return {"id": playlist_id, "name": "Playlist not found", "tracks": [], "trends": {}}
        store = PlaylistStore(self.output_root)
        exclusions = playlist.get("segmentExclusions", {})
        tracks = [self._playlist_track(entry["trackId"], entry["id"], exclusions.get(entry["id"], [])) for entry in store.entries(playlist)]
        playable = [track for track in tracks if track["playable"]]
        previous = None
        for track in tracks:
            if not track["playable"]:
                track["transition"] = {"label": "Skipped", "score": 0, "severity": "none", "reasons": []}
                track["outlier"] = {"label": "Skipped", "score": 0, "severity": "none", "reasons": []}
                continue
            track["transition"] = self._transition(track, previous)
            track["outlier"] = self._outlier(track, playable)
            previous = track
        return {
            "id": playlist_id, "name": playlist["name"], "source": playlist.get("source", "custom"),
            "tracks": tracks,
            "chartTracks": playable,
            "trends": {key: self._normalize([track["features"].get(key) for track in playable]) for key in ("energy", "bass", "rhythm", "brightness", "tempo")},
            "raw_trends": {key: [track["features"].get(key) for track in playable] for key in ("energy", "bass", "rhythm", "brightness", "tempo")},
        }

    def _playlist_track(self, track_id, entry_id, excluded_indexes=()):
        path = self.output_root / f"{track_id}.json"
        catalog = next((item for item in self._catalog() if item["id"] == track_id), {"title": track_id, "artist": ""})
        if not path.exists():
            return {"id": track_id, "entryId": entry_id, **catalog, "bpm": None, "key": None, "camelot": None, "duration": 0, "available": False, "playable": False, "features": {}, "segments": [], "originalSegments": []}
        doc = json.loads(path.read_text())
        fingerprints = doc.get("analysis", {}).get("fingerprints", [])
        key = doc.get("library", {}).get("key")
        excluded = {int(index) for index in excluded_indexes}
        original_segments = [self._segment_flow_item(item, index) for index, item in enumerate(fingerprints)]
        for feature in ("energy", "bass", "rhythm", "brightness"):
            for item, normalized in zip(original_segments, self._normalize([item["features"].get(feature) for item in original_segments])):
                item[f"normalized_{feature}"] = normalized
        for segment in original_segments:
            segment["included"] = segment["index"] not in excluded
        segments = [segment for segment in original_segments if segment["included"]]
        def weighted(feature):
            values = [(segment["features"].get(feature), self._segment_duration(segment)) for segment in segments]
            values = [(value, duration) for value, duration in values if isinstance(value, (int, float))]
            total = sum(duration for _, duration in values)
            return sum(value * duration for value, duration in values) / total if total else None
        features = {feature: weighted(feature) for feature in ("energy", "bass", "rhythm", "brightness")}
        features["tempo"] = doc.get("library", {}).get("bpm")
        duration = sum(self._segment_duration(segment) for segment in segments)
        return {"id": track_id, "entryId": entry_id, "title": doc.get("metadata", {}).get("title") or catalog["title"], "artist": doc.get("metadata", {}).get("artist") or catalog["artist"], "bpm": features["tempo"], "key": key, "camelot": self._camelot(key), "duration": duration, "available": bool(fingerprints), "playable": bool(segments), "features": features, "segments": segments, "originalSegments": original_segments, "entry": segments[0]["features"] if segments else {}, "exit": segments[-1]["features"] if segments else {}}

    @staticmethod
    def _segment_duration(segment):
        start, end = segment.get("start"), segment.get("end")
        return max(0.0, end - start) if isinstance(start, (int, float)) and isinstance(end, (int, float)) else 0.0

    def _segment_flow_item(self, fingerprint, index):
        return {
            "index": index, "type": fingerprint.get("segment", "CUSTOM"),
            "start": fingerprint.get("start_time", 0), "end": fingerprint.get("end_time", 0),
            "energy": self._value(fingerprint, "energy.overall"),
            "features": {name: self._value(fingerprint, path) for name, path in {
                "energy": "energy.overall", "bass": "bass.overall", "rhythm": "rhythm.density", "brightness": "spectrum.spectral_centroid",
            }.items()},
        }

    @staticmethod
    def _normalize(values):
        valid = [value for value in values if isinstance(value, (int, float))]
        if not valid:
            return [0.0 for _ in values]
        low, high = min(valid), max(valid)
        if high - low < 1e-9:
            return [.5 if isinstance(value, (int, float)) else 0.0 for value in values]
        return [(value - low) / (high - low) if isinstance(value, (int, float)) else 0.0 for value in values]

    def _transition(self, track, previous):
        if not track["playable"] or not previous or not previous["playable"]:
            return {"label": "No transition data", "score": 0, "severity": "none", "reasons": []}
        changes, reasons = [], []
        for key, label, threshold in (("energy", "energy", .12), ("bass", "bass", .18), ("rhythm", "rhythm", 20), ("brightness", "brightness", 900)):
            value = track["features"].get(key)
            previous_value = previous["features"].get(key)
            if isinstance(value, (int, float)) and isinstance(previous_value, (int, float)) and abs(value - previous_value) > threshold:
                changes.append(1); reasons.append(f"abrupt {label} change")
        bpm = track.get("bpm")
        previous_bpm = previous.get("bpm")
        if isinstance(bpm, (int, float)) and isinstance(previous_bpm, (int, float)) and abs(bpm - previous_bpm) > 8:
            changes.append(1); reasons.append("large BPM jump")
        if track.get("camelot") and previous.get("camelot") and not self._compatible_keys(previous["camelot"], track["camelot"]):
            changes.append(1); reasons.append("key clash risk")
        score = len(changes)
        return {"label": "Transition break" if score else "Smooth transition", "score": score, "severity": "high" if score >= 3 else "medium", "reasons": reasons}

    def _outlier(self, track, all_tracks):
        if not track["playable"] or len(all_tracks) < 3:
            return {"label": "No outlier data", "score": 0, "severity": "none", "reasons": []}
        reasons, score = [], 0
        for key, label in (("energy", "energy"), ("bass", "bass"), ("rhythm", "rhythm"), ("brightness", "brightness")):
            values = [item["features"].get(key) for item in all_tracks if isinstance(item["features"].get(key), (int, float))]
            value = track["features"].get(key)
            if not isinstance(value, (int, float)) or len(values) < 3:
                continue
            center = median(values); mad = median([abs(item - center) for item in values])
            if mad > 1e-9 and abs(value - center) / (1.4826 * mad) > 3.5:
                score += 1; reasons.append(f"unusual {label} for this playlist")
        return {"label": "Playlist outlier" if score else "In playlist range", "score": score, "severity": "high" if score >= 2 else "medium", "reasons": reasons}

    @staticmethod
    def _compatible_keys(first, second):
        if first == second:
            return True
        try:
            first_number, first_mode = int(first[:-1]), first[-1]
            second_number, second_mode = int(second[:-1]), second[-1]
        except (ValueError, TypeError):
            return False
        difference = (second_number - first_number) % 12
        if first_mode == second_mode:
            return difference in {0, 1, 2, 7, 11}
        return difference in {0, 3, 11}

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
        if max(values) - min(values) < 1e-9:
            return "Even"
        rank = sum(number <= current for number in values) / len(values)
        return "Low" if rank < .33 else "High" if rank > .67 else "Mid"

    @staticmethod
    def _pattern_summary(values):
        """Collapse raw beat observations into one representative four-beat bar."""
        bits = [1 if value else 0 for value in values]
        bars = [tuple(bits[index:index + 4]) for index in range(0, len(bits) - 3, 4)]
        if not bars:
            return {"available": False, "pattern": [], "bars": 0, "consistency": 0}
        counts = {}
        for bar in bars:
            counts[bar] = counts.get(bar, 0) + 1
        pattern, repeats = max(counts.items(), key=lambda item: item[1])
        return {
            "available": True, "pattern": list(pattern), "bars": len(bars),
            "consistency": round(100 * repeats / len(bars)),
        }

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
        return {"percent": percent, "tone": tone, "state": state, "track": {"state": track, "tone": InsightsHandler._tone(track)}, "absolute": {"state": absolute, "tone": InsightsHandler._tone(absolute)}}

    @staticmethod
    def _tone(state):
        if state in {"Low", "Falling", "Compact"}:
            return "low"
        if state in {"Mid", "Stable", "Balanced"}:
            return "mid"
        if state in {"High", "Rising", "Dynamic"}:
            return "high"
        return "neutral"

    @staticmethod
    def _round(value):
        return round(value, 6) if isinstance(value, (int, float)) else None

    @staticmethod
    def _downsample(values, size=120):
        if not values:
            return [0.0] * size
        if len(values) <= size:
            return [float(value) for value in values]
        return [float(values[round(index * (len(values) - 1) / (size - 1))]) for index in range(size)]

    @classmethod
    def _waveform_view(cls, analysis):
        detail = analysis.get("waveformDetail") or []
        preview = analysis.get("waveformPreview") or []
        samples = detail or preview
        if not samples:
            return {"available": False, "source": None, "samples": []}
        values = [abs(float(value)) for value in samples if isinstance(value, (int, float))]
        if not values:
            return {"available": False, "source": None, "samples": []}
        maximum = max(values)
        normalized = [value / maximum if maximum else 0.0 for value in cls._downsample(values, 400)]
        return {"available": True, "source": "detail" if detail else "preview", "samples": normalized}

    @staticmethod
    def _camelot(key):
        if not key:
            return None
        value = str(key).strip()
        if len(value) >= 2 and value[:-1].isdigit() and value[-1].upper() in {"A", "B"}:
            return value.upper()
        normalized = value.replace("♯", "#").replace("♭", "b").replace("major", "maj").replace("minor", "min").replace(" ", "").lower()
        if normalized.endswith("m") and not normalized.endswith(("maj", "min")):
            normalized = f"{normalized[:-1]}min"
        mapping = {"cmaj":"8B", "gmaj":"9B", "dmaj":"10B", "amaj":"11B", "emaj":"12B", "bmaj":"1B", "f#maj":"2B", "gbmaj":"2B", "dbmaj":"3B", "c#maj":"3B", "abmaj":"4B", "g#maj":"4B", "ebmaj":"5B", "d#maj":"5B", "bbmaj":"6B", "a#maj":"6B", "fmaj":"7B", "amin":"8A", "emin":"9A", "bmin":"10A", "f#min":"11A", "gbmin":"11A", "c#min":"12A", "dbmin":"12A", "g#min":"1A", "abmin":"1A", "d#min":"2A", "ebmin":"2A", "a#min":"3A", "bbmin":"3A", "fmin":"4A", "cmin":"5A", "gmin":"6A", "dmin":"7A"}
        return mapping.get(normalized)

    @staticmethod
    def _envelope(fingerprints):
        def value(item, path):
            return InsightsHandler._value(item, path) or 0.0
        return [{"start": item.get("start_time", 0), "end": item.get("end_time", 0), "energy": value(item, "energy.overall"), "bass": value(item, "bass.overall")} for item in fingerprints]

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
