# PROVENANCE: ORIGINAL - build-progress reporter: a weighted-stage model that
# drives both the terminal readout and the /api/status loading bar. Stdlib
# only. See PROVENANCE.md.
"""Progress reporting for the live edition build.

One `ProgressReporter` is created per build. The orchestrator (and the
narration step in the server) call `begin(key)` / `complete(key, items)` as
each stage runs; every transition is pushed to a `sink` callback. The server
wires a sink that both (a) prints a terminal readout and (b) caches the latest
state for the `/api/status` endpoint that feeds the in-app loading bar.

Stages carry weights so the bar tracks wall-clock honestly: narration and
full-text fetch dominate a build, so an equal-slice bar would lurch. A stage
counts as half-done the moment it begins, so the bar never freezes through a
long stage (it advances on begin, then completes on done).

An empty plan makes the reporter a no-op (every key is unknown, the default
sink is None), so callers can pass `ProgressReporter([])` instead of guarding
every call site.
"""

from __future__ import annotations

import contextlib
import sys
import time


class ProgressReporter:
    """Drives a weighted progress bar over a known, ordered stage plan.

    `plan` is a list of ``(key, label, weight)``. Stages not in the plan are
    ignored and planned stages that never run simply stay pending - so the
    same reporter works for both live and offline builds."""

    def __init__(self, plan, sink=None):
        self._labels = {k: lbl for k, lbl, _ in plan}
        self._weights = {k: float(w) for k, _, w in plan}
        self._order = [k for k, _, _ in plan]
        self._total_weight = sum(self._weights.values()) or 1.0
        self._sink = sink
        self._done: set[str] = set()
        self._active: str | None = None
        self._active_started = 0.0
        self._started = time.perf_counter()

    # -- stage transitions -------------------------------------------------

    def begin(self, key: str, detail: str | None = None) -> None:
        if key not in self._labels:
            return
        self._active = key
        self._active_started = time.perf_counter()
        self._emit("begin", key, detail=detail)

    def complete(self, key: str, items: int | None = None,
                 detail: str | None = None) -> None:
        if key not in self._labels:
            return
        seconds = (round(time.perf_counter() - self._active_started, 2)
                   if self._active == key else None)
        self._done.add(key)
        self._active = None
        self._emit("complete", key, items=items, seconds=seconds, detail=detail)

    def finish(self) -> None:
        self._active = None
        self._emit("done", None)

    # -- internals ---------------------------------------------------------

    def _fraction(self, active: str | None) -> float:
        weight = sum(self._weights[k] for k in self._done)
        if active and active in self._weights:
            weight += 0.5 * self._weights[active]  # half-credit while running
        return min(1.0, weight / self._total_weight)

    def _emit(self, event: str, key: str | None, items=None, seconds=None,
              detail=None) -> None:
        if self._sink is None:
            return
        done = event == "done"
        self._sink({
            "status": "done" if done else "running",
            "event": event,
            "stage": key,
            "label": self._labels.get(key, "Finishing up"),
            "detail": detail,
            "items": items,
            "seconds": seconds,
            "index": len(self._done),
            "total": len(self._order),
            "fraction": round(1.0 if done else self._fraction(
                key if event == "begin" else None), 3),
            "elapsed": round(time.perf_counter() - self._started, 1),
        })


def build_printer(stream=None):
    """A sink that prints a self-contained terminal readout - one full line
    when a stage starts (so a long stage never looks hung) and one when it
    finishes with its item count + elapsed.

    Deliberately one line per event, not a deferred newline: under `cura serve`
    the build runs in a background thread while the HTTP server logs requests
    to the same console, and any half-written line would be fragmented. ASCII
    only, so it can't trip a cp1252 Windows console."""
    stream = stream or sys.stdout

    def emit(s):
        event = s["event"]
        if event == "begin":
            stream.write(f"  > {s['label']} ...\n")
        elif event == "complete":
            bits = []
            if s["items"] is not None:
                bits.append(str(s["items"]))
            if s["seconds"] is not None:
                bits.append(f"{s['seconds']}s")
            tail = (" - " + " / ".join(bits)) if bits else ""
            stream.write(f"  + {s['label']}{tail}\n")
        elif event == "done":
            stream.write(f"[cura] edition ready in {s['elapsed']}s\n")
        stream.flush()

    return emit


@contextlib.contextmanager
def step(label: str, stream=None):
    """Time a one-off blocking step (e.g. loading a neural model) and print
    `<label> … ready 4.1s` / `… failed 0.2s`. Used for the model-load phase,
    which blocks before the server starts - the only place a terminal can show
    that wait. First-run model downloads print their own progress bars in the
    gap between the two halves of the line."""
    stream = stream or sys.stderr
    stream.write(f"[cura] {label} ... ")
    stream.flush()
    t0 = time.perf_counter()
    ok = True
    try:
        yield
    except BaseException:
        ok = False
        raise
    finally:
        stream.write(f"{'ready' if ok else 'failed'} "
                     f"{time.perf_counter() - t0:.1f}s\n")
        stream.flush()
