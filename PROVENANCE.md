# Code provenance

What in this repository was written for Cura, what was implemented from a
published method, and what is a thin wrapper around someone else's package.
Three classes:

- original: written for this project.
- adapted: a published algorithm implemented here from its description. The
  code is mine; the idea is cited.
- library: a wrapper whose substance is a third-party package. Only the glue
  is mine.

Each source file states its class in a one-line header comment.

## Summary

| Area | Files | Original | Adapted | Library |
|---|---|---|---|---|
| `cura/` pipeline | 44 | 37 | 3 | 4 |
| `design/` interface | 14 | 14 | 0 | 0 |
| `tests/` | 9 | 9 | 0 | 0 |

The research contribution is the disagreement metric in
`cura/triangulate/metrics.py` and the orchestration in `cura/orchestrator.py`.

## Pipeline (`cura/`)

### Core

| File | Class | Notes |
|---|---|---|
| `__init__.py` | original | package docstring, version |
| `__main__.py` | original | entry point |
| `contracts.py` | original | dataclasses; `to_ui_dict()` maps to the UI contracts in `design/HANDOFF.md` |
| `orchestrator.py` | original | stage sequencing, per-stage fallback to baselines, latency instrumentation, topic-diverse pool selection |
| `cli.py` | original | commands (argparse) |
| `progress.py` | original | weighted build-progress reporter for the terminal and `/api/status` |
| `server.py` | original | local web server, background `EditionCache`, live-data injection, Cleo endpoints (`http.server`; the `anthropic` SDK for the optional Cleo proxy) |
| `export_site.py` | original | static site export with no API calls |

### Ingestion (`cura/ingest/`)

| File | Class | Notes |
|---|---|---|
| `__init__.py` | original | re-exports |
| `rss.py` | original | feed list, normalisation, lead-image heuristics, parallel fetch; feedparser parses RSS/Atom |
| `reddit.py` | original | Reddit public-JSON ingestion (urllib) |
| `fulltext.py` | original | fetch orchestration, gain gating, sentence cleanup; trafilatura extracts the text |
| `expand.py` | original | Google News coverage expansion for under-sourced stories; feedparser parses |
| `dedupe.py` | original | URL canonicalisation and normalised-title dedup |
| `cluster.py` | adapted | sequential leader clustering (Hartigan, 1975) over scikit-learn TF-IDF cosine; the named-entity gate is this project's addition |
| `cluster_embed.py` | adapted | the same `leader_cluster` and gate over sentence-transformers embeddings (all-MiniLM-L6-v2) |
| `store.py` | original | rolling 72-hour article store with first-seen pruning |

### Summarisation (`cura/summarize/`)

| File | Class | Notes |
|---|---|---|
| `__init__.py` | original | re-exports |
| `base.py` | original | `Summarizer` protocol, sentence splitter |
| `textrank.py` | adapted | TextRank (Mihalcea and Tarau, 2004): PageRank power iteration over a TF-IDF cosine sentence graph, with scikit-learn and numpy |
| `abstractive.py` | library | Hugging Face transformers summarisation pipeline (BART/Pegasus); token-budget truncation is the glue |

### Stance (`cura/stance/`)

| File | Class | Notes |
|---|---|---|
| `__init__.py` | original | re-exports |
| `base.py` | original | `StanceClassifier` protocol |
| `vader.py` | library | vaderSentiment (Hutto and Gilbert, 2014); the glue maps its output to `StanceResult` |
| `transformer.py` | library | transformers text-classification pipeline with the cardiffnlp RoBERTa checkpoint; label map and signed score are the glue |

### Triangulation (`cura/triangulate/`)

| File | Class | Notes |
|---|---|---|
| `__init__.py` | original | re-exports |
| `metrics.py` | original | the cross-source disagreement metric: spread of signed stance scores, normalised entropy of the soft-vote label distribution, contested flag; standard-library maths |

### Briefing (`cura/briefing/`)

| File | Class | Notes |
|---|---|---|
| `__init__.py` | original | re-exports |
| `assemble.py` | original | five-minute assembly, story and segment building, Verify payload, trend extraction, coverage-bias spread; `OUTLET_LEAN` is reference data from public AllSides and Ad Fontes ratings |
| `render_text.py` | original | text renderer |
| `render_newspaper.py` | original | one-page newspaper renderer (HTML/CSS; Google Fonts at render time) |

### Text-to-speech (`cura/tts/`)

| File | Class | Notes |
|---|---|---|
| `__init__.py` | original | re-exports |
| `webspeech.py` | original | audio-player page with transcript sync; narration by the browser's Web Speech API (the baseline) |
| `server.py` | library | Coqui TTS (Tacotron 2); character map and length capping are the glue |

### Evaluation (`cura/eval/`)

| File | Class | Notes |
|---|---|---|
| `__init__.py` | original | package marker |
| `stance.py` | original | macro-F1, per-class metrics, confusion matrix; metric functions from scikit-learn |
| `summary.py` | original | summariser harness; the novel-bigram faithfulness check is this project's; ROUGE from rouge-score |
| `triangulation.py` | original | blind annotation pack, agreement statistics, threshold sweep; Cohen's kappa from its definition |
| `clustering.py` | original | hard-pair sampling, pair precision/recall/F1; TF-IDF from scikit-learn |
| `latency.py` | original | per-stage and end-to-end latency, percentiles by linear interpolation |
| `tts.py` | original | blind MOS listening-test page and confidence-interval aggregation (ITU-T P.800 method) |
| `user_study.py` | original | Likert medians and IQR, format rankings, contested-flag agreement, non-response and tie handling |
| `datasets/fetch_cnn_dailymail.py` | original | fetch script for a third-party dataset |
| `datasets/fetch_tweeteval_sentiment.py` | original | fetch script for a third-party dataset |

## Interface (`design/`)

The React interface that `cura serve` renders. There is no build step: React 18,
ReactDOM and Babel standalone load from a CDN and transpile the `.jsx` in the
browser. Those packages and Google Fonts are the only third-party parts.

| File(s) | Class | Notes |
|---|---|---|
| `Cura - Desktop.html` | original | page shell: CSS tokens, fonts, script order |
| `app/*.jsx` (11 files) | original | views and state; `data.jsx` holds sample data replaced live by `window.CURA_LIVE`; `listen.jsx` uses the Web Speech API; `cleo.jsx` and `read.jsx` call the Cleo endpoint with offline fallbacks; `tour.jsx` is the guided tour |
| `components/*.jsx` (2 files) | original | browser frame, tweaks panel |
| `HANDOFF.md` | original | data-contract specification |

## Tests and packaging

| File(s) | Class | Notes |
|---|---|---|
| `tests/*.py` (conftest and 8 test files) | original | pytest suite |
| `pyproject.toml` | original | packaging and optional extras |
| `README.md` | original | project documentation |

## Third-party packages

### Core

| Package | Used for | Licence |
|---|---|---|
| feedparser | RSS/Atom parsing | BSD |
| vaderSentiment | VADER lexicon (stance baseline) | MIT |
| scikit-learn | TF-IDF, cosine similarity, classification metrics | BSD |
| numpy | arrays | BSD |

### Optional extras

| Package | Extra | Used for | Licence |
|---|---|---|---|
| rouge-score | dev, eval | ROUGE | Apache-2.0 |
| pytest | dev | test runner | MIT |
| trafilatura | fulltext | article extraction | Apache-2.0 |
| transformers | abstractive, stance-transformer | BART summaries, RoBERTa stance | Apache-2.0 |
| torch | with the above | model backend | BSD-style |
| sentence-transformers | embeddings | clustering embeddings | Apache-2.0 |
| coqui-tts | tts | neural narration | MPL-2.0 |
| anthropic | cleo | Cleo chat and Verify proxy | MIT |

### Front end (CDN)

| Package | Used for | Licence |
|---|---|---|
| React 18, ReactDOM | interface | MIT |
| @babel/standalone | in-browser JSX transpile | MIT |
| Google Fonts (Fraunces, Inter, JetBrains Mono) | typography | SIL OFL |

## Pre-trained models (downloaded at runtime)

| Model | Stage | Origin |
|---|---|---|
| facebook/bart-large-cnn | abstractive summary | Lewis et al., 2019 |
| cardiffnlp/twitter-roberta-base-sentiment-latest | transformer stance | Barbieri et al., 2020 |
| sentence-transformers/all-MiniLM-L6-v2 | embedding clustering | Wang et al., 2020; Reimers and Gurevych, 2019 |
| tts_models/en/ljspeech/tacotron2-DDC | neural TTS | Shen et al., 2018, trained on LJSpeech |
| Claude (claude-haiku-4-5) | Cleo editor and Verify | Anthropic API |

## Published methods implemented here

| Method | Where | Reference |
|---|---|---|
| TextRank | `summarize/textrank.py` | Mihalcea and Tarau, 2004; PageRank, Brin and Page, 1998 |
| Sequential leader clustering | `ingest/cluster.py` | Hartigan, 1975; the entity gate is this project's |
| TF-IDF and cosine similarity | clustering, summarisation | Spärck Jones, 1972 |
| Shannon entropy | `triangulate/metrics.py` | Shannon, 1948 |
| Cohen's kappa | `eval/triangulation.py` | Cohen, 1960 |
| ROUGE | `eval/summary.py` | Lin, 2004, via rouge-score |
| Macro-F1, confusion matrix | `eval/stance.py` | via scikit-learn |
| Mean opinion score | `eval/tts.py` | ITU-T P.800 |

## External datasets and reference data

| Data | Where | Origin |
|---|---|---|
| CNN/DailyMail | summarisation benchmark | Hermann et al., 2015; See et al., 2017 |
| TweetEval sentiment (SemEval-2017 Task 4A) | stance benchmark | Rosenthal et al., 2017; Barbieri et al., 2020 |
| LJSpeech | the Tacotron 2 voice | Ito and Johnson, 2017 |
| AllSides and Ad Fontes media-bias ratings | `OUTLET_LEAN` in `briefing/assemble.py` | public bias charts, approximate and US-centric |
