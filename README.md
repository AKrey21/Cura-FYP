# Cura - AI news intelligence

Final-year project ("Orchestrating AI Models" template). Cura orchestrates
summarisation, stance classification, and text-to-speech into a single
pipeline, turning multi-source coverage of chosen topics into a personalised
~5-minute daily briefing - text, audio, or a one-page newspaper.

The research contribution is the **orchestration** plus **cross-source stance
triangulation**: for stories covered by two or more sources, the pipeline
quantifies disagreement (spread of a signed stance score + label-distribution
entropy) and flags contested coverage. Every model choice is justified against
a baseline on a benchmark - see [`design/HANDOFF.md`](design/HANDOFF.md) for the UI
prototype and the data contracts the pipeline targets.

## Pipeline

```
choose topics → ingest (RSS + Reddit) → dedupe → cluster by event
             → summarise (TextRank, ↗ BART/Pegasus)
             → stance   (VADER,    ↗ fine-tuned RoBERTa)
             → triangulate disagreement (spread + entropy → "contested")
             → assemble ~5-min briefing → render (text now; audio/newspaper next)
```

Each model sits behind a small protocol so baselines and stretch models are
swappable and evaluable in isolation; the orchestrator falls back to the
baseline if a stretch model fails, and records per-stage latency for the
system evaluation.

## Quickstart - run the whole app

```bash
# one-time setup
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"

# one line: ingest live news (RSS + Reddit), run the AI pipeline,
# open the Cura web app in your browser with today's real edition
.venv/bin/python -m cura serve
```

That starts the full product: live multi-source ingestion → dedupe → event
clustering → summarisation → stance → triangulation, rendered in the
high-fidelity UI (Read / Listen / Experience / Verify / Cleo). The edition
re-runs every 15 minutes. Variants:

```bash
.venv/bin/python -m cura serve --topics technology economy   # personalised
.venv/bin/python -m cura serve --input examples/sample_articles.json  # offline demo
export ANTHROPIC_API_KEY=sk-ant-...   # + pip install -e ".[cleo]"
.venv/bin/python -m cura serve        # Cleo chat + Verify answer with a real LLM
```

**What's free vs paid:** news ingestion (RSS feeds + Reddit's public JSON),
the NLP pipeline (TextRank, VADER, clustering, triangulation), and the Listen
narration (browser Web Speech API) all cost nothing and need no keys. The
only paid piece is **Cleo chat / Verify claim-checking**, which needs an
Anthropic API key (Console billing, pay-per-token; a Claude Pro/Max plan does
not include API keys). Without a key those two features run in the
prototype's scripted demo mode - everything else is fully live.

### CLI output formats (no server)

```bash
.venv/bin/python -m cura run --topics technology                     # text feed
.venv/bin/python -m cura run --input examples/sample_articles.json --format json       # UI contract JSON
.venv/bin/python -m cura run --input examples/sample_articles.json --format newspaper --out daily.html
.venv/bin/python -m cura run --input examples/sample_articles.json --format audio --out brief.html
```

## Evaluation harness

```bash
# Stance: macro-F1 + per-class metrics + confusion matrix, VADER baseline
.venv/bin/python -m cura eval-stance --data labelled.csv [--transformer]

# Summarisation: ROUGE-1/2/L + faithfulness (grounded-bigram precision)
.venv/bin/python -m cura eval-summary --data pairs.json [--abstractive]
```

Dataset formats and suggested benchmarks (SemEval, CNN/DailyMail, hand-labelled
headline samples, triangulation human-judgement protocol):
[`cura/eval/datasets/README.md`](cura/eval/datasets/README.md).

## Layout

| Path | What |
|---|---|
| `design/` | The web interface (React, served by `cura serve`) and its binding data contracts |
| `cura/ingest/` | RSS + Reddit ingestion, URL/title dedupe, TF-IDF event clustering |
| `cura/summarize/` | TextRank baseline; optional abstractive (`pip install -e ".[abstractive]"`) |
| `cura/stance/` | VADER baseline; optional transformer (`".[stance-transformer]"`) |
| `cura/triangulate/` | Disagreement metrics: stance-score spread, label entropy, contested flag |
| `cura/briefing/` | ~5-minute assembly + text and newspaper renderers (emits `Story` / `CURA_BRIEFING` shapes) |
| `cura/tts/` | Web Speech audio-player baseline; optional Coqui server TTS (`".[tts]"`) |
| `cura/orchestrator.py` | Stage sequencing, graceful fallback, latency report |
| `cura/server.py` | `cura serve`: serves the design prototype with live pipeline data + Cleo API proxy |
| `cura/eval/` | Stance / summary metric harnesses + dataset guide |
| `examples/` | Offline article fixture (multi-source, one deliberately contested story) |
| `tests/` | pytest suite (all offline) |

## Status / build order

1. ✅ **Core path** - ingestion → summarise → stance → triangulation → text
   briefing, with stance + summarisation eval harnesses and per-stage latency.
2. ✅ Audio (Web Speech player baseline, optional Coqui server TTS) and the
   one-page newspaper renderer (`--format newspaper|audio`).
3. ✅ Web delivery - `cura serve` runs the pipeline and serves the design
   prototype with live data; Cleo/Verify proxy to the Anthropic API.
   ⬜ Remaining: scheduling (cron the daily edition), mobile/iOS parity,
   user accounts, and the evaluation runs on real benchmarks for the report.
