# Stance benchmark - VADER baseline vs fine-tuned RoBERTa

**Date:** 2026-06-11
**Dataset:** TweetEval `sentiment` (= SemEval-2017 Task 4A, 3-class tweet
sentiment), test split, n=1000 sampled in chunks spread across the split
(fetched with `python cura/eval/datasets/fetch_tweeteval_sentiment.py 1000`).
**Class balance:** negative 317 / neutral 491 / positive 192 - imbalanced,
which is why macro-F1 (not accuracy) is the headline metric.
**Command:** `python -m cura eval-stance --data cura/eval/datasets/tweeteval_sentiment_test_1000.csv --transformer`
**Versions:** transformers 4.57.6 · torch 2.12.0 (CPU) · vaderSentiment 3.3
**Models:** VADER lexicon (zero-shot, cura/stance/vader.py) vs
`cardiffnlp/twitter-roberta-base-sentiment-latest` (cura/stance/transformer.py).
**Training disclosure:** the RoBERTa checkpoint is *fine-tuned on TweetEval's
training split* (standard benchmark setting; train/test separation respected).
VADER is an untrained lexicon. State both in the report.

## Results

| classifier | macro-F1 | accuracy | ms/text (CPU) |
|---|---|---|---|
| VADER (baseline) | 0.528 | 0.531 | 0.1 |
| RoBERTa (fine-tuned) | **0.712** | **0.709** | 32 |

Per-class F1:

| class | VADER | RoBERTa |
|---|---|---|
| negative | 0.560 | 0.728 |
| neutral | 0.550 | 0.690 |
| positive | 0.473 | 0.718 |

Confusion matrices (rows = true, cols = predicted; negative/neutral/positive):

```
VADER                      RoBERTa
167    65    85            253    60     4
101   228   162            118   312    61
 11    45   136              7    41   144
```

## Reading

- **RoBERTa beats VADER by +18.4 macro-F1 points** and is balanced across
  classes (F1 0.69–0.73); VADER's errors are structural, not random:
  - *Positive over-prediction:* VADER predicts positive 383 times for 192
    true positives (precision 0.355) - lexicon hits on positive words ignore
    sarcasm, idiom, and negation scope.
  - *Neutral leakage:* neutral recall 0.464 - any sentiment-laden word in an
    otherwise neutral tweet fires the lexicon.
- **Cost of adoption:** 32 ms/text on CPU ≈ ~5 s of stance classification per
  edition (~145 articles) vs ~0.01 s for VADER, plus a ~500 MB model. That is
  affordable inside the 15-minute refresh.
- **For triangulation:** RoBERTa's softmax probabilities feed the entropy
  metric more sensibly than VADER's lexicon shares, but verify calibration
  (reliability diagram / ECE on this sample) before leaning on entropy in the
  report - flagged as future work.

## Decision (per the adoption rule in cura/stance/transformer.py)

Macro-F1 0.712 > 0.528 - the transformer clearly earns its slot, and the
latency cost is acceptable. Adopted as the opt-in `--stance-transformer`
mode on `cura run` / `cura serve` (VADER remains the no-dependency default
on the light stack, per the project conventions). Caveat for the report:
this benchmark is tweets (deployment is headlines + article leads); a
hand-labelled sample of ingested headlines (datasets README) is the
strongest follow-up evidence.

## Reproduce

```bash
pip install -e ".[dev,stance-transformer]"
python cura/eval/datasets/fetch_tweeteval_sentiment.py 1000
python -m cura eval-stance --data cura/eval/datasets/tweeteval_sentiment_test_1000.csv --transformer
```
