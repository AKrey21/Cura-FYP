# PROVENANCE: LIBRARY - wraps the vaderSentiment package (Hutto & Gilbert,
# 2014); original glue maps its output to the StanceResult contract. Standard
# +/-0.05 compound thresholds. See PROVENANCE.md.
"""Baseline stance/sentiment: VADER lexicon (Hutto & Gilbert, 2014).

Untrained lexicon method - fast, transparent, no labelled data required, which
is exactly why it is the baseline rather than the product: the proposal's
evaluation plan requires any replacement (e.g. fine-tuned RoBERTa) to beat it
on macro-F1 over a labelled benchmark.

Note: VADER's pos/neu/neg proportions are *pseudo*-probabilities (lexicon
coverage shares, not calibrated posteriors). They satisfy the StanceResult
contract for triangulation, but the report must flag this limitation.
"""

from __future__ import annotations

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from cura.contracts import StanceResult

# Standard VADER compound-score thresholds
_POS_THRESHOLD = 0.05
_NEG_THRESHOLD = -0.05


class VaderStanceClassifier:
    name = "vader"

    def __init__(self):
        self._analyzer = SentimentIntensityAnalyzer()

    def classify(self, text: str) -> StanceResult:
        scores = self._analyzer.polarity_scores(text or "")
        compound = scores["compound"]
        if compound >= _POS_THRESHOLD:
            label = "positive"
        elif compound <= _NEG_THRESHOLD:
            label = "negative"
        else:
            label = "neutral"
        total = scores["pos"] + scores["neu"] + scores["neg"] or 1.0
        probs = {"negative": scores["neg"] / total,
                 "neutral": scores["neu"] / total,
                 "positive": scores["pos"] / total}
        return StanceResult(label=label, score=compound, probs=probs, method=self.name)
