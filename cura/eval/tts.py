# PROVENANCE: ORIGINAL - MOS listening-test harness (blind A/B page + CI
# aggregation). MOS is a standard methodology (ITU-T P.800); the harness is
# original. Stdlib only. See PROVENANCE.md.
"""TTS quality evaluation - blind MOS listening test, server TTS vs Web Speech.

The evaluation plan requires a quality measure (MOS / intelligibility) for
TTS against the Web Speech API baseline. Web Speech synthesises in the
browser and can't be captured server-side, so the test runs *in* the
browser: ``export_listening_test`` renders each briefing sentence to WAV
with the server engine (Coqui) and emits a self-contained ``test.html``
where each item plays two versions - A and B, randomised per item - one the
WAV, the other live ``speechSynthesis``. The rater scores both on the
standard 5-point MOS naturalness scale and picks a preference, then
downloads a ratings CSV. ``evaluate`` aggregates one or more raters' CSVs:
per-engine MOS with 95% CI, the paired per-item difference, and preference
rates.

Raters must be human listeners - there is nothing an LLM can do here.
"""

from __future__ import annotations

import csv
import html as html_mod
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path

MOS_SCALE = "1 = bad, 2 = poor, 3 = fair, 4 = good, 5 = excellent"


def export_listening_test(sentences: list[str], out_dir: str,
                          synthesizer=None, seed: int = 7) -> int:
    """Render stimuli + the blind test page. `synthesizer(text, path)` is
    injectable for offline tests; default is Coqui (optional extra)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if synthesizer is None:
        from cura.tts.server import CoquiTTS
        synthesizer = CoquiTTS().synthesize_text

    rng = random.Random(seed)
    items = []
    for i, sentence in enumerate(sentences):
        wav = f"item_{i:02d}.wav"
        synthesizer(sentence, str(out / wav))
        items.append({"id": i, "text": sentence, "wav": wav,
                      # which side hides the server engine this item
                      "neural_side": rng.choice(["A", "B"])})

    (out / "test.html").write_text(_test_page(items), encoding="utf-8")
    return len(items)


def _test_page(items: list[dict]) -> str:
    payload = json.dumps([{**it, "text": html_mod.escape(it["text"])}
                          for it in items])
    return f"""<!doctype html>
<meta charset="utf-8">
<title>Cura TTS listening test</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 720px; margin: 40px auto; padding: 0 16px; }}
  .item {{ border: 1px solid #ddd; border-radius: 8px; padding: 16px 20px; margin: 18px 0; }}
  .sentence {{ font-style: italic; color: #444; margin-bottom: 12px; }}
  button {{ padding: 6px 14px; margin-right: 8px; cursor: pointer; }}
  select {{ margin: 0 16px 0 4px; }}
  .done {{ background: #1F5E3F; color: white; border: none; padding: 12px 24px;
          border-radius: 6px; font-size: 15px; }}
</style>
<h1>Cura TTS listening test</h1>
<p>For each sentence, listen to version <b>A</b> and version <b>B</b> (use
headphones if you can). Rate the <b>naturalness</b> of each on the MOS
scale ({MOS_SCALE}), then pick which you'd prefer for a daily news
briefing. You don't know which system is which — just rate what you hear.</p>
<p>Rater name/initials: <input id="rater" placeholder="e.g. AL"></p>
<div id="items"></div>
<button class="done" onclick="finish()">Finish &amp; download ratings CSV</button>
<script>
const ITEMS = {payload};
const root = document.getElementById('items');
ITEMS.forEach(it => {{
  const div = document.createElement('div');
  div.className = 'item';
  div.innerHTML = `
    <div class="sentence">${{it.id + 1}}. “${{it.text}}”</div>
    <button onclick="play(${{it.id}}, 'A')">▶ Play A</button>
    <button onclick="play(${{it.id}}, 'B')">▶ Play B</button>
    <div style="margin-top:10px">
      A: <select id="mos_a_${{it.id}}"><option value="">–</option>
        <option>1</option><option>2</option><option>3</option><option>4</option><option>5</option></select>
      B: <select id="mos_b_${{it.id}}"><option value="">–</option>
        <option>1</option><option>2</option><option>3</option><option>4</option><option>5</option></select>
      Prefer:
      <label><input type="radio" name="pref_${{it.id}}" value="A"> A</label>
      <label><input type="radio" name="pref_${{it.id}}" value="B"> B</label>
      <label><input type="radio" name="pref_${{it.id}}" value="tie"> tie</label>
    </div>`;
  root.appendChild(div);
}});
function play(id, side) {{
  const it = ITEMS[id];
  speechSynthesis.cancel();
  if (side === it.neural_side) {{
    new Audio(it.wav).play();
  }} else {{
    const u = new SpeechSynthesisUtterance(it.text);
    u.lang = 'en-US';
    speechSynthesis.speak(u);
  }}
}}
function finish() {{
  const rater = document.getElementById('rater').value.trim() || 'anonymous';
  // record the Web Speech environment — the baseline voice differs per
  // browser/OS, and the protocol requires reporting it
  const voices = speechSynthesis.getVoices();
  const voice = ((voices.find(v => v.default) || voices[0] || {{}}).name) || 'unknown';
  const env = (navigator.userAgent + ' | voice: ' + voice).replace(/,/g, ';');
  const rows = [['rater','item','engine_a','engine_b','mos_a','mos_b','preference','environment']];
  for (const it of ITEMS) {{
    const a = document.getElementById('mos_a_' + it.id).value;
    const b = document.getElementById('mos_b_' + it.id).value;
    const pref = (document.querySelector(`input[name="pref_${{it.id}}"]:checked`) || {{}}).value;
    if (!a || !b || !pref) {{ alert('Item ' + (it.id + 1) + ' is incomplete.'); return; }}
    const engA = it.neural_side === 'A' ? 'coqui' : 'webspeech';
    const engB = it.neural_side === 'B' ? 'coqui' : 'webspeech';
    rows.push([rater, it.id, engA, engB, a, b, pref, env]);
  }}
  const blob = new Blob([rows.map(r => r.join(',')).join('\\n')], {{type: 'text/csv'}});
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = 'tts_ratings_' + rater + '.csv';
  link.click();
}}
</script>
"""


@dataclass
class TtsEvalResult:
    n_items: int
    n_raters: int
    mos: dict            # engine -> {n, mean, sd, ci95}
    paired_diff: dict    # coqui minus webspeech: {mean, ci95, n}
    preference: dict     # engine|tie -> share

    def table(self) -> str:
        lines = [f"MOS listening test — {self.n_raters} rater(s), "
                 f"{self.n_items} items   ({MOS_SCALE})", ""]
        lines.append(f"{'engine':<12} {'n':>4} {'MOS':>6} {'sd':>6} {'95% CI':>14}")
        for engine, s in self.mos.items():
            ci = f"[{s['mean'] - s['ci95']:.2f}, {s['mean'] + s['ci95']:.2f}]"
            lines.append(f"{engine:<12} {s['n']:>4} {s['mean']:>6.2f} "
                         f"{s['sd']:>6.2f} {ci:>14}")
        d = self.paired_diff
        lines.append(f"\npaired difference (coqui − webspeech): "
                     f"{d['mean']:+.2f} ± {d['ci95']:.2f} (n={d['n']})")
        prefs = "   ".join(f"{k}: {v:.0%}" for k, v in self.preference.items())
        lines.append(f"preference: {prefs}")
        return "\n".join(lines)


def _stats(values: list[float]) -> dict:
    n = len(values)
    mean = sum(values) / n
    sd = math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1)) if n > 1 else 0.0
    return {"n": n, "mean": mean, "sd": sd,
            "ci95": 1.96 * sd / math.sqrt(n) if n > 1 else 0.0}


def evaluate(csv_paths: list[str]) -> TtsEvalResult:
    by_engine: dict[str, list[float]] = {}
    diffs: list[float] = []
    prefs: dict[str, int] = {}
    raters: set[str] = set()
    items: set[str] = set()
    for path in csv_paths:
        with open(path, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                raters.add(row["rater"])
                items.add(row["item"])
                scores = {row["engine_a"]: float(row["mos_a"]),
                          row["engine_b"]: float(row["mos_b"])}
                for engine, score in scores.items():
                    by_engine.setdefault(engine, []).append(score)
                if {"coqui", "webspeech"} <= set(scores):
                    diffs.append(scores["coqui"] - scores["webspeech"])
                pref = row["preference"]
                winner = (pref if pref == "tie"
                          else (row["engine_a"] if pref == "A" else row["engine_b"]))
                prefs[winner] = prefs.get(winner, 0) + 1
    if not by_engine:
        raise ValueError("no ratings found — run the listening test first")
    total = sum(prefs.values())
    diff_stats = _stats(diffs) if diffs else {"n": 0, "mean": 0.0, "ci95": 0.0}
    return TtsEvalResult(
        n_items=len(items), n_raters=len(raters),
        mos={eng: _stats(vals) for eng, vals in sorted(by_engine.items())},
        paired_diff={"mean": diff_stats["mean"], "ci95": diff_stats["ci95"],
                     "n": diff_stats["n"]},
        preference={k: v / total for k, v in sorted(prefs.items())})
