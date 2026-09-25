# Triangulation validation - annotation protocol

**Goal.** The contested flag is the novel contribution's output: a story is
flagged when stance **spread ≥ 0.35** or label **entropy ≥ 0.80** across ≥ 2
sources (`cura/triangulate/metrics.py`). Those thresholds are hypotheses. This
study validates them against human judgement, as the evaluation plan requires.

## The annotation pack

Generated 2026-06-11 from live ingestion (the default 41-feed set + Reddit),
VADER stance (the production default), via:

```bash
python -m cura export-triangulation \
  --out cura/eval/datasets/2026-06-11-triangulation-annotate.csv --limit 30
```

- 30 multi-source stories (3–9 sources each, mean 4.4).
- `…-annotate.csv` - what the annotator reads: per-source
  `[Outlet] headline - snippet` lines, one row per story.
- `…-annotate.model.json` - the model's spread/entropy/flag per story.
  **Do not open it while annotating** - the CSV is deliberately blind so the
  model's verdict can't anchor you.
- Both files are gitignored (they contain article text); regenerate any day
  with the command above.

At the default thresholds the model flags **18/30 (60%)** of this pack as
contested - a high rate that itself suggests the thresholds may be
permissive. The sweep below tests exactly that.

## How to annotate (~15 minutes)

For each row, read every source line, then fill `contested` with **yes** or
**no**:

- **yes** - the sources visibly disagree in framing or substance: tone
  (alarmed vs reassuring), blame assignment, emphasis, or the facts asserted.
- **no** - the sources tell substantively the same story, even if the topic
  itself is divisive. *A war story is not automatically contested; the
  question is whether these outlets' accounts diverge.*

Use `notes` for anything borderline. Leave `contested` blank to skip a row -
skipped rows are excluded and counted, not guessed.

Ideally a second person annotates an independent copy: inter-annotator
agreement (Cohen's kappa between humans) is the ceiling any model can be
expected to reach - report it alongside the model's kappa.

## Scoring

```bash
python -m cura eval-triangulation \
  --data cura/eval/datasets/2026-06-11-triangulation-annotate.csv \
  --model cura/eval/datasets/2026-06-11-triangulation-annotate.model.json \
  --sweep
```

Reports, at the default thresholds: **Cohen's kappa** (headline number -
contested is the rarer class, so raw accuracy flatters a never-contested
predictor), accuracy, precision/recall/F1 on the contested class, and the
2×2 confusion table. `--sweep` grid-searches spread ∈ [0, 0.6] ×
entropy ∈ [0.5, 1.0] over the stored per-story metrics and ranks operating
points by kappa, marking the defaults - showing whether they sit on a
plateau (robust) or a cliff (fragile), and what the annotated-data-optimal
thresholds would be.

## Results

**Rounds 1–2 (LLM judge, 2026-06-11):** see
`2026-06-11-triangulation-llm-judge.md`. Round 1 (VADER-era pack): kappa
0.231, sweep ceiling 0.304 - inputs, not thresholds, were binding; the
companion stance A/B moved the serving default to RoBERTa. Round 2 (fresh
pack, RoBERTa metrics): sweep optimum spread 0.50 / entropy 0.80 (kappa
0.247), applied provisionally in `cura/triangulate/metrics.py`. Key
finding: sentiment dispersion only partly captures perceived framing
disagreement (κ ≈ 0.25 at best).

**Round 1H (human pass on the round-1 pack): done.** Author 15/30
contested; author-vs-metric sweep optimum spread 0.35 / entropy 0.60
(kappa 0.533, F1 0.800 - the metric's best validation result);
author-vs-LLM inter-annotator kappa 0.133 with systematic divergence
(topic-divisiveness vs framing-clash readings of "contested") - tighten
the protocol definition before round 3.

**Round 3 (human pass on the round-2 pack, 2026-08-01): done.** Author
11/30 contested. Protocol tightened per round 1H before annotating:
contested = a reader would come away with a different picture of what
happened or who is at fault (facts, blame, or valence) - not intensity
variance, complementary facets, or divergence among off-anchor sources;
noisy clusters are judged on the anchor story even though the metric
scores the whole cluster (that gap is a clustering-purity error, tracked
by the clustering eval). Results:

- **Metric vs author: kappa 0.085** (F1 0.435) at the serving thresholds
  (spread 0.50 / entropy 0.80) - which the sweep confirms is also the
  human-optimal operating point. The thresholds are calibrated; the
  input signal is what's binding.
- **Inter-annotator (author vs declared LLM judge): kappa 0.724**
  (26/30, disagreeing on c-009/c-032/c-050/c-145) - up from 0.133 in
  round 1H, so the tightened definition made "contested" reliably
  judgeable. The metric sits far below this ceiling.
- **Error modes.** False negatives are same-valence framing clashes -
  blame reassignment among uniformly negative sources is invisible to
  sentiment dispersion (c-073: three different culprits at spread 0.08;
  also c-000, c-043, c-005, c-032). False positives are noise-polluted
  clusters where off-anchor sources inflate dispersion (c-050, c-068,
  c-286, c-006) and uniform criticism at varying intensity (c-145).
- **Rubric sensitivity.** Flipping the three notes-flagged conditional
  rows (c-050 anchor-vs-cluster, c-141 op-ed exclusion, c-246
  explanatory attribution) moves kappa only within 0.028–0.167; the
  conclusion is robust to every rubric decision.

Headline finding for the report: with annotation noise ruled out
(ceiling 0.724) and thresholds at their optimum, sentiment dispersion
captures only a small part of perceived framing disagreement (κ ≈ 0.09).
The failure is constructive: it locates the missing signal - stance
*target* (who is blamed), not stance *valence* - and motivates
frame-aware classification as future work.

**LLM-annotator reliability (repeat pass, 2026-08-03).** To bound label
noise in the LLM-judge legs, a fresh, fully blind instance of the judge
model re-labelled the round-2 pack under the round-3 tightened protocol
(labels: `datasets/2026-08-03-triangulation-annotate-r2.claude-repeat.csv`;
6/30 contested - the tightened definition reads more conservatively).
Agreement: **κ 0.603** (25/30) with the author's round-3 labels; **κ 0.493**
(23/30) with the archived first judge pass (that comparison mixes rater
noise with the protocol change, so it is the pessimistic bound). Reading:
the realistic rater ceiling spans κ ≈ 0.5–0.7 rather than the single 0.724
point - and the metric's κ 0.085 sits far below every point of that range,
so the round-3 conclusion is robust to LLM label noise. Repeat-pass
disagreements with the author (c-000, c-005, c-032, c-043, c-059) are all
same-valence blame-splits the stricter instance read as complementary
coverage - the construct's residual grey zone.
