# Triangulation validation, round 1 - LLM judge + stance A/B (2026-06-11)

**Trigger:** with every edition story now multi-source, the contested flag
fired on 19/30 stories (63%) of a *live edition* - entire sections flagged
wall-to-wall. (On the exported annotation pack below the same thresholds
fire on 18/30 - the pack is a snapshot, not the edition, so the two counts
differ by one story.) A flag that fires on most things carries no
information. Two experiments isolate the cause.

**Annotator disclosure:** labels in this round are from a *declared LLM
annotator* (Claude Fable 5), judging the blind pack only (per-source
headlines + snippets; the model sidecar was never opened before labelling).
LLM-as-judge supplements but does not replace the human pass - the
protocol's headline result must come from the author's own labels
(`triangulation-protocol.md`). Labels + per-story rationales:
`datasets/2026-06-11-triangulation-annotate.claude.csv` (gitignored with the
pack; regenerable).

## 1. Flag vs LLM-judge labels (30 stories, VADER-era pack)

LLM judge: 12/30 contested (40%) vs the model's 18/30 (60%).

At the default thresholds (spread ≥ 0.35, entropy ≥ 0.80):

| metric | value |
|---|---|
| Cohen's kappa | **0.231** (weak) |
| accuracy | 0.600 |
| contested precision | 0.500 |
| contested recall | 0.750 |

Confusion (rows = judge, cols = model): TP 9, FN 3, FP 9, TN 9 - **half the
model's flags are false alarms**.

**Sweep finding:** the full threshold grid tops out at kappa **0.304**
(spread 0.35, entropy 0.65). No threshold combination fixes the flag, so
recalibration on these inputs is pointless - the noise is upstream:
1. VADER stance scores (macro-F1 0.528 on the stance benchmark) scatter
   across sources, inflating spread on uncontested stories.
2. This pack predates the entity-gate clustering fix; several "stories" are
   cross-event mashups whose stance comparison is meaningless (the judge's
   notes flag each one).

Thresholds therefore stay at their defaults for now, pending round 2.

## 2. Stance classifier A/B (40 identical clusters, rolling-store corpus)

Same articles, same clusters, same triangulation math - only the stance
classifier differs:

| classifier | contested | mean spread | mean entropy |
|---|---|---|---|
| VADER (baseline) | 20/40 (**50%**) | 0.327 | 0.488 |
| RoBERTa (`--stance-transformer`) | 13/40 (**32%**) | 0.295 | 0.729 |

The nine stories RoBERTa un-flags are face-valid non-contested stories
(NASA Artemis crew naming, Anthropic's $200M research pledge, a film
casting announcement) - VADER was flagging on lexical noise. Note RoBERTa's
*higher* mean entropy: its calibrated probabilities are less spiky, so the
entropy metric reads differently per classifier - another reason thresholds
must be calibrated against the production classifier, not in the abstract.

## 3. Round 2 - fresh pack under entity-gate clustering + RoBERTa

Flipping the serving classifier to RoBERTa did **not** deflate the live
flag rate (20/30 contested) - RoBERTa's calibrated probabilities are
flatter than VADER's lexicon proportions, so the normalised entropy runs
structurally higher and the `entropy ≥ 0.80` cutoff (implicitly calibrated
for VADER) fires constantly. Thresholds must be calibrated against the
production classifier. So: pack re-exported with `--stance-transformer`
under the entity-gate clustering, blind-judged again by the LLM annotator
(13/30 contested; labels + rationales in
`datasets/…-annotate-r2.claude.csv`), and re-swept on RoBERTa metrics:

| operating point | kappa | F1 | flags |
|---|---|---|---|
| spread 0.35 / entropy 0.80 (old defaults) | 0.186 | 0.538 | 13/30 |
| **spread 0.50 / entropy 0.80 (sweep optimum)** | **0.247** | 0.560 | 12/30 |
| spread 0.50 / entropy 0.85 | −0.066 | 0.286 | 8/30 |

Entropy stays at 0.80 - the 0.80–0.85 band holds genuinely contested
stories (raising the cutoff sends kappa negative). Spread moves 0.35 → 0.50.

**The deeper finding:** even the optimum agrees only weakly (κ ≈ 0.25).
The judge's contested labels track *editorial framing* clashes
(controversy-vs-achievement angles, critical op-eds vs neutral wires);
spread/entropy measure *sentiment dispersion*. Those constructs only
partially overlap - a story can be uniformly negative in tone yet framed
in opposing ways, and vice versa. This is a construct-validity result for
the disagreement metric itself, worth a paragraph in the report and a
future-work line (e.g. stance-toward-subject rather than raw sentiment).

## 4. Round 1H - the human pass (author labels, round-1 pack)

The author independently labelled the round-1 pack: **15/30 contested**.

- Against the deployed thresholds (spread 0.50 / entropy 0.80, on the
  pack's VADER-era metrics): kappa 0.133, recall 0.333 - the recalibrated
  cutoffs are too strict for the author's judgement on those metrics.
- **Sweep optimum on the author's labels: spread 0.35 / entropy 0.60 -
  kappa 0.533, F1 0.800.** The disagreement metric tracks the author's
  judgement moderately well once calibrated - a far better
  construct-validity result than the LLM judge's ceiling (0.304).
- **Inter-annotator agreement (author vs LLM judge), same 30 stories:
  kappa 0.133** - 13/30 disagreements, and they are systematic: the author
  flags topic-divisive and mixed-coverage stories; the LLM judge flags
  editorial-framing splits (celebratory-vs-critical coverage of the same
  event). "Contested" is rater-dependent under the current protocol -
  the definition needs tightening (or an adjudication round), and the
  report should present both raters with this caveat.

The author's optimum is *not* transplanted into production: it was
measured on VADER-era metrics, and the serving stack is RoBERTa (shifted
entropy scale - section 3). Final thresholds await the author's labels on
the round-2 pack, where metric and serving stack match.

## Decisions

1. **`cura serve` now runs `--stance-transformer`** (RoBERTa) - macro-F1
   0.712 vs 0.528 on the stance benchmark, and the A/B's un-flagged
   stories are face-valid.
2. **Thresholds recalibrated to spread ≥ 0.50, entropy ≥ 0.80** - the
   round-2 sweep optimum on RoBERTa metrics, recorded as provisional
   (LLM-judge labels) in `cura/triangulate/metrics.py`.
3. **Round-1 human pass done** (section 4): author-vs-metric kappa 0.533
   at the author's optimum; author-vs-LLM kappa 0.133 (systematic rater
   divergence - protocol finding). One step remains: the author labels the
   round-2 pack (`…-annotate-r2.csv`, still blank) so thresholds can be
   set on human labels over the *serving* (RoBERTa) metrics; until then
   the provisional spread 0.50 / entropy 0.80 stands.
