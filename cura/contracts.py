# PROVENANCE: ORIGINAL - data contracts (Article/StanceResult/Summary/
# Triangulation/StoryCluster/Story/Briefing) and the to_ui_dict() mappings to
# design/HANDOFF.md. Bespoke to Cura; stdlib (dataclasses) only. See PROVENANCE.md.
"""Shared datatypes for the pipeline.

The `Story` and `BriefingSegment` shapes mirror the UI data contracts in
design/HANDOFF.md ("Data Contracts"); `Story.to_ui_dict()` and
`BriefingSegment.to_ui_dict()` must stay byte-compatible with what the
prototype's app/data.jsx expects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Article:
    """One normalised piece of coverage from any source (outlet or social)."""

    id: str
    source: str            # e.g. "BBC", "Reddit r/worldnews"
    url: str
    title: str
    body: str = ""         # full text when available, else summary/description
    published: datetime | None = None
    topic: str | None = None
    source_kind: str = "news"   # "news" | "social"
    image: str = ""        # lead image URL from the feed, when provided


@dataclass
class StanceResult:
    """Stance of one article toward its story.

    `score` is a signed stance score in [-1, 1] (negative/critical ... positive/
    supportive); `probs` are class probabilities summing to 1. For the VADER
    baseline these are lexicon proportions, not calibrated probabilities - the
    transformer classifier is expected to provide calibrated ones (see
    cura/stance/base.py).
    """

    label: str                       # "negative" | "neutral" | "positive"
    score: float                     # signed, in [-1, 1]
    probs: dict[str, float] = field(default_factory=dict)
    method: str = ""

    LABELS = ("negative", "neutral", "positive")


@dataclass
class Summary:
    text: str
    sentences: list[str]
    method: str = ""


@dataclass
class Triangulation:
    """Cross-source disagreement for one story (the novel metric).

    spread - population std-dev of the signed stance scores across sources.
    entropy - Shannon entropy of the label distribution, normalised to [0, 1].
    A story is `contested` when covered by >= 2 sources and either metric
    crosses its threshold (see cura/triangulate/metrics.py).
    """

    n_sources: int
    mean_score: float
    spread: float
    entropy: float
    contested: bool
    per_source: dict[str, StanceResult] = field(default_factory=dict)


@dataclass
class StoryCluster:
    """Articles judged to cover the same underlying event."""

    id: str
    articles: list[Article]
    section: str = "Top Stories"
    summary: Summary | None = None       # tight (~3 sentences): tldr + briefing
    detail: Summary | None = None        # longer: story-page body prose
    stances: list[StanceResult] = field(default_factory=list)
    triangulation: Triangulation | None = None

    @property
    def n_sources(self) -> int:
        return len({a.source for a in self.articles})

    @property
    def latest_published(self) -> datetime:
        dates = [a.published for a in self.articles if a.published]
        return max(dates) if dates else datetime.now(timezone.utc)


def confidence_from_sources(n_sources: int) -> tuple[int, str]:
    """Map independent-source count to the UI's 1-5 confidence scale."""
    if n_sources >= 6:
        return 5, "Strongly sourced"
    if n_sources >= 4:
        return 4, "Well-sourced"
    if n_sources == 3:
        return 3, "Multiple sources"
    if n_sources == 2:
        return 2, "Two sources"
    return 1, "Single source"


@dataclass
class Story:
    """UI-facing story shape (design/HANDOFF.md 'Story' contract)."""

    id: str
    section: str
    headline: str
    dek: str
    tldr: list[str]
    sources: int
    confidence: int
    confidence_label: str
    timestamp: str
    why: str
    minutes: int
    contested: bool = False
    feature: bool = False
    body: list[str] = field(default_factory=list)        # article paragraphs
    citations: list[dict] = field(default_factory=list)  # {source, title, url}
    image: str = ""                                      # lead image URL
    bias: dict | None = None     # coverage spread {left, center, right} in %

    def to_ui_dict(self) -> dict:
        d = {
            "id": self.id,
            "section": self.section,
            "headline": self.headline,
            "dek": self.dek,
            "tldr": self.tldr,
            "sources": self.sources,
            "confidence": self.confidence,
            "confidenceLabel": self.confidence_label,
            "timestamp": self.timestamp,
            "why": self.why,
            "minutes": self.minutes,
            "contested": self.contested,
            "feature": self.feature,
        }
        if self.body:
            d["body"] = self.body
        if self.citations:
            d["citations"] = self.citations
        if self.image:
            d["image"] = self.image
        if self.bias:
            d["bias"] = self.bias
        return d


@dataclass
class BriefingSegment:
    """One spoken sentence (CURA_BRIEFING contract); sentence-level for TTS."""

    text: str
    chapter: str | None = None

    def to_ui_dict(self) -> dict:
        d: dict = {"text": self.text}
        if self.chapter:
            d["chapter"] = self.chapter
        return d


@dataclass
class Briefing:
    stories: list[Story]
    segments: list[BriefingSegment]
    clusters: list[StoryCluster]
    word_count: int
    est_minutes: float
    compare: dict | None = None        # Verify view: same story, N framings
    trends: list[dict] = field(default_factory=list)  # {rank,label,delta,section}
    extra_stories: list[Story] = field(default_factory=list)  # beyond the briefing

    def to_ui_dict(self) -> dict:
        d = {
            "stories": [s.to_ui_dict() for s in self.stories],
            "briefing": [s.to_ui_dict() for s in self.segments],
            "wordCount": self.word_count,
            "estMinutes": round(self.est_minutes, 1),
        }
        if self.compare:
            d["compare"] = self.compare
        if self.trends:
            d["trends"] = self.trends
        if self.extra_stories:
            d["moreStories"] = [s.to_ui_dict() for s in self.extra_stories]
        return d
