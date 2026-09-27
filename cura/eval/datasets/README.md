# Evaluation datasets

Third-party benchmarks (TweetEval, CNN/DailyMail) are not vendored: fetch
them with the scripts here and point the eval CLI at the local copies. The
project's own labelled packs (the headline stance sample, the triangulation
annotation rounds, the clustering pairs) are tracked in this folder, so every
result in `cura/eval/results/` can be recomputed. Each results file records the split it was run on and, for the stance
benchmarks, the class balance.

## Stance / sentiment (macro-F1 vs VADER baseline)

CSV with `text,label` columns; labels `negative | neutral | positive`.

- **TweetEval sentiment (SemEval-2017 Task 4 subtask A)** - 3-class tweet
  sentiment, test split; the benchmark run used a 1,000-tweet sample fetched
  with `python cura/eval/datasets/fetch_tweeteval_sentiment.py 1000`.
- **A hand-labelled sample of ingested headlines** (200, labelled by the author
  alone, blind to model output; the pack is below) - the deployment-domain check
  reported in §5.2 of the report, with its single-annotator limitation stated there.


Run: `python -m cura eval-stance --data path/to/stance.csv [--transformer]`
(also reports 10-bin ECE when the classifier emits class probabilities).

The headline pack for the domain-gap check is generated with
`python -m cura export-stance-pack` - a seeded blind sample from the
rolling article store (`2026-08-02-stance-headlines-200.csv` here was
drawn from the 2,232-article June store snapshot). Both copies are here:
`2026-08-02-stance-headlines-200.csv` as exported and
`2026-08-02-stance-headlines-200.Aaron-Filled-In.csv`, the author-labelled
copy the headline result is computed from.

## Summarisation (ROUGE + faithfulness vs TextRank baseline)

JSON list of `{"document": ..., "reference": ...}`.

- **CNN/DailyMail** 3.0.0, test split, first 300 articles (BART on CPU caps the
  sample; the report's §5.3 result uses exactly this sample) - news-domain,
  human-written highlights as references. Fetch (no extra dependencies):
  `python cura/eval/datasets/fetch_cnn_dailymail.py 300`

Run: `python -m cura eval-summary --data path/to/pairs.json [--abstractive]`

Results from runs of this benchmark live in `cura/eval/results/`.

## Triangulation validation (human judgement)

Protocol and the round-by-round record: `cura/eval/results/triangulation-protocol.md`.
The packs are here, exported blind by `python -m cura export-triangulation`
(the metric's own spread/entropy/flag per cluster is kept apart in the
`.model.json` so annotators never see it):

- `2026-06-11-triangulation-annotate.csv` (author labels), `.claude.csv`
  (the declared LLM judge's labels), `.model.json` - round 1.
- `2026-06-11-triangulation-annotate-r2.csv`, `.claude.csv`, `.model.json` -
  round 2, a fresh sample scored by the serving classifier.
- `2026-08-03-triangulation-annotate-r2.claude-repeat.csv` - a blind repeat
  pass by a fresh judge instance on 30 round-2 clusters (rater-ceiling check).

Run: `python -m cura eval-triangulation --data <pack.csv> --model <pack.model.json> --sweep`.

## Clustering (pair benchmark)

`2026-06-11-clustering-pairs.csv` - 60 cross-outlet article pairs sampled
adversarially from a live corpus and labelled same-event / not by the author
(`.claude.csv`: the LLM judge's labels on the same pairs).
`2026-06-11-clustering-pairs.snapshot.json` - the 1,084-article corpus
snapshot (feed title and description per article) the pairs were drawn from,
so the run reproduces exactly:
`python -m cura eval-clustering --pairs <pairs.csv> --snapshot <snapshot.json>`.

## TTS

MOS listening test, server TTS vs the Web Speech API baseline - protocol
and results in `cura/eval/results/tts-protocol.md`; collected ratings in
`tts-ratings/`.

## User study

Usefulness / trust / format preference - protocol and questionnaire in
`cura/eval/results/user-study-protocol.md`; responses in `user-study/responses.csv` (one row per paper questionnaire, transcribed
by the researcher). Aggregate with `python -m cura eval-user-study` -
Likert medians/IQR per item, format rankings, contested-flag agreement,
open answers verbatim.

A retrospective needs survey (September 2026; the same eight participants,
matched by code; gathered after the design) sits beside it: questionnaire
and researcher notes in `user-study/needs-survey-2026-09.md`, responses in
`user-study/needs-survey-responses.csv`. Tally with
`python -m cura eval-needs-survey` - counts per option ("six of eight",
never percentages at n = 8), "other" text and open answers verbatim.
Results and reading: `cura/eval/results/needs-survey-2026-09.md`.
