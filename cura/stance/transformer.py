# PROVENANCE: LIBRARY - wraps the transformers text-classification pipeline with
# a public RoBERTa sentiment checkpoint (cardiffnlp); original glue is the label
# mapping + signed score. Third-party: transformers, torch. See PROVENANCE.md.
"""Stretch stance classifier: transformer (e.g. fine-tuned RoBERTa).

Optional extra - install with `pip install -e ".[stance-transformer]"`.
Softmax outputs are closer to calibrated probabilities than VADER's lexicon
shares, but the report should still verify calibration (e.g. reliability
diagram / ECE) before leaning on them for triangulation entropy.

Adopt only if macro-F1 on the labelled benchmark beats the VADER baseline
(cura/eval/stance.py), and state clearly whether the checkpoint was used
zero-shot or fine-tuned on the benchmark's training split.
"""

from __future__ import annotations

from cura.contracts import StanceResult

# Maps common checkpoint label conventions onto our canonical 3-way labels.
_LABEL_MAP = {
    "negative": "negative", "neutral": "neutral", "positive": "positive",
    "label_0": "negative", "label_1": "neutral", "label_2": "positive",
}


class TransformerStanceClassifier:
    name = "transformer"

    def __init__(self, model_name: str = "cardiffnlp/twitter-roberta-base-sentiment-latest"):
        try:
            from transformers import pipeline
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "TransformerStanceClassifier needs the optional extra: "
                'pip install -e ".[stance-transformer]"') from exc
        self.model_name = model_name
        self._pipe = pipeline("text-classification", model=model_name, top_k=None)

    def classify(self, text: str) -> StanceResult:
        results = self._pipe((text or "")[:1500])[0]
        probs = {_LABEL_MAP.get(r["label"].lower(), r["label"].lower()): r["score"]
                 for r in results}
        for canonical in StanceResult.LABELS:
            probs.setdefault(canonical, 0.0)
        label = max(probs, key=probs.get)
        score = probs["positive"] - probs["negative"]  # signed score in [-1, 1]
        return StanceResult(label=label, score=score, probs=probs,
                            method=f"{self.name}:{self.model_name}")
