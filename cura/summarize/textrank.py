# PROVENANCE: ADAPTED - TextRank (Mihalcea & Tarau, 2004): PageRank power
# iteration over a TF-IDF cosine sentence graph. Algorithm published; this
# implementation is original. Third-party: scikit-learn, numpy. See PROVENANCE.md.
"""Extractive baseline: TextRank over TF-IDF sentence similarity.

PageRank by power iteration on the cosine-similarity graph of sentences
(Mihalcea & Tarau, 2004). This is the benchmark the abstractive model must
beat on ROUGE + faithfulness before it is adopted (evaluation plan).
"""

from __future__ import annotations

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from cura.contracts import Summary
from cura.summarize.base import split_sentences


class TextRankSummarizer:
    name = "textrank"

    def __init__(self, damping: float = 0.85, iterations: int = 50):
        self.damping = damping
        self.iterations = iterations

    def summarize(self, text: str, max_sentences: int = 3) -> Summary:
        sentences = split_sentences(text)
        if len(sentences) <= max_sentences:
            return Summary(text=" ".join(sentences), sentences=sentences, method=self.name)

        matrix = TfidfVectorizer(stop_words="english").fit_transform(sentences)
        sim = cosine_similarity(matrix)
        np.fill_diagonal(sim, 0.0)
        row_sums = sim.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1.0
        transition = sim / row_sums

        n = len(sentences)
        rank = np.full(n, 1.0 / n)
        for _ in range(self.iterations):
            rank = (1 - self.damping) / n + self.damping * transition.T @ rank

        top = sorted(np.argsort(rank)[::-1][:max_sentences])  # original order
        chosen = [sentences[i] for i in top]
        return Summary(text=" ".join(chosen), sentences=chosen, method=self.name)
