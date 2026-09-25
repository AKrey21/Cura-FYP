# PROVENANCE: ADAPTED - sequential leader clustering (Hartigan, 1975) over
# scikit-learn TF-IDF cosine similarity. The named-entity gate that vetoes
# same-vocabulary cross-event merges is an ORIGINAL modification. Third-party:
# scikit-learn, numpy. See PROVENANCE.md.
"""Cluster articles by underlying event.

Greedy leader clustering over TF-IDF cosine similarity of title + body lead:
an article joins the cluster whose *seed* article it is most similar to
(above threshold, sharing at least one named entity), else starts a new
cluster. Deterministic and dependency-light; swappable for embedding-based
clustering later, evaluated against this baseline.

Why leader, not single-link: single-link merges transitively, and on a real
ingest (~600 articles from ~40 feeds) it chained 84% of the corpus into one
mega-"story" - A links B, B links C, so A and C end up together even when
unrelated. Requiring similarity to the seed bounds every cluster's diameter.

Why the entity gate: same-domain different-event pairs (two unrelated
baseball stories; an Indonesian court case vs Iran strikes) share enough
vocabulary to cross any workable cosine threshold - on a live 581-article
corpus (2026-06-11), wrong-event members scored up to 0.154 while genuine
cross-outlet members started at 0.159. Names separate what vocabulary can't:
distinct events almost never share proper nouns. The gate only ever splits
(an article that shares no name with the seed starts its own cluster), so it
cannot cause over-merging; when either side has no extractable names it
abstains and the threshold alone decides.
"""

from __future__ import annotations

import re
from collections import Counter

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from cura.contracts import Article, StoryCluster

# Calibrated on the labelled pair benchmark (cura/eval/results/
# 2026-06-11-clustering-pairs.md): 0.12 is the sweep optimum - pair F1 0.950
# vs 0.923 at 0.14, with precision staying 1.000 because the entity gate,
# not the threshold, is what blocks same-vocabulary cross-event merges.
# Short social posts justify the low floor (same-event Reddit pair: 0.145).
SIMILARITY_THRESHOLD = 0.12

# Capitalised tokens that aren't discriminating entities: function words and
# headline furniture, months/days, and country shorthands shared by half of
# all coverage.
_ENTITY_STOP = frozenset("""the a an in on at as and but or for to of with
after before over under from into amid says said new news live update
updates breaking watch video why how what when where who which police
government president minister officials court house senate congress white
january february march april may june july august september october november
december monday tuesday wednesday thursday friday saturday sunday
us usa uk eu un""".split())


def _doc(article: Article) -> str:
    return f"{article.title}. {article.body[:400]}"


def _entities(article: Article) -> frozenset[str]:
    """Proper-noun-ish tokens: capitalised words and acronyms from the title
    + body lead, minus headline furniture. Crude but dependency-free."""
    text = f"{article.title} {article.body[:400]}"
    tokens = re.findall(r"\b(?:[A-Z][a-z'’\-]{2,}|[A-Z]{2,})\b", text)
    return frozenset(t.casefold() for t in tokens
                     if t.casefold() not in _ENTITY_STOP)


def _section(members: list[Article]) -> str:
    """Majority topic of the cluster's articles (feeds tag their topic)."""
    topics = Counter(a.topic for a in members if a.topic)
    return topics.most_common(1)[0][0] if topics else "Top Stories"


def leader_cluster(articles: list[Article], sim: np.ndarray,
                   threshold: float) -> list[StoryCluster]:
    """Leader clustering with the entity gate over any similarity matrix -
    shared by the TF-IDF baseline and the embedding clusterer, so the two
    differ only in how `sim` is computed."""
    entities = [_entities(a) for a in articles]
    labels = np.full(len(articles), -1, dtype=int)
    seeds: list[int] = []  # index of each cluster's first (seed) article
    for i in range(len(articles)):
        joined = False
        if seeds:
            sims_to_seeds = sim[i, seeds]
            # Most-similar seed first; the entity gate may veto a match, in
            # which case the next seed above threshold gets its chance.
            for k in np.argsort(-sims_to_seeds):
                if sims_to_seeds[k] < threshold:
                    break
                seed_ents = entities[seeds[int(k)]]
                if (not entities[i] or not seed_ents
                        or not entities[i].isdisjoint(seed_ents)):
                    labels[i] = int(k)
                    joined = True
                    break
        if not joined:
            labels[i] = len(seeds)
            seeds.append(i)

    clusters = []
    for label in range(len(seeds)):
        members = [articles[k] for k in np.where(labels == label)[0]]
        clusters.append(StoryCluster(id=f"c-{label:03d}", articles=members,
                                     section=_section(members)))
    # Biggest stories (most independent sources, then most recent) first
    clusters.sort(key=lambda c: (-c.n_sources, -c.latest_published.timestamp()))
    return clusters


def cluster_articles(articles: list[Article],
                     threshold: float = SIMILARITY_THRESHOLD) -> list[StoryCluster]:
    if not articles:
        return []
    if len(articles) == 1:
        return [StoryCluster(id="c-000", articles=list(articles),
                             section=_section(articles))]

    vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
    matrix = vectorizer.fit_transform([_doc(a) for a in articles])
    return leader_cluster(articles, cosine_similarity(matrix), threshold)
