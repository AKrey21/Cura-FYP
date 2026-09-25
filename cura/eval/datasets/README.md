# Evaluation datasets

Datasets are not vendored into the repo - download them and point the eval
CLI at local copies. Document, in the report, exactly which split was used and
its class balance.

## Stance / sentiment (macro-F1 vs VADER baseline)

CSV with `text,label` columns; labels `negative | neutral | positive`.

- **SemEval-2017 Task 4 subtask A** - 3-class tweet sentiment; the standard
  benchmark VADER itself is often reported on. Good for the social-media leg.
- **A hand-labelled sample of ingested headlines** (~300, double-annotated,
  report inter-annotator agreement) - strongest evidence, since it matches the
  deployment distribution; also feeds the class-imbalance/bias discussion.
- For true *stance* (target-aware) rather than sentiment: **SemEval-2016
  Task 6** (stance in tweets) - note it uses favor/against/none, which maps to
  positive/negative/neutral.

Run: `python -m cura eval-stance --data path/to/stance.csv [--transformer]`
(also reports 10-bin ECE when the classifier emits class probabilities).

The headline pack for the domain-gap check is generated with
`python -m cura export-stance-pack` - a seeded blind sample from the
rolling article store (`2026-08-02-stance-headlines-200.csv` here was
drawn from the 2,232-article June store snapshot).

## Summarisation (ROUGE + faithfulness vs TextRank baseline)

JSON list of `{"document": ..., "reference": ...}`.

- **CNN/DailyMail** (test split, or a 200–500 doc sample for compute reasons -
  state the sample size) - news-domain, abstractive references.
  Fetch a sample (no extra dependencies):
  `python cura/eval/datasets/fetch_cnn_dailymail.py 300`
- **XSum** if testing one-sentence compression.

Run: `python -m cura eval-summary --data path/to/pairs.json [--abstractive]`

Results from runs of this benchmark live in `cura/eval/results/`.

## Triangulation validation (human judgement)

Collect ~30 multi-source story clusters from real runs, have 2–3 annotators
label each "contested / not contested", then report agreement between the
spread/entropy flags and the human majority (plus a threshold sweep /
precision-recall curve over SPREAD_THRESHOLD and ENTROPY_THRESHOLD).

## TTS

MOS listening test, server TTS vs the Web Speech API baseline - protocol
and results in `cura/eval/results/tts-protocol.md`; collected ratings in
`tts-ratings/`.

## User study

Usefulness / trust / format preference - protocol and questionnaire in
`cura/eval/results/user-study-protocol.md`; responses collect into
`user-study/responses.csv` (one row per paper questionnaire, transcribed
by the researcher). Aggregate with `python -m cura eval-user-study` -
Likert medians/IQR per item, format rankings, contested-flag agreement,
open answers verbatim.
