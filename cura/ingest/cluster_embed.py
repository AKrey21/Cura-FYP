# PROVENANCE: ADAPTED - reuses the original leader_cluster + entity gate
# (cura/ingest/cluster.py); only the similarity matrix changes. Third-party:
# sentence-transformers (all-MiniLM-L6-v2) supplies the embeddings. See PROVENANCE.md.
"""Embedding-based event clustering - the stretch over the TF-IDF baseline.

Lexical clustering misses same-event articles that use different vocabulary
("Fed signals rate cut" vs "Powell hints at easing"); sentence embeddings
match on meaning. Same leader algorithm and entity gate as the baseline
(cura/ingest/cluster.py) - only the similarity matrix differs - so any
quality difference is attributable to the representation, per the project's
baseline-vs-stretch evaluation rule.

Optional extra: ``pip install -e ".[embeddings]"`` (sentence-transformers;
the orchestrator falls back to the TF-IDF baseline if it fails at runtime).

Benchmarked 2026-06-11 (cura/eval/results/2026-06-11-clustering-pairs.md):
statistical tie with the tuned baseline on pair F1 (0.951 vs 0.950, n=60)
at ~90 MB model + ~30-60 s CPU encode per build - so the baseline stays the
default and this remains opt-in (``--embed-cluster``).
"""

from __future__ import annotations

from cura.contracts import Article, StoryCluster
from cura.ingest.cluster import _doc, _section, leader_cluster

# Cosine over normalised all-MiniLM-L6-v2 embeddings. Measured on the
# fixture: same-event pairs score 0.586-0.942, cross-event pairs stay under
# 0.252 (the baseball regression pair: 0.165) - a far wider margin than
# TF-IDF's 0.154-vs-0.159; 0.45 sits mid-margin with room both ways.
EMBED_THRESHOLD = 0.45
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_model = None


def available() -> bool:
    try:
        import sentence_transformers  # noqa: F401
        return True
    except ImportError:
        return False


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed_cluster_articles(articles: list[Article],
                           threshold: float = EMBED_THRESHOLD) -> list[StoryCluster]:
    if not articles:
        return []
    if len(articles) == 1:
        return [StoryCluster(id="c-000", articles=list(articles),
                             section=_section(articles))]
    embeddings = _get_model().encode([_doc(a) for a in articles],
                                     normalize_embeddings=True,
                                     show_progress_bar=False)
    return leader_cluster(articles, embeddings @ embeddings.T, threshold)
