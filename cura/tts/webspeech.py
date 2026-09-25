# PROVENANCE: ORIGINAL - self-contained audio-player page (player JS, CSS,
# transcript sync). Narration uses the browser Web Speech API (speechSynthesis),
# the proposal's TTS baseline. See PROVENANCE.md.
"""TTS baseline: Web Speech API player.

Generates a standalone HTML page that narrates the CURA_BRIEFING segments
client-side with `speechSynthesis` - the baseline named in the proposal, and
the same narration model as the design prototype's Listen view (sentence-level
segments, synced transcript, play/pause/seek, speed control).

A server TTS (cura/tts/server.py) must beat this on a MOS-style listening test
before it replaces the baseline (evaluation plan).
"""

from __future__ import annotations

import html
import json

from cura.contracts import Briefing

_CSS = """
:root{--paper:#F4EFE6;--ink:#0E1A2B;--ink-soft:#2A3548;--ink-muted:#6B7280;
--accent:#B8331E;--rule:rgba(14,26,43,0.18)}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--paper);color:var(--ink);font-family:'Inter',sans-serif;
display:flex;justify-content:center;padding:40px 16px}
.player{max-width:640px;width:100%}
.card{background:var(--ink);color:var(--paper);border-radius:10px;padding:28px;
text-align:center}
.eyebrow{font-family:'JetBrains Mono',monospace;font-size:10px;
letter-spacing:.22em;text-transform:uppercase;opacity:.7}
h1{font-family:'Fraunces',serif;font-size:26px;margin:10px 0 18px}
.controls{display:flex;gap:14px;justify-content:center;align-items:center}
button{cursor:pointer;border:1px solid rgba(244,239,230,.4);background:none;
color:var(--paper);border-radius:50%;width:44px;height:44px;font-size:15px}
button.play{width:56px;height:56px;background:var(--paper);color:var(--ink);
font-size:18px}
.speed{margin-top:14px}
.speed button{width:auto;height:auto;border-radius:12px;padding:4px 12px;
font-size:11px}
.speed button.on{background:var(--paper);color:var(--ink)}
.transcript{margin-top:28px}
.chapter{font-family:'JetBrains Mono',monospace;font-size:10px;
letter-spacing:.22em;text-transform:uppercase;color:var(--accent);
margin:20px 0 6px}
.seg{font-family:'Fraunces',serif;font-size:17px;line-height:1.5;
color:var(--ink-muted);padding:6px 12px;border-left:3px solid transparent;
cursor:pointer}
.seg.active{color:var(--ink);font-size:19px;border-left-color:var(--accent)}
.seg.done{opacity:.55}
.notice{margin-top:16px;font-size:13px;color:var(--ink-muted);display:none}
"""

_JS = """
const segs = SEGMENTS;
let idx = 0, playing = false, rate = 1.0;
const supported = 'speechSynthesis' in window;
if (!supported) document.getElementById('notice').style.display = 'block';
const els = [...document.querySelectorAll('.seg')];
function paint() {
  els.forEach((el, i) => {
    el.classList.toggle('active', i === idx);
    el.classList.toggle('done', i < idx);
  });
  els[idx]?.scrollIntoView({block: 'center', behavior: 'smooth'});
  document.getElementById('play').textContent = playing ? '❚❚' : '▶';
}
function speak() {
  if (!supported || idx >= segs.length) { playing = false; paint(); return; }
  const u = new SpeechSynthesisUtterance(segs[idx].text);
  u.rate = rate;
  u.onend = () => { if (playing && idx < segs.length - 1) { idx++; speak(); } else { playing = false; } paint(); };
  speechSynthesis.cancel();
  speechSynthesis.speak(u);
  paint();
}
function toggle() {
  if (!supported) return;
  playing = !playing;
  if (playing) speak(); else speechSynthesis.cancel();
  paint();
}
function jump(d) { idx = Math.min(segs.length - 1, Math.max(0, idx + d)); if (playing) speak(); else paint(); }
function seek(i) { idx = i; playing = true; speak(); }
function setRate(r, el) {
  rate = r;
  document.querySelectorAll('.speed button').forEach(b => b.classList.remove('on'));
  el.classList.add('on');
  if (playing) speak();
}
document.getElementById('play').onclick = toggle;
document.getElementById('prev').onclick = () => jump(-1);
document.getElementById('next').onclick = () => jump(1);
els.forEach((el, i) => el.onclick = () => seek(i));
paint();
"""


def render_audio_player(briefing: Briefing, title: str = "Daily Brief") -> str:
    transcript_parts = []
    for seg in briefing.segments:
        if seg.chapter:
            transcript_parts.append(f'<div class="chapter">{html.escape(seg.chapter)}</div>')
        transcript_parts.append(f'<div class="seg">{html.escape(seg.text)}</div>')
    segments_json = json.dumps([s.to_ui_dict() for s in briefing.segments])
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cura — {html.escape(title)}</title>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600&family=Inter:wght@400;600&family=JetBrains+Mono&display=swap" rel="stylesheet">
<style>{_CSS}</style></head>
<body><div class="player">
<div class="card">
  <div class="eyebrow">CURA · ~{briefing.est_minutes:.0f} min · {len(briefing.stories)} stories</div>
  <h1>{html.escape(title)}</h1>
  <div class="controls">
    <button id="prev" title="previous">↞</button>
    <button id="play" class="play" title="play/pause">▶</button>
    <button id="next" title="next">↠</button>
  </div>
  <div class="speed">
    <button onclick="setRate(0.75,this)">0.75×</button>
    <button class="on" onclick="setRate(1,this)">1×</button>
    <button onclick="setRate(1.25,this)">1.25×</button>
    <button onclick="setRate(1.5,this)">1.5×</button>
  </div>
</div>
<p id="notice" class="notice">Speech synthesis is not supported in this browser —
the transcript below is still readable and navigable.</p>
<div class="transcript">{"".join(transcript_parts)}</div>
</div>
<script>const SEGMENTS = {segments_json};</script>
<script>{_JS}</script>
</body></html>"""
