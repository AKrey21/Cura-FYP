# PROVENANCE: ORIGINAL - latency harness; percentile computed by hand (standard
# linear interpolation). Stdlib only. See PROVENANCE.md.
"""System latency evaluation: per-stage and end-to-end briefing time.

Runs the pipeline N times and aggregates each stage's seconds (mean, p95,
min, max) from the orchestrator's RunReport - the same instrumentation the
run report shows, made repeatable. One untimed warm-up run happens first so
model loading (BART/RoBERTa downloads, lazy imports) is reported as a
separate cold-start number instead of polluting the steady-state stats.

Offline (--input) runs measure compute honestly and reproducibly; live runs
add network variance, which is itself worth reporting - state which mode a
number came from.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from cura.orchestrator import Pipeline


def percentile(values: list[float], q: float) -> float:
    """Linear-interpolated percentile, dependency-free."""
    ordered = sorted(values)
    if not ordered:
        return 0.0
    pos = (len(ordered) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


@dataclass
class LatencyResult:
    runs: int
    cold_seconds: float                 # first (warm-up) run, models loading
    stages: dict[str, dict]             # name -> {mean, p95, min, max}
    total: dict                         # same stats for end-to-end
    mode: str                           # "offline fixture" | "live ingestion"

    def table(self) -> str:
        lines = [f"latency over {self.runs} runs ({self.mode}; "
                 f"after 1 untimed warm-up)",
                 f"cold start (first run, incl. model loading): "
                 f"{self.cold_seconds:.3f}s",
                 "",
                 f"{'stage':<14} {'mean':>8} {'p95':>8} {'min':>8} {'max':>8}"]
        for name, s in self.stages.items():
            lines.append(f"{name:<14} {s['mean']:>8.3f} {s['p95']:>8.3f} "
                         f"{s['min']:>8.3f} {s['max']:>8.3f}")
        t = self.total
        lines.append(f"{'TOTAL':<14} {t['mean']:>8.3f} {t['p95']:>8.3f} "
                     f"{t['min']:>8.3f} {t['max']:>8.3f}")
        return "\n".join(lines)


def _stats(values: list[float]) -> dict:
    return {"mean": sum(values) / len(values),
            "p95": percentile(values, 0.95),
            "min": min(values), "max": max(values)}


def evaluate(pipeline: Pipeline, runs: int = 5,
             topics: list[str] | None = None,
             articles: list | None = None) -> LatencyResult:
    t0 = time.perf_counter()
    pipeline.run(topics=topics, articles=articles)  # warm-up: load models
    cold = time.perf_counter() - t0

    per_stage: dict[str, list[float]] = {}
    totals: list[float] = []
    for _ in range(runs):
        _, report = pipeline.run(topics=topics, articles=articles)
        for stage in report.stages:
            per_stage.setdefault(stage.name, []).append(stage.seconds)
        totals.append(report.total_seconds)

    return LatencyResult(
        runs=runs,
        cold_seconds=round(cold, 3),
        stages={name: _stats(vals) for name, vals in per_stage.items()},
        total=_stats(totals),
        mode="offline fixture" if articles is not None else "live ingestion")
