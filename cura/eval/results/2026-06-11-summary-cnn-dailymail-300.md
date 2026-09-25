# Summarisation benchmark - TextRank baseline vs abstractive BART

**Date:** 2026-06-11
**Dataset:** CNN/DailyMail 3.0.0, test split, first 300 articles
(fetched with `python cura/eval/datasets/fetch_cnn_dailymail.py 300`;
references are the dataset's human-written highlights)
**Command:** `python -m cura eval-summary --data cura/eval/datasets/cnn_dailymail_test_300.json --abstractive`
**Versions:** transformers 4.57.6 · torch 2.12.0 (CPU) · rouge-score 0.1.2
**Models:** TextRank (cura/summarize/textrank.py, light stack) vs
`facebook/bart-large-cnn` (cura/summarize/abstractive.py)
**Settings:** `max_sentences=3` for both; ROUGE F-measure with stemming;
faithfulness = per-sentence novel-bigram precision against the source
(1.0 = every bigram grounded; extractive scores 1.0 by construction).

## Results

| summariser | ROUGE-1 | ROUGE-2 | ROUGE-L | faithfulness | cost |
|---|---|---|---|---|---|
| TextRank (baseline) | 0.265 | 0.091 | 0.181 | **1.000** | <1 min for all 300, free, offline |
| BART (`bart-large-cnn`) | **0.349** | **0.146** | **0.259** | 0.895 | ~30 min for 300 on CPU, 1.6 GB model |

## Reading

- **ROUGE:** BART wins decisively - +8.4 / +5.5 / +7.8 points absolute on
  ROUGE-1/2/L. Its summaries overlap far more with the human-written
  highlights. (Note `bart-large-cnn` is fine-tuned on CNN/DailyMail, so this
  is its home turf; treat these as an upper bound for news-domain gains.)
- **Faithfulness:** TextRank is perfectly grounded by construction; BART
  generates ~10.5% of its bigrams without direct support in the source -
  the abstractive failure mode the metric exists to expose. Spot-check a
  sample of low-faithfulness outputs for actual hallucination vs benign
  paraphrase before quoting this in the report.
- **Cost:** TextRank summarises the whole sample in under a minute on the
  light stack; BART needs roughly half an hour on CPU (~6 s/article) and a
  1.6 GB model download.

## Decision (per the adoption rule in cura/summarize/abstractive.py)

The rule is *adopt only if it beats TextRank on ROUGE **and** the
faithfulness check*. BART clearly wins ROUGE but cannot beat a perfectly
grounded extractive baseline on faithfulness (0.895 < 1.000). Combined with
the latency/footprint cost, **TextRank stays the product default**; BART
remains the opt-in `--abstractive` mode. For the report this is the
trade-off finding: fluency/overlap vs verifiability - and verifiability is
the product's core promise ("every sentence traceable to a source").

## Reproduce

```bash
pip install -e ".[dev,abstractive]"
python cura/eval/datasets/fetch_cnn_dailymail.py 300
python -m cura eval-summary --data cura/eval/datasets/cnn_dailymail_test_300.json --abstractive
```
