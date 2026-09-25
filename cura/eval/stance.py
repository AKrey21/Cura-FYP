# PROVENANCE: ORIGINAL - stance evaluation harness (macro-F1, per-class metrics,
# confusion matrix, reporting). Third-party: scikit-learn supplies the metric
# functions. See PROVENANCE.md.
"""Stance-classifier evaluation: macro-F1 (headline metric), per-class
precision/recall/F1, and a confusion matrix - accuracy alone is not accepted
because news sentiment is class-imbalanced (mostly negative/neutral).

Dataset format: CSV with `text` and `label` columns, labels in
{negative, neutral, positive}. Suggested benchmarks: SemEval-2017 Task 4A
(twitter sentiment) or a hand-labelled sample of ingested headlines; document
the choice and its class balance in the report.
"""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass

from sklearn.metrics import (classification_report, confusion_matrix, f1_score)

from cura.contracts import StanceResult
from cura.stance.base import StanceClassifier

LABELS = list(StanceResult.LABELS)
ECE_BINS = 10


@dataclass
class StanceEvalResult:
    classifier: str
    macro_f1: float
    accuracy: float
    per_class: dict          # sklearn classification_report dict
    confusion: list[list[int]]
    n: int
    ece: float | None = None   # None when the classifier reports no probs

    def table(self) -> str:
        lines = [f"classifier: {self.classifier}   n={self.n}",
                 f"macro-F1: {self.macro_f1:.3f}   accuracy: {self.accuracy:.3f}"]
        if self.ece is not None:
            lines.append(f"ECE ({ECE_BINS}-bin, max-prob confidence): {self.ece:.3f}")
        lines += ["",
                 f"{'class':<10} {'prec':>6} {'rec':>6} {'f1':>6} {'support':>8}"]
        for label in LABELS:
            row = self.per_class[label]
            lines.append(f"{label:<10} {row['precision']:>6.3f} {row['recall']:>6.3f} "
                         f"{row['f1-score']:>6.3f} {int(row['support']):>8}")
        lines += ["", "confusion matrix (rows=true, cols=pred; " + ", ".join(LABELS) + "):"]
        lines += ["  " + " ".join(f"{v:>5}" for v in row) for row in self.confusion]
        return "\n".join(lines)


def load_dataset(path: str) -> list[tuple[str, str]]:
    """Rows with a blank label are skipped (partially annotated packs);
    unknown non-blank labels are an error."""
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    data = [(r["text"], r["label"].strip().lower()) for r in rows
            if r["label"].strip()]
    bad = {label for _, label in data} - set(LABELS)
    if bad:
        raise ValueError(f"unknown labels in {path}: {bad} (expected {LABELS})")
    return data


def _ece(conf_correct: list[tuple[float, bool]], bins: int = ECE_BINS) -> float:
    """Expected calibration error: |accuracy − mean confidence| per
    equal-width confidence bin, weighted by bin occupancy."""
    total = len(conf_correct)
    ece = 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        bucket = [(c, ok) for c, ok in conf_correct
                  if lo <= c < hi or (b == bins - 1 and c == 1.0)]
        if not bucket:
            continue
        conf = sum(c for c, _ in bucket) / len(bucket)
        acc = sum(ok for _, ok in bucket) / len(bucket)
        ece += (len(bucket) / total) * abs(acc - conf)
    return ece


def evaluate(classifier: StanceClassifier, data: list[tuple[str, str]]) -> StanceEvalResult:
    y_true = [label for _, label in data]
    results = [classifier.classify(text) for text, _ in data]
    y_pred = [r.label for r in results]
    report = classification_report(y_true, y_pred, labels=LABELS,
                                   output_dict=True, zero_division=0)
    conf_correct = [(max(r.probs.values()), r.label == t)
                    for r, t in zip(results, y_true) if r.probs]
    return StanceEvalResult(
        classifier=classifier.name,
        macro_f1=f1_score(y_true, y_pred, labels=LABELS, average="macro", zero_division=0),
        accuracy=report["accuracy"],
        per_class=report,
        confusion=confusion_matrix(y_true, y_pred, labels=LABELS).tolist(),
        n=len(data),
        ece=_ece(conf_correct) if conf_correct else None,
    )


def export_headline_pack(articles, csv_path: str, n: int = 200,
                         seed: int = 7) -> int:
    """Blind annotation pack for the domain-gap check: a seeded sample of
    ingested headlines with an empty ``label`` column (negative / neutral /
    positive). No model output anywhere near it - same blinding rule as the
    triangulation pack."""
    unique: dict[str, object] = {}
    for a in articles:
        unique.setdefault(a.title.strip().casefold(), a)
    pool = list(unique.values())
    random.Random(seed).shuffle(pool)
    picked = pool[:n]
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["id", "source", "text", "label"])
        for a in picked:
            writer.writerow([a.id, a.source, a.title.strip(), ""])
    return len(picked)
