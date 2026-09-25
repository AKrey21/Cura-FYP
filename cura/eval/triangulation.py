# PROVENANCE: ORIGINAL - triangulation-validation harness: blind annotation pack,
# agreement stats and threshold sweep. Cohen's kappa implemented from its
# definition (standard measure). Stdlib only. See PROVENANCE.md.
"""Triangulation validation: does the contested flag agree with people?

The disagreement metrics (spread, entropy - cura/triangulate/metrics.py) are
hypotheses; the evaluation plan requires validating them against human
judgement of which stories are contested. Three pieces:

1. ``export_annotation_pack`` - writes a *blind* annotation CSV (one row per
   multi-source story with the per-source headlines + snippets a human needs,
   plus an empty ``contested`` column; no model verdicts, so the annotator
   isn't anchored) and a JSON sidecar holding the model's spread/entropy/flag
   per story for scoring later.
2. ``evaluate`` - agreement between the flag and the human labels: accuracy,
   precision/recall/F1 on the contested class, and Cohen's kappa. Kappa is
   the headline number - contested stories are the rare class, so raw
   accuracy flatters a never-contested predictor.
3. ``sweep`` - grid over (spread_threshold, entropy_threshold), re-deriving
   the flag from the stored metrics, to find the best operating point and
   show how sensitive agreement is around the defaults.

Annotation protocol (also in cura/eval/results/triangulation-protocol.md):
for each row, read every source's headline + snippet and mark ``contested``
as yes when the sources visibly disagree in framing or substance (tone,
blame, emphasis, or facts) - not merely when the topic itself is divisive.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass

from cura.contracts import StoryCluster
from cura.ingest import cluster_articles, dedupe_articles
from cura.stance.base import StanceClassifier
from cura.stance.vader import VaderStanceClassifier
from cura.triangulate import triangulate
from cura.triangulate.metrics import ENTROPY_THRESHOLD, SPREAD_THRESHOLD

SNIPPET_WORDS = 30
_TRUE = {"y", "yes", "1", "true", "contested"}
_FALSE = {"n", "no", "0", "false", "not contested", "uncontested"}


def collect_clusters(articles, stance_classifier: StanceClassifier | None = None,
                     min_sources: int = 2, limit: int = 30) -> list[StoryCluster]:
    """Multi-source clusters with triangulation attached - the stories worth
    annotating. Summarisation is skipped: annotators read the sources raw."""
    clf = stance_classifier or VaderStanceClassifier()
    articles = dedupe_articles(articles)
    clusters = [c for c in cluster_articles(articles)
                if c.n_sources >= min_sources][:limit]
    for cluster in clusters:
        by_source = {}
        for a in cluster.articles:
            by_source.setdefault(a.source, clf.classify(f"{a.title}. {a.body[:500]}"))
        cluster.triangulation = triangulate(by_source)
    return clusters


def _snippet(body: str, words: int = SNIPPET_WORDS) -> str:
    tokens = body.split()
    text = " ".join(tokens[:words])
    return text + ("…" if len(tokens) > words else "")


def export_annotation_pack(clusters: list[StoryCluster], csv_path: str,
                           sidecar_path: str) -> int:
    """Blind CSV for the annotator + model sidecar for the scorer."""
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["id", "headline", "n_sources", "coverage",
                         "contested", "notes"])
        for c in clusters:
            seen: set[str] = set()
            lines = []
            for a in c.articles:
                if a.source in seen:
                    continue
                seen.add(a.source)
                lines.append(f"[{a.source}] {a.title} — {_snippet(a.body)}")
            writer.writerow([c.id, c.articles[0].title, c.n_sources,
                             "\n".join(lines), "", ""])
    with open(sidecar_path, "w", encoding="utf-8") as fh:
        json.dump([{"id": c.id,
                    "headline": c.articles[0].title,
                    "n_sources": c.triangulation.n_sources,
                    "spread": c.triangulation.spread,
                    "entropy": c.triangulation.entropy,
                    "contested": c.triangulation.contested}
                   for c in clusters], fh, indent=2)
    return len(clusters)


def load_annotations(csv_path: str) -> tuple[dict[str, bool], int]:
    """id -> human contested label; blank/unparsable rows are skipped and
    counted so the report can state coverage honestly."""
    labels: dict[str, bool] = {}
    skipped = 0
    with open(csv_path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            raw = (row.get("contested") or "").strip().casefold()
            if raw in _TRUE:
                labels[row["id"]] = True
            elif raw in _FALSE:
                labels[row["id"]] = False
            else:
                skipped += 1
    return labels, skipped


def load_sidecar(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _agreement(y_true: list[bool], y_pred: list[bool]) -> dict:
    n = len(y_true)
    tp = sum(t and p for t, p in zip(y_true, y_pred))
    fp = sum((not t) and p for t, p in zip(y_true, y_pred))
    fn = sum(t and (not p) for t, p in zip(y_true, y_pred))
    tn = n - tp - fp - fn
    accuracy = (tp + tn) / n if n else 0.0
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = (2 * precision * recall / (precision + recall)
          if precision + recall else 0.0)
    # Cohen's kappa: chance-corrected agreement for two raters
    p_yes = ((tp + fp) / n) * ((tp + fn) / n) if n else 0.0
    p_no = ((tn + fn) / n) * ((tn + fp) / n) if n else 0.0
    p_e = p_yes + p_no
    kappa = (accuracy - p_e) / (1 - p_e) if p_e < 1 else 1.0
    return {"n": n, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "accuracy": accuracy, "precision": precision,
            "recall": recall, "f1": f1, "kappa": kappa}


@dataclass
class TriangulationEvalResult:
    stats: dict
    skipped: int
    spread_threshold: float
    entropy_threshold: float

    def table(self) -> str:
        s = self.stats
        lines = [
            f"contested flag vs human labels   n={s['n']}"
            + (f"   ({self.skipped} unannotated rows skipped)" if self.skipped else ""),
            f"thresholds: spread >= {self.spread_threshold:.2f} "
            f"or entropy >= {self.entropy_threshold:.2f}",
            "",
            f"Cohen's kappa: {s['kappa']:.3f}   accuracy: {s['accuracy']:.3f}",
            f"contested class — precision: {s['precision']:.3f}   "
            f"recall: {s['recall']:.3f}   F1: {s['f1']:.3f}",
            "",
            "confusion (rows=human, cols=model; contested, not):",
            f"  {s['tp']:>4} {s['fn']:>4}",
            f"  {s['fp']:>4} {s['tn']:>4}",
        ]
        return "\n".join(lines)


def _flags(rows: list[dict], spread_t: float, entropy_t: float) -> list[bool]:
    return [r["n_sources"] >= 2 and (r["spread"] >= spread_t
                                     or r["entropy"] >= entropy_t)
            for r in rows]


def evaluate(annotated_csv: str, sidecar_path: str,
             spread_threshold: float = SPREAD_THRESHOLD,
             entropy_threshold: float = ENTROPY_THRESHOLD) -> TriangulationEvalResult:
    labels, skipped = load_annotations(annotated_csv)
    rows = [r for r in load_sidecar(sidecar_path) if r["id"] in labels]
    if not rows:
        raise ValueError(f"no annotated rows in {annotated_csv} match "
                         f"{sidecar_path} — fill the `contested` column first")
    y_true = [labels[r["id"]] for r in rows]
    y_pred = _flags(rows, spread_threshold, entropy_threshold)
    return TriangulationEvalResult(stats=_agreement(y_true, y_pred),
                                   skipped=skipped,
                                   spread_threshold=spread_threshold,
                                   entropy_threshold=entropy_threshold)


def sweep(annotated_csv: str, sidecar_path: str,
          spread_grid: list[float] | None = None,
          entropy_grid: list[float] | None = None) -> str:
    """Threshold grid, ranked by kappa - shows the best operating point and
    whether the defaults sit on a plateau or a cliff."""
    labels, _ = load_annotations(annotated_csv)
    rows = [r for r in load_sidecar(sidecar_path) if r["id"] in labels]
    if not rows:
        raise ValueError("no annotated rows to sweep over")
    y_true = [labels[r["id"]] for r in rows]
    spread_grid = spread_grid or [round(0.05 * i, 2) for i in range(13)]   # 0–0.6
    entropy_grid = entropy_grid or [round(0.5 + 0.05 * i, 2) for i in range(11)]  # 0.5–1.0
    results = []
    for st in spread_grid:
        for et in entropy_grid:
            stats = _agreement(y_true, _flags(rows, st, et))
            results.append((st, et, stats["kappa"], stats["f1"]))
    results.sort(key=lambda r: (-r[2], -r[3]))
    lines = [f"threshold sweep over {len(rows)} annotated stories "
             f"(ranked by kappa; defaults marked *):",
             f"{'spread>=':>9} {'entropy>=':>10} {'kappa':>7} {'f1':>7}"]
    defaults = (SPREAD_THRESHOLD, ENTROPY_THRESHOLD)
    for st, et, kappa, f1 in results[:10]:
        mark = " *" if (st, et) == defaults else ""
        lines.append(f"{st:>9.2f} {et:>10.2f} {kappa:>7.3f} {f1:>7.3f}{mark}")
    if defaults not in {(st, et) for st, et, _, _ in results[:10]}:
        stats = _agreement(y_true, _flags(rows, *defaults))
        lines.append(f"{defaults[0]:>9.2f} {defaults[1]:>10.2f} "
                     f"{stats['kappa']:>7.3f} {stats['f1']:>7.3f} *(default)")
    return "\n".join(lines)
