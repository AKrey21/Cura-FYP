# PROVENANCE: ORIGINAL - Summarizer protocol + lightweight sentence splitter.
# Stdlib re only. See PROVENANCE.md.
"""Summarizer protocol - every summariser is swappable and evaluable in
isolation (cura/eval/summary.py benchmarks any two implementations)."""

from __future__ import annotations

import re
from typing import Protocol, runtime_checkable

from cura.contracts import Summary

_SENT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'“])")


def split_sentences(text: str) -> list[str]:
    """Lightweight sentence splitter (sentence-level output is required by the
    CURA_BRIEFING contract for TTS reliability)."""
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return []
    return [s.strip() for s in _SENT_RE.split(text) if s.strip()]


@runtime_checkable
class Summarizer(Protocol):
    name: str

    def summarize(self, text: str, max_sentences: int = 3) -> Summary:
        """Condense `text` to at most `max_sentences` sentences."""
        ...
