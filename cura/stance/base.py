# PROVENANCE: ORIGINAL - StanceClassifier protocol. Stdlib typing only.
# See PROVENANCE.md.
"""StanceClassifier protocol.

Every classifier returns a StanceResult with (a) a 3-way label, (b) a signed
score in [-1, 1], and (c) class probabilities summing to 1. The signed score
and probabilities feed triangulation (spread + entropy), so calibration
matters: the eval harness (cura/eval/stance.py) reports macro-F1, per-class
metrics and a confusion matrix so any candidate is compared like-for-like
against the VADER baseline.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from cura.contracts import StanceResult


@runtime_checkable
class StanceClassifier(Protocol):
    name: str

    def classify(self, text: str) -> StanceResult:
        ...
