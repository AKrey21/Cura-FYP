# PROVENANCE: ORIGINAL - summariser evaluation harness; the novel-bigram
# faithfulness metric is original. Third-party: rouge-score for ROUGE.
# See PROVENANCE.md.
"""Summariser evaluation: ROUGE-1/2/L against references plus a faithfulness
check, so an abstractive model is adopted only if it beats the TextRank
baseline on *both* (ROUGE rewards overlap; faithfulness penalises content the
source never said - the abstractive failure mode).

Faithfulness proxy: novel-bigram precision - the fraction of summary bigrams
that appear in the source document. 1.0 for extractive output by construction;
abstractive models score lower as they hallucinate. (For the report, optionally
corroborate with an NLI entailment checker on a sample.)

Dataset format: JSON list of {"document": ..., "reference": ...} pairs -
e.g. a sample of CNN/DailyMail.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from cura.summarize.base import Summarizer

_TOKEN_RE = re.compile(r"[a-z0-9']+")


def _bigrams(text: str) -> set[tuple[str, str]]:
    tokens = _TOKEN_RE.findall(text.lower())
    return set(zip(tokens, tokens[1:]))


def faithfulness(summary: str, document: str) -> float:
    """Fraction of summary bigrams grounded in the source document.

    Bigrams are collected per summary sentence so that the join between two
    non-adjacent extracted sentences is not counted as a (spurious) novel
    bigram - extractive output scores 1.0 by construction.
    """
    from cura.summarize.base import split_sentences

    summary_bigrams: set[tuple[str, str]] = set()
    for sentence in split_sentences(summary) or [summary]:
        summary_bigrams |= _bigrams(sentence)
    if not summary_bigrams:
        return 1.0
    return len(summary_bigrams & _bigrams(document)) / len(summary_bigrams)


@dataclass
class SummaryEvalResult:
    summarizer: str
    rouge1: float
    rouge2: float
    rougeL: float
    faithfulness: float
    n: int

    def table(self) -> str:
        return (f"summarizer: {self.summarizer}   n={self.n}\n"
                f"ROUGE-1: {self.rouge1:.3f}  ROUGE-2: {self.rouge2:.3f}  "
                f"ROUGE-L: {self.rougeL:.3f}  faithfulness: {self.faithfulness:.3f}")


def load_dataset(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    for row in data:
        if "document" not in row or "reference" not in row:
            raise ValueError(f"{path}: each row needs 'document' and 'reference'")
    return data


def evaluate(summarizer: Summarizer, data: list[dict],
             max_sentences: int = 3) -> SummaryEvalResult:
    from rouge_score import rouge_scorer  # optional extra: pip install -e ".[eval]"
    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)

    totals = {"rouge1": 0.0, "rouge2": 0.0, "rougeL": 0.0, "faith": 0.0}
    for row in data:
        summary = summarizer.summarize(row["document"], max_sentences=max_sentences)
        scores = scorer.score(row["reference"], summary.text)
        for key in ("rouge1", "rouge2", "rougeL"):
            totals[key] += scores[key].fmeasure
        totals["faith"] += faithfulness(summary.text, row["document"])

    n = len(data)
    return SummaryEvalResult(summarizer=summarizer.name,
                             rouge1=totals["rouge1"] / n, rouge2=totals["rouge2"] / n,
                             rougeL=totals["rougeL"] / n, faithfulness=totals["faith"] / n,
                             n=n)
