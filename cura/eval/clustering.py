# PROVENANCE: ORIGINAL - clustering pair-benchmark harness (hard-pair sampling,
# pair precision/recall/F1, cluster-shape stats). Third-party: scikit-learn
# (TF-IDF for candidate sampling). See PROVENANCE.md.
"""Event-clustering evaluation - pair-labelled benchmark, baseline vs stretch.

A clusterer is good when two articles about the same event land in the same
cluster (pair recall) and two articles about different events don't (pair
precision). The benchmark:

1. ``export_pair_annotation`` - from a real corpus, sample *hard* candidate
   pairs: the top cross-outlet pairs under TF-IDF similarity, the top pairs
   under embedding similarity (when installed), and a random mid-similarity
   band. Sampling from both representations keeps the set from favouring
   either method. Writes a blind annotation CSV (both articles' title +
   lead, empty ``same_event`` column) plus a corpus snapshot JSON so the
   labels stay attached to the exact articles they were made on.
2. ``evaluate_pairs`` - cluster the snapshot with a given clusterer and
   score the labelled pairs: precision/recall/F1 on same-event (positive),
   plus cluster-shape stats. Run once per clusterer; compare.
"""

from __future__ import annotations

import csv
import json
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from cura.contracts import Article
from cura.ingest import dedupe_articles
from cura.ingest.cluster import _doc

_TRUE = {"y", "yes", "1", "true", "same"}
_FALSE = {"n", "no", "0", "false", "different"}


def _lead(article: Article, words: int = 30) -> str:
    tokens = article.body.split()
    return " ".join(tokens[:words]) + ("…" if len(tokens) > words else "")


def _art_to_dict(a: Article) -> dict:
    return {"id": a.id, "source": a.source, "url": a.url, "title": a.title,
            "body": a.body, "topic": a.topic, "source_kind": a.source_kind,
            "published": a.published.isoformat() if a.published else None,
            "image": a.image}


def _art_from_dict(r: dict) -> Article:
    return Article(id=r["id"], source=r["source"], url=r.get("url", ""),
                   title=r["title"], body=r.get("body", ""),
                   topic=r.get("topic"),
                   source_kind=r.get("source_kind", "news"),
                   published=(datetime.fromisoformat(r["published"])
                              if r.get("published") else None),
                   image=r.get("image", ""))


def export_pair_annotation(articles: list[Article], out_csv: str,
                           snapshot_json: str, per_bucket: int = 20,
                           seed: int = 7) -> int:
    arts = dedupe_articles(articles)
    n = len(arts)
    vec = TfidfVectorizer(stop_words="english", max_features=5000)
    tfidf_sim = cosine_similarity(vec.fit_transform([_doc(a) for a in arts]))

    def cross_outlet(i: int, j: int) -> bool:
        return arts[i].source != arts[j].source

    pairs: dict[tuple[int, int], str] = {}  # (i, j) -> sampling bucket

    def top_pairs(sim, bucket: str) -> None:
        scored = [(sim[i][j], i, j) for i in range(n) for j in range(i + 1, n)
                  if cross_outlet(i, j)]
        scored.sort(reverse=True)
        added = 0
        for _, i, j in scored:
            if (i, j) not in pairs:
                pairs[(i, j)] = bucket
                added += 1
                if added == per_bucket:
                    break

    top_pairs(tfidf_sim, "tfidf-top")
    try:
        from cura.ingest.cluster_embed import _get_model
        emb = _get_model().encode([_doc(a) for a in arts],
                                  normalize_embeddings=True,
                                  show_progress_bar=False)
        top_pairs(emb @ emb.T, "embed-top")
    except ImportError:
        pass

    rng = random.Random(seed)
    band = [(i, j) for i in range(n) for j in range(i + 1, n)
            if cross_outlet(i, j) and 0.05 <= tfidf_sim[i][j] <= 0.5
            and (i, j) not in pairs]
    for i, j in rng.sample(band, min(per_bucket, len(band))):
        pairs[(i, j)] = "random-band"

    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["pair_id", "bucket", "a_id", "a_source", "a_text",
                         "b_id", "b_source", "b_text", "same_event", "notes"])
        for k, ((i, j), bucket) in enumerate(sorted(pairs.items(),
                                                    key=lambda kv: kv[1])):
            a, b = arts[i], arts[j]
            writer.writerow([f"p{k:03d}", bucket,
                             a.id, a.source, f"{a.title} — {_lead(a)}",
                             b.id, b.source, f"{b.title} — {_lead(b)}",
                             "", ""])
    Path(snapshot_json).write_text(
        json.dumps([_art_to_dict(a) for a in arts]), encoding="utf-8")
    return len(pairs)


def load_pair_labels(csv_path: str) -> tuple[dict[tuple[str, str], bool], int]:
    labels: dict[tuple[str, str], bool] = {}
    skipped = 0
    with open(csv_path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            raw = (row.get("same_event") or "").strip().casefold()
            if raw in _TRUE:
                labels[(row["a_id"], row["b_id"])] = True
            elif raw in _FALSE:
                labels[(row["a_id"], row["b_id"])] = False
            else:
                skipped += 1
    return labels, skipped


@dataclass
class PairEvalResult:
    clusterer: str
    n_pairs: int
    skipped: int
    precision: float
    recall: float
    f1: float
    n_clusters: int
    n_multi_source: int

    def table(self) -> str:
        return (f"{self.clusterer}: pair precision {self.precision:.3f}  "
                f"recall {self.recall:.3f}  F1 {self.f1:.3f}  "
                f"(n={self.n_pairs} labelled pairs"
                + (f", {self.skipped} unlabelled skipped" if self.skipped else "")
                + f")\n{'':>{len(self.clusterer) + 2}}"
                f"{self.n_clusters} clusters, {self.n_multi_source} multi-source")


def evaluate_pairs(snapshot_json: str, labels_csv: str, clusterer,
                   name: str) -> PairEvalResult:
    arts = [_art_from_dict(r) for r in
            json.loads(Path(snapshot_json).read_text(encoding="utf-8"))]
    labels, skipped = load_pair_labels(labels_csv)
    if not labels:
        raise ValueError(f"no labelled pairs in {labels_csv} — "
                         "fill the `same_event` column first")
    clusters = clusterer(arts)
    cluster_of = {a.id: c.id for c in clusters for a in c.articles}
    tp = fp = fn = 0
    for (a_id, b_id), same in labels.items():
        together = cluster_of.get(a_id) == cluster_of.get(b_id)
        tp += same and together
        fp += (not same) and together
        fn += same and not together
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = (2 * precision * recall / (precision + recall)
          if precision + recall else 0.0)
    return PairEvalResult(
        clusterer=name, n_pairs=len(labels), skipped=skipped,
        precision=precision, recall=recall, f1=f1,
        n_clusters=len(clusters),
        n_multi_source=sum(1 for c in clusters if c.n_sources >= 2))
