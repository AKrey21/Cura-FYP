# PROVENANCE: ORIGINAL - the project's NOVEL contribution: the cross-source
# disagreement metric (signed-stance-score spread + soft-vote normalised label
# entropy + contested flag). Builds on standard measures (population std-dev,
# Shannon entropy). Stdlib math only. See PROVENANCE.md.
"""Cross-source stance triangulation - the project's novel contribution.

For a story covered by >= 2 sources we quantify disagreement two ways:

1. spread - population standard deviation of the signed stance scores
             (in [-1, 1]) across sources. Max possible is 1.0 (half the
             sources at -1, half at +1), so the value reads as a fraction
             of maximal polarisation.
2. entropy - Shannon entropy of the aggregated label distribution,
             normalised by log2(3) so it lies in [0, 1]. We aggregate by
             summing each source's class probabilities (a soft vote), which
             uses calibration rather than discarding it.

A story is flagged "contested" when either metric crosses its threshold.
The thresholds are hypotheses to validate against human judgement of which
stories are contested (evaluation plan) - keep them visible and
tunable, not buried.
"""

from __future__ import annotations

import math

from cura.contracts import StanceResult, Triangulation

# Calibrated against the round-2 validation study (cura/eval/results/
# 2026-06-11-triangulation-llm-judge.md): threshold sweep over 30 stories
# labelled by a declared LLM judge, on RoBERTa stance metrics. Spread 0.50
# is the sweep optimum (kappa 0.247 vs 0.186 at the old 0.35); entropy 0.80
# carries real signal (0.85 drops kappa below zero). Provisional pending the
# human annotation pass - agreement is weak everywhere, which is itself the
# study's finding: sentiment dispersion only partly captures perceived
# framing disagreement.
SPREAD_THRESHOLD = 0.50
ENTROPY_THRESHOLD = 0.80


def label_entropy(probs_per_source: list[dict[str, float]]) -> float:
    """Normalised Shannon entropy of the soft-vote label distribution."""
    if not probs_per_source:
        return 0.0
    totals = {label: 0.0 for label in StanceResult.LABELS}
    for probs in probs_per_source:
        for label in totals:
            totals[label] += probs.get(label, 0.0)
    mass = sum(totals.values())
    if mass <= 0:
        return 0.0
    entropy = -sum((p / mass) * math.log2(p / mass)
                   for p in totals.values() if p > 0)
    return entropy / math.log2(len(totals))


def triangulate(stances_by_source: dict[str, StanceResult],
                spread_threshold: float = SPREAD_THRESHOLD,
                entropy_threshold: float = ENTROPY_THRESHOLD) -> Triangulation:
    n = len(stances_by_source)
    scores = [s.score for s in stances_by_source.values()]
    mean = sum(scores) / n if n else 0.0
    spread = math.sqrt(sum((x - mean) ** 2 for x in scores) / n) if n else 0.0
    entropy = label_entropy([s.probs for s in stances_by_source.values()])
    contested = n >= 2 and (spread >= spread_threshold or entropy >= entropy_threshold)
    return Triangulation(n_sources=n, mean_score=round(mean, 4),
                         spread=round(spread, 4), entropy=round(entropy, 4),
                         contested=contested, per_source=dict(stances_by_source))
