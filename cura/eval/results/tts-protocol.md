# TTS quality evaluation - MOS listening test protocol

**Goal.** The evaluation plan requires a quality measure for TTS against
the Web Speech API baseline. This is a blind, within-subjects MOS
(mean opinion score) listening test comparing the stretch engine -
**Coqui TTS** (tacotron2-DDC, LJSpeech), per the proposal's stack table -
with the **Web Speech API** voice the Listen view uses today.

## Design

- 10 briefing sentences from the offline fixture (deterministic,
  regenerable): `python -m cura export-tts-eval --input
  examples/sample_articles.json --sentences 10`.
- Each item plays version **A** and version **B** - one is a Coqui WAV,
  the other live `speechSynthesis` - with the side randomised per item
  (seeded), so raters can't anchor on position. Raters see the sentence
  text, rate the **naturalness** of each version on the 5-point MOS scale
  (1 bad … 5 excellent), and pick a preference (A / B / tie).
- Within-subjects: every rater hears both engines on every sentence, so
  the paired per-item difference is the primary statistic.
- One caveat to report: Web Speech renders with the rater's local system
  voice, so the baseline varies slightly across machines/browsers. Run
  raters on the same machine if possible, and record the browser used.

## Running it

1. `python -m cura export-tts-eval …` (above) - writes WAVs + `test.html`
   to `cura/eval/datasets/tts-listening-test/` (gitignored, regenerable).
2. Each rater opens `test.html` in a browser (headphones), completes all
   10 items, and downloads their `tts_ratings_<name>.csv`.
3. Aggregate: `python -m cura eval-tts --data tts_ratings_*.csv` - reports
   per-engine MOS with 95% CI, the paired Coqui−WebSpeech difference, and
   preference rates.

Aim for **5+ raters** (classmates work); at 10 items each that gives n≥50
ratings per engine. Raters must be human listeners - this is the one
evaluation an LLM cannot stand in for, even partially.

## Results

**Study run 2026-08-02.** 6 raters (R01–R06), 10 items, within-subjects
 - n = 60 paired ratings per engine. Data:
`cura/eval/datasets/tts-ratings/2026-08-02-all-raters.csv`; aggregate
with `python -m cura eval-tts --data <that file>`.

| engine | n | MOS | sd | 95% CI |
|---|---|---|---|---|
| Coqui | 60 | **4.07** | 0.82 | [3.86, 4.27] |
| Web Speech | 60 | 3.33 | 0.71 | [3.15, 3.51] |

Paired difference (Coqui − Web Speech): **+0.73 ± 0.24** (95% CI
[+0.49, +0.97] - excludes zero). Preference: **Coqui 67%**, Web Speech
17%, tie 17%. The direction is unanimous: every rater's mean paired
difference favours Coqui (range +0.50 to +1.00), so the effect is not
driven by any single rater.

**Environments (the protocol's known caveat, recorded per row in the
`environment` column):** raters used five setups - Windows Chrome ×3
(recorded voice: Microsoft David), Mac Chrome (Samantha), Mac Safari,
Linux Chrome - so the Web Speech baseline varied across raters rather
than being held constant. All recorded defaults are older-generation
system voices; **no rater used Edge's modern neural Web Speech voices**,
so this result establishes superiority over the *common default* browser
voice, not over the best available Web Speech stack.

**Adoption (2026-08-02): confirmed.** The 2026-06-11 provisional adoption
of `cura serve --neural-tts` is now evidence-backed: +0.73 MOS and a 4:1
preference ratio justify the ~1.1 s/sentence server CPU and ~113 MB model
cost. The flag still defaults off; without it (or if synthesis fails)
Listen falls back to Web Speech.
