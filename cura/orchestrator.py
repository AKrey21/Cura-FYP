# PROVENANCE: ORIGINAL - pipeline orchestration, graceful per-stage fallback,
# latency instrumentation and topic-diverse pool selection (a core framing
# contribution). Stdlib only. See PROVENANCE.md.
"""Pipeline orchestration - the project's framing contribution.

Sequences the stages (ingest -> dedupe -> cluster -> summarise -> stance ->
triangulate -> assemble), times each one for the latency evaluation, and
degrades gracefully: if a stretch model fails at runtime the stage falls back
to its baseline and the fallback is recorded in the run report rather than
sinking the briefing.
"""

from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass, field

from cura.briefing.assemble import BriefingAssembler
from cura.contracts import Article, Briefing, StoryCluster
from cura.ingest import cluster_articles, dedupe_articles, fetch_reddit, fetch_rss
from cura.progress import ProgressReporter
from cura.stance.base import StanceClassifier
from cura.stance.vader import VaderStanceClassifier
from cura.summarize.base import Summarizer
from cura.summarize.textrank import TextRankSummarizer
from cura.triangulate import triangulate


@dataclass
class StageReport:
    name: str
    seconds: float
    items: int
    fallback: str | None = None
    error: str | None = None


@dataclass
class RunReport:
    stages: list[StageReport] = field(default_factory=list)

    @property
    def total_seconds(self) -> float:
        return sum(s.seconds for s in self.stages)

    def add(self, name: str, started: float, items: int,
            fallback: str | None = None, error: str | None = None) -> None:
        self.stages.append(StageReport(name=name, seconds=round(time.perf_counter() - started, 3),
                                       items=items, fallback=fallback, error=error))

    def table(self) -> str:
        lines = [f"{'stage':<14} {'seconds':>8} {'items':>6}  notes"]
        for s in self.stages:
            note = s.fallback and f"fallback -> {s.fallback}" or s.error or ""
            lines.append(f"{s.name:<14} {s.seconds:>8.3f} {s.items:>6}  {note}")
        lines.append(f"{'TOTAL':<14} {self.total_seconds:>8.3f}")
        return "\n".join(lines)


class Pipeline:
    """End-to-end orchestrator. Models are injected so each is swappable and
    the whole pipeline is testable offline (pass `articles=` to skip network)."""

    def __init__(self,
                 summarizer: Summarizer | None = None,
                 stance_classifier: StanceClassifier | None = None,
                 assembler: BriefingAssembler | None = None,
                 clusterer=None,
                 max_stories: int = 9,
                 section_depth: int = 3,
                 feeds: list[dict] | None = None,
                 store: bool = True):
        self.summarizer = summarizer or TextRankSummarizer()
        self.stance_classifier = stance_classifier or VaderStanceClassifier()
        self.clusterer = clusterer or cluster_articles
        # Baselines used when an injected stretch model fails at runtime
        self._fallback_summarizer = TextRankSummarizer()
        self._fallback_stance = VaderStanceClassifier()
        self.assembler = assembler or BriefingAssembler()
        self.max_stories = max_stories
        self.section_depth = section_depth
        self.feeds = feeds  # None -> rss.DEFAULT_FEEDS
        self.store = store  # rolling 72h pool (live ingestion only)

    # -- stages ------------------------------------------------------------

    def _ingest(self, report: RunReport) -> list[Article]:
        t0 = time.perf_counter()
        articles = fetch_rss(self.feeds) + fetch_reddit()
        if self.store:
            # Cluster against the rolling 72h pool, not just this snapshot -
            # outlets cover the same story hours apart and would never meet
            # inside one fetch's feed windows.
            from cura.ingest.store import merge_and_save
            articles = merge_and_save(articles)
        report.add("ingest", t0, len(articles))
        return articles

    @staticmethod
    def _filter_topics(articles: list[Article], topics: list[str] | None) -> list[Article]:
        if not topics:
            return articles
        wanted = [t.casefold() for t in topics]
        # A topic matches as free text in the article OR as the feed's own
        # section tag - "Technology" should select the technology desks even
        # when the word never appears in the prose.
        filtered = [a for a in articles
                    if any(t in f"{a.title} {a.body}".casefold()
                           or (a.topic or "").casefold() == t
                           for t in wanted)]
        return filtered or articles  # never brief on nothing

    def _summarize_cluster(self, cluster: StoryCluster, max_sentences: int = 3,
                           max_articles: int = 6) -> tuple[object, str | None]:
        # Summarise bodies where available - near-duplicate headlines reinforce
        # each other under TextRank and crowd out substantive sentences.
        bodies = []
        for a in cluster.articles[:max_articles]:
            body = a.body.strip()
            if body:
                # Feed descriptions are often truncated without terminal
                # punctuation; joining them raw fuses sentences together.
                bodies.append(body if body[-1] in ".!?…\"”'’" else body + ".")
        corpus = " ".join(bodies) if bodies else " ".join(
            f"{a.title}." for a in cluster.articles[:max_articles])
        try:
            return self.summarizer.summarize(corpus, max_sentences=max_sentences), None
        except Exception:
            return (self._fallback_summarizer.summarize(corpus, max_sentences=max_sentences),
                    self._fallback_summarizer.name)

    def _cluster(self, articles: list[Article]) -> tuple[list[StoryCluster], str | None]:
        try:
            return self.clusterer(articles), None
        except Exception:
            return cluster_articles(articles), "tf-idf baseline"

    def _select_pool(self, clusters: list[StoryCluster]) -> list[StoryCluster]:
        """Topic-diverse analysed pool.

        Pure coverage rank starves Read's sections: heavily-covered topics
        (World, mostly) fill the whole analysis window. Keep the ranked
        front as briefing candidates, then top up every other topic to
        `section_depth` clusters so each section has material."""
        front = clusters[: self.max_stories * 2]
        pool = list(front)
        per_topic = Counter(c.section for c in front)
        for cluster in clusters[self.max_stories * 2:]:
            if per_topic[cluster.section] >= self.section_depth:
                continue
            pool.append(cluster)
            per_topic[cluster.section] += 1
        return pool

    def _classify(self, text: str) -> tuple[object, str | None]:
        try:
            return self.stance_classifier.classify(text), None
        except Exception:
            return self._fallback_stance.classify(text), self._fallback_stance.name

    # -- run ---------------------------------------------------------------

    def run(self, topics: list[str] | None = None,
            articles: list[Article] | None = None,
            progress: ProgressReporter | None = None) -> tuple[Briefing, RunReport]:
        report = RunReport()
        # An empty-plan reporter is a no-op, so every stage can report
        # unconditionally - callers that don't want progress pass nothing.
        progress = progress or ProgressReporter([])

        live = articles is None
        progress.begin("ingest")
        if live:
            articles = self._ingest(report)
        else:
            report.add("ingest", time.perf_counter(), len(articles),
                       fallback="provided offline")
        progress.complete("ingest", len(articles))
        # Filter after ingest in both paths, so offline/--input runs honour
        # --topics too instead of mislabelling unrelated stories as matches.
        articles = self._filter_topics(articles, topics)

        progress.begin("dedupe")
        t0 = time.perf_counter()
        articles = dedupe_articles(articles)
        report.add("dedupe", t0, len(articles))
        progress.complete("dedupe", len(articles))

        progress.begin("cluster")
        t0 = time.perf_counter()
        clusters, cluster_fb = self._cluster(articles)
        clusters = self._select_pool(clusters)
        report.add("cluster", t0, len(clusters), fallback=cluster_fb)
        progress.complete("cluster", len(clusters))

        # Coverage expansion (live only): ask Google News who else covered
        # the under-sourced stories, then re-dedupe and re-cluster - this is
        # what turns single-source stories into triangulatable ones.
        if live:
            from cura.ingest import expand
            progress.begin("expand")
            t0 = time.perf_counter()
            extra = expand.expand_coverage(clusters)
            if extra:
                if self.store:
                    from cura.ingest.store import merge_and_save
                    merge_and_save(extra)
                articles = dedupe_articles(articles + extra)
                reclustered, _ = self._cluster(articles)
                clusters = self._select_pool(reclustered)
            report.add("expand", t0, len(extra),
                       fallback=(None if extra else "no extra coverage found"))
            progress.complete("expand", len(extra))

        # Full-article text for the clusters that can become stories - feed
        # descriptions are thin, and every later stage improves on real text.
        # Live runs only: offline fixtures must run without network.
        if live:
            from cura.ingest import fulltext
            progress.begin("fulltext")
            t0 = time.perf_counter()
            if fulltext.available():
                candidates = [a for c in clusters for a in c.articles[:8]]
                upgraded = fulltext.fetch_full_text(candidates)
                report.add("fulltext", t0, upgraded,
                           fallback=(None if upgraded
                                     else "no pages yielded more than the feed"))
            else:
                report.add("fulltext", t0, 0,
                           fallback='feed descriptions (pip install -e ".[fulltext]")')
            progress.complete("fulltext",
                              next((s.items for s in report.stages
                                    if s.name == "fulltext"), 0))

        progress.begin("summarize")
        t0 = time.perf_counter()
        summary_fallbacks = 0
        for cluster in clusters:
            cluster.summary, fb = self._summarize_cluster(cluster)
            summary_fallbacks += bool(fb)
            # Longer pass over a wider corpus for the story-page body
            cluster.detail, _ = self._summarize_cluster(
                cluster, max_sentences=8, max_articles=10)
        report.add("summarize", t0, len(clusters),
                   fallback=(f"{summary_fallbacks} via baseline" if summary_fallbacks else None))
        progress.complete("summarize", len(clusters))

        progress.begin("stance")
        t0 = time.perf_counter()
        stance_fallbacks = 0
        for cluster in clusters:
            by_source = {}
            for a in cluster.articles:
                result, fb = self._classify(f"{a.title}. {a.body[:500]}")
                stance_fallbacks += bool(fb)
                by_source.setdefault(a.source, result)  # one vote per source
            cluster.stances = list(by_source.values())
            cluster.triangulation = triangulate(by_source)
        report.add("stance", t0, sum(len(c.articles) for c in clusters),
                   fallback=(f"{stance_fallbacks} via baseline" if stance_fallbacks else None))
        progress.complete("stance", sum(len(c.articles) for c in clusters))

        progress.begin("assemble")
        t0 = time.perf_counter()
        # The full analysed pool goes in: the briefing keeps the ranked front
        # (word-budgeted), the rest become Read's per-topic extra stories.
        briefing = self.assembler.assemble(clusters, topics=topics,
                                           max_stories=self.max_stories)
        report.add("assemble", t0, len(briefing.stories))
        progress.complete("assemble", len(briefing.stories))

        return briefing, report
