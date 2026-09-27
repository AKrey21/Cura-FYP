# Cura

Cura reads the day's news from many outlets, works out where they agree and
where they don't, and turns the result into a five-minute briefing you can
read, listen to, or skim as a one-page paper.

It is my final-year project for the University of London CM3070 module, built
under the "Orchestrating AI Models" template. The pipeline chains three kinds
of model, each with a simple baseline and a heavier alternative that only
replaces the baseline if it wins on a benchmark. My own contribution is the triangulation step: for any story covered by two or more outlets, Cura
measures how far their stances diverge and flags the story as contested, and
the report tests how well that flag matches human judgement.

## What it does

1. Pulls articles from 72 RSS feeds across 51 outlets, plus Reddit's public
   listing endpoints, into a rolling 72-hour store.
2. Removes duplicates and groups articles into events. Two articles only join
   the same event if they share named entities, which stops unrelated stories
   with similar wording from merging.
3. Summarises each event (TextRank by default; BART if installed).
4. Classifies each outlet's stance (VADER by default; a fine-tuned RoBERTa if
   installed) with calibrated class probabilities.
5. Measures disagreement per event as the spread of stance scores plus the
   entropy of the vote, and flags contested coverage.
6. Assembles a briefing that fits about five minutes of narration and renders
   it three ways: a sectioned text feed, narrated audio with a synced
   transcript, and a single broadsheet page.

If a heavier model fails to load or errors at run time, the orchestrator
falls back to the baseline and records that it did so, along with the time
each stage took.

## Running it

Python 3.10 or newer.

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m cura serve
```

On Windows, `.\cura` does the same as the last line.

`serve` fetches live news, runs the pipeline, and opens the web app on
today's edition. The edition rebuilds itself every 15 minutes while the
server runs. Useful variations:

```bash
.venv/bin/python -m cura serve --topics technology economy      # only these topics
.venv/bin/python -m cura serve --input examples/sample_articles.json   # offline, fixture data
.venv/bin/python -m cura serve --light                          # baselines only, fast start
.venv/bin/python -m cura present                                # guided-tour demo mode
```

Installing an optional extra is all it takes for `serve` to use it:

| Extra | Adds |
|---|---|
| `abstractive` | BART summaries |
| `stance-transformer` | fine-tuned RoBERTa stance classifier |
| `embeddings` | sentence-embedding clustering |
| `fulltext` | full article text instead of feed descriptions |
| `tts` | Coqui neural narration rendered on the server |
| `cleo` | Cleo, the in-app assistant, and the Verify claim checker |

Everything except Cleo and the claim checker runs with no keys and no cost. Those two
call the Anthropic API and need `ANTHROPIC_API_KEY` set; without it they fall
back to a scripted demo and the rest of the app is unaffected.

Without the server, `run` produces a briefing from the command line:

```bash
.venv/bin/python -m cura run --topics technology
.venv/bin/python -m cura run --input examples/sample_articles.json --format newspaper --out daily.html
.venv/bin/python -m cura run --input examples/sample_articles.json --format audio --out brief.html
.venv/bin/python -m cura run --input examples/sample_articles.json --format json
```

`export-site` writes the day's edition as a static site with no server and no
key in the page, for hosting anywhere.

## Evaluation

Each result below comes from a script in the repo, with the data committed or fetched by script, so the numbers can be recomputed.

| Stage | Result |
|---|---|
| Stance | RoBERTa macro-F1 0.712 vs VADER 0.528 on TweetEval; 0.697 vs 0.493 on 200 hand-labelled headlines. Adopted. |
| Summarisation | BART beats TextRank on ROUGE but scores 0.895 on the faithfulness check where extractive output scores 1.000. Rejected as default. |
| Clustering | TF-IDF pair F1 0.950, a statistical tie with sentence embeddings, so the lighter one stays. |
| Triangulation | The contested flag agrees with my own labels at κ 0.533 at its best threshold. Under a tightened protocol two raters agree at κ 0.724 while the flag reaches κ 0.085, so stance dispersion captures only part of what readers call contested. |
| Narration | Coqui scores 0.73 MOS above the browser's Web Speech voice in a blind listening test. Adopted. |
| Users | Eight participants; usefulness median 4 of 5; audio the preferred daily format. |
| System | About 96% of end-to-end time is network fetching. |

The commands:

```bash
.venv/bin/python -m cura eval-stance --data <labelled.csv> [--transformer]
.venv/bin/python -m cura eval-summary --data <pairs.json> [--abstractive]
.venv/bin/python -m cura eval-clustering --pairs <pairs.csv> --snapshot <snapshot.json>
.venv/bin/python -m cura eval-triangulation --data <pack.csv> --model <pack.model.json> --sweep
.venv/bin/python -m cura eval-tts --data <ratings.csv>
.venv/bin/python -m cura eval-user-study
.venv/bin/python -m cura eval-latency --input examples/sample_articles.json --runs 5
```

Datasets, annotation packs, and protocols are described in
[cura/eval/datasets/README.md](cura/eval/datasets/README.md); results and
the round-by-round record are in `cura/eval/results/`. Third-party
benchmarks (TweetEval, CNN/DailyMail) are fetched by script rather than
committed.

## Layout

| Path | Contents |
|---|---|
| `cura/ingest/` | RSS and Reddit ingestion, the rolling store, dedupe, coverage expansion, event clustering |
| `cura/summarize/` | TextRank, optional BART |
| `cura/stance/` | VADER, optional RoBERTa |
| `cura/triangulate/` | the disagreement metric and contested flag |
| `cura/briefing/` | briefing assembly and the text and newspaper renderers |
| `cura/tts/` | Web Speech player and optional Coqui narration |
| `cura/orchestrator.py` | stage sequencing, fallback, per-stage timing |
| `cura/server.py` | the web server and the Cleo proxy |
| `cura/eval/` | evaluation harnesses, datasets, results |
| `web/` | the React interface; its README lists the data shapes the pipeline must produce |
| `examples/` | an offline fixture with one contested story |
| `tests/` | pytest suite, all offline |

`PROVENANCE.md` classifies every source file as original, adapted, or a thin
wrapper around a library, and names the papers the adapted algorithms come
from.

## Status

The core pipeline, all three output formats, the web app, and the evaluation
studies are complete. Not done: a mobile layout beyond responsive CSS, and
user accounts. Personalisation stops at topic selection and on-demand
editions.
