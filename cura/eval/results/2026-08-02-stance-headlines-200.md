# Stance domain-gap check - hand-labelled ingested headlines

**Date:** 2026-08-02
**Dataset:** 200 headlines drawn blind (seeded sample, `export-stance-pack`,
seed 7) from the 2,232-article June store snapshot - the *deployment*
domain, unlike the TweetEval tweets of the 2026-06-11 benchmark. Labelled
by the author in `2026-08-02-stance-headlines-200.Aaron-Filled-In.csv`
before any model output was seen (same blinding rule as the triangulation
packs). Labelling UI: `datasets/label-headlines.html`.
**Class balance:** negative 66 / neutral 81 / positive 53 - imbalanced,
macro-F1 stays the headline metric.
**Command:** `python -m cura eval-stance --data cura/eval/datasets/2026-08-02-stance-headlines-200.Aaron-Filled-In.csv --transformer`
**Versions:** transformers 4.57.6 · torch 2.12.0 (CPU) · vaderSentiment 3.3
**Models:** VADER lexicon (untrained) vs
`cardiffnlp/twitter-roberta-base-sentiment-latest` (fine-tuned on tweets -
*zero-shot on headlines*, which is the point of this check).

## Results

| classifier | macro-F1 | accuracy | ECE (10-bin) |
|---|---|---|---|
| VADER (baseline) | 0.493 | 0.495 | 0.308 |
| RoBERTa (zero-shot on headlines) | **0.697** | **0.715** | **0.091** |

Per-class F1:

| class | VADER | RoBERTa |
|---|---|---|
| negative | 0.541 | 0.803 |
| neutral | 0.467 | 0.716 |
| positive | 0.471 | 0.571 |

Confusion matrices (rows = true, cols = predicted; negative/neutral/positive):

```
VADER                      RoBERTa
 40    19     7             49    17     0
 28    35    18              7    72     2
 14    15    24              0    31    22
```

## Reading

- **The domain gap is small: 0.712 (tweets, in-domain) → 0.697 (headlines,
  zero-shot), −1.5 macro-F1 points.** VADER degrades more (0.528 → 0.493).
  The +18-point transformer margin from the June benchmark carries over to
  the deployment domain (+20.4 points here), answering that benchmark's
  closing caveat.
- **The gap is concentrated in one place: positive recall 0.415** (31 of 53
  true positives predicted neutral; TweetEval positive F1 was 0.718 vs
  0.571 here). News headlines' positive register - sports results, research
  findings, cultural notes - is milder than tweets' first-person
  enthusiasm, and the model defaults these to neutral. Precision stays high
  (0.875–0.917 on the polar classes).
- **Errors are adjacent, never polarity flips:** zero negative↔positive
  confusions in either direction. For triangulation this matters - a
  missed mild positive shrinks measured spread slightly; it cannot
  *fabricate* disagreement.
- **Calibration (the June benchmark's flagged follow-up): ECE 0.091 for
  RoBERTa vs 0.308 for VADER.** The entropy leg of the triangulation
  metric leans on class probabilities; RoBERTa's are usable, VADER's
  max-prob confidences overstate by ~0.31 on average - further support for
  computing triangulation over the transformer's probabilities in serving.

## Limitations

Single annotator (the author) - no inter-annotator reliability on these
labels; blinding to model output is the mitigation. n=200 gives roughly
±0.06–0.07 on macro-F1 at 95% (bootstrap, worth confirming with the
report's `bootstrap_cis.py` if this table is promoted to the report).

## Reproduce

```bash
pip install -e ".[dev,stance-transformer]"
python -m cura export-stance-pack --out pack.csv --n 200   # fresh blind pack
# fill `label`, then:
python -m cura eval-stance --data pack.csv --transformer
```
