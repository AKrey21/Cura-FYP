# PROVENANCE: ORIGINAL - ~5-minute briefing assembly, Story/segment building,
# Verify-view payload, trend extraction and coverage-bias spread. The
# OUTLET_LEAN table is REFERENCE data from public AllSides / Ad Fontes media-bias
# ratings. Stdlib only. See PROVENANCE.md.
"""Assemble analysed story clusters into a ~5-minute briefing.

Produces both UI contracts at once: the Story feed and the sentence-level
CURA_BRIEFING transcript (design/HANDOFF.md). The word budget keeps the
narrated briefing near the 5-minute target at typical TTS speaking rate.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timezone

from cura.contracts import (Briefing, BriefingSegment, Story, StoryCluster,
                            confidence_from_sources)
from cura.summarize.base import split_sentences

WORDS_PER_MINUTE = 165          # typical TTS narration rate
TARGET_MINUTES = 5.0


def _relative_time(cluster: StoryCluster) -> str:
    delta = datetime.now(timezone.utc) - cluster.latest_published
    minutes = max(1, int(delta.total_seconds() // 60))
    if minutes < 60:
        return f"{minutes} min ago"
    hours = minutes // 60
    return f"{hours} hr ago" if hours < 24 else f"{hours // 24} d ago"


def _word_count(segments: list[BriefingSegment]) -> int:
    return sum(len(s.text.split()) for s in segments)


def _story_body(cluster: StoryCluster) -> list[str]:
    """Article-page prose for the story detail view.

    Opens with the longer extractive summary minus anything the TL;DR
    already shows, then one reporting paragraph per source drawn from that
    source's own text (skipping sentences the reader has already seen)."""
    used = set(cluster.summary.sentences)
    detail = cluster.detail or cluster.summary
    fresh = [s for s in detail.sentences if s not in used]
    used.update(fresh)
    paragraphs = [" ".join(fresh[i:i + 2]) for i in range(0, len(fresh), 2)]

    stances = cluster.triangulation.per_source if cluster.triangulation else {}
    seen_sources: set[str] = set()
    for a in cluster.articles:
        if a.source in seen_sources:
            continue
        snippet_sentences = [s for s in split_sentences(a.body)
                             if s not in used][:2]
        if not snippet_sentences:
            continue
        seen_sources.add(a.source)
        used.update(snippet_sentences)
        snippet = " ".join(snippet_sentences)
        stance = stances.get(a.source)
        framing = (f" Cura reads this framing as {stance.label}."
                   if stance and stance.label != "neutral" else "")
        paragraphs.append(f"{a.source}, under “{a.title}”: {snippet}{framing}")
        if len(seen_sources) == 5:
            break

    tri = cluster.triangulation
    if tri and tri.contested:
        paragraphs.append(
            f"Cura flags this story as contested: across {tri.n_sources} "
            f"sources, framing diverges notably — worth reading more than "
            f"one account.")
    return [p for p in paragraphs if p]


def _story_citations(cluster: StoryCluster, limit: int = 6) -> list[dict]:
    """The actual articles behind the story, for the citations footer."""
    return [{"source": a.source, "title": a.title, "url": a.url}
            for a in cluster.articles[:limit]]


def _story_image(cluster: StoryCluster) -> str:
    """Lead article's image, else the first one any source provides."""
    return next((a.image for a in cluster.articles if a.image), "")


# Outlet editorial lean, following the public AllSides / Ad Fontes media-bias
# ratings (approximate, US-centric by construction; non-rated and non-US
# outlets default to center; cite the ratings and this caveat in the report).
# Social sources are excluded from the spread - subreddits aren't outlets.
OUTLET_LEAN: dict[str, str] = {
    "The Guardian": "left", "NPR": "left", "NYT": "left", "CNN": "left",
    "Al Jazeera": "left", "Politico": "left", "Grist": "left",
    "ABC News": "left", "CBS News": "left", "NBC News": "left",
    "The Independent": "left", "Business Insider": "left", "Wired": "left",
    "Inside Climate News": "left", "Variety": "left", "Rolling Stone": "left",
    "BBC": "center", "CNA": "center", "Straits Times": "center",
    "Sky News": "center", "Deutsche Welle": "center", "SCMP": "center",
    "CNBC": "center", "The Hill": "center", "TechCrunch": "center",
    "The Verge": "center", "Ars Technica": "center", "ScienceDaily": "center",
    "New Scientist": "center", "STAT News": "center", "ESPN": "center",
    "Sky Sports": "center", "Euronews": "center", "France 24": "center",
    "ABC Australia": "center", "Times of India": "center",
    "MarketWatch": "center", "Fortune": "center", "Forbes": "center",
    "Engadget": "center", "MIT Tech Review": "center", "Nature": "center",
    "Phys.org": "center", "Live Science": "center", "Carbon Brief": "center",
    "KFF Health News": "center", "Medical Xpress": "center",
    "CBS Sports": "center",
    "Fox News": "right", "NY Post": "right", "Daily Mail": "right",
}


def _coverage_bias(cluster: StoryCluster) -> dict | None:
    """Left/center/right spread of the outlets covering this story
    (one vote per outlet), as integer percentages summing to 100."""
    outlets = {a.source for a in cluster.articles if a.source_kind == "news"}
    if len(outlets) < 2:
        return None
    counts = {"left": 0, "center": 0, "right": 0}
    for outlet in outlets:
        counts[OUTLET_LEAN.get(outlet, "center")] += 1
    total = sum(counts.values())
    bias = {k: round(100 * v / total) for k, v in counts.items()}
    # rounding drift -> pin the sum to 100 on the largest bucket
    largest = max(bias, key=bias.get)
    bias[largest] += 100 - sum(bias.values())
    return bias


_STANCE_LEAN = {  # stance label -> Verify-view chip text + colour
    "negative": ("CRITICAL", "#B8331E"),
    "neutral": ("NEUTRAL", "#6B7280"),
    "positive": ("SUPPORTIVE", "#1F5E3F"),
}


def _first_sentence(text: str, fallback: str) -> str:
    match = re.search(r".+?[.!?](?:\s|$)", text)
    return (match.group(0) if match else text or fallback).strip()


def _build_compare(cluster: StoryCluster) -> dict | None:
    """Verify-view payload: the same story, one column per source, framed by
    the stance classifier - the triangulation metric made visible."""
    tri = cluster.triangulation
    if not tri or len(tri.per_source) < 2:
        return None
    lead = cluster.articles[0]
    by_source = {a.source: a for a in reversed(cluster.articles)}
    # One source per stance label first, so the columns show the actual
    # disagreement; then fill remaining slots in coverage order.
    by_label: dict[str, list] = {}
    for name, stance in tri.per_source.items():
        by_label.setdefault(stance.label, []).append((name, stance))
    ordered = [group.pop(0) for group in by_label.values()]
    ordered += [pair for group in by_label.values() for pair in group]
    columns = []
    for source, stance in ordered[:3]:
        article = by_source.get(source)
        if article is None:
            continue
        lean, color = _STANCE_LEAN.get(stance.label, ("NEUTRAL", "#6B7280"))
        columns.append({
            "name": source,
            "lean": lean,
            "leanColor": color,
            "headline": article.title,
            "framing": (f"Cura's stance model reads this framing as "
                        f"{stance.label} (score {stance.score:+.2f})."),
            "quote": _first_sentence(article.body, article.title),
            "notes": [f"Stance: {stance.label} ({stance.score:+.2f})",
                      f"{article.source_kind} source",
                      f"1 of {tri.n_sources} sources on this story"],
        })
    if len(columns) < 2:
        return None
    confidence, conf_label = confidence_from_sources(cluster.n_sources)
    labels = {s.label for s in tri.per_source.values()}
    differ = [f"Across {tri.n_sources} sources, stance spread is "
              f"{tri.spread:.2f} and label entropy {tri.entropy:.2f}."]
    if len(labels) > 1:
        differ.append("Sources disagree on framing: "
                      + ", ".join(f"{name} reads {st.label}"
                                  for name, st in list(tri.per_source.items())[:3])
                      + ".")
    else:
        differ.append(f"All compared sources frame this story as "
                      f"{next(iter(labels))}.")
    differ.append("Contested by Cura's thresholds." if tri.contested
                  else "Not contested by Cura's thresholds.")
    return {
        "storyId": f"s-{cluster.id}",
        "headline": lead.title,
        "confidence": confidence,
        "confidenceLabel": conf_label,
        "sources": columns,
        "agree": (cluster.summary.sentences[:3] if cluster.summary else []),
        "differ": differ,
    }


_STOPWORDS = frozenset("""a an and are as at be but by for from has have in is
it its of on or s say says that the their this to was were will with after
amid over under new more than not no""".split())

# Words too generic to be a trend on their own (but fine inside a bigram,
# e.g. "World Cup")
_GENERIC_UNIGRAMS = frozenset("""world news cup who what says said year years
day days week time report reports revealed latest live update updates
breaking watch video podcast today man woman people first last best big
could would should very just like still about between during before
because""".split())


def _build_trends(clusters: list[StoryCluster], limit: int = 5) -> list[dict]:
    """Most-repeated headline terms across the edition's sources - a simple,
    transparent trend signal (mention counts, not engagement)."""
    counts: Counter[str] = Counter()
    section_for: dict[str, str] = {}
    for cluster in clusters:
        for a in cluster.articles:
            tokens = re.findall(r"[A-Za-z][A-Za-z'-]+", a.title)
            good = lambda w: w.casefold() not in _STOPWORDS and len(w) > 2  # noqa: E731
            unigrams = {w for w in tokens
                        if good(w) and w.casefold() not in _GENERIC_UNIGRAMS}
            # Bigrams from *adjacent* title words (no stopword between),
            # so removed words can't splice unrelated terms together.
            bigrams = {f"{w1} {w2}" for w1, w2 in zip(tokens, tokens[1:])
                       if good(w1) and good(w2)}
            for gram in unigrams | bigrams:
                key = gram.casefold()
                counts[key] += 1
                section_for.setdefault(key, cluster.section)
    # Prefer bigrams: drop unigrams contained in an equally-frequent bigram
    ranked = [(term, n) for term, n in counts.most_common(60) if n >= 2]
    kept: list[tuple[str, int]] = []
    for term, n in ranked:
        if " " not in term and any(term in big and m >= n
                                   for big, m in ranked if " " in big):
            continue
        kept.append((term, n))
        if len(kept) == limit:
            break
    return [{"rank": i + 1, "label": term.title(),
             "delta": f"{n}× mentions", "section": section_for[term]}
            for i, (term, n) in enumerate(kept)]


class BriefingAssembler:
    def __init__(self, target_minutes: float = TARGET_MINUTES,
                 words_per_minute: int = WORDS_PER_MINUTE,
                 max_extra_stories: int = 24):
        self.word_budget = int(target_minutes * words_per_minute)
        self.words_per_minute = words_per_minute
        self.max_extra_stories = max_extra_stories

    def _make_story(self, cluster: StoryCluster, topics: list[str] | None,
                    topic_label: str, feature: bool) -> Story:
        lead = cluster.articles[0]
        contested = bool(cluster.triangulation and cluster.triangulation.contested)
        confidence, conf_label = confidence_from_sources(cluster.n_sources)
        dek = (cluster.summary.sentences[1]
               if len(cluster.summary.sentences) > 1 else cluster.summary.sentences[0])
        body = _story_body(cluster)
        story_words = len(" ".join(body + cluster.summary.sentences).split())
        return Story(
            id=f"s-{cluster.id}",
            section=cluster.section,
            headline=lead.title,
            dek=dek,
            tldr=cluster.summary.sentences[:3],
            sources=cluster.n_sources,
            confidence=confidence,
            confidence_label=conf_label,
            timestamp=_relative_time(cluster),
            why=(f"Matches your topics: {topic_label}" if topics
                 else "Top story by source coverage"),
            minutes=max(1, round(story_words / 220)),
            contested=contested,
            feature=feature,
            body=body,
            citations=_story_citations(cluster),
            image=_story_image(cluster),
            bias=_coverage_bias(cluster),
        )

    def assemble(self, clusters: list[StoryCluster], topics: list[str] | None = None,
                 max_stories: int | None = None) -> Briefing:
        topic_label = ", ".join(topics) if topics else "today's top stories"
        segments: list[BriefingSegment] = [BriefingSegment(
            chapter="Your briefing",
            text=f"Good day — this is Cura with your briefing on {topic_label}.")]
        stories: list[Story] = []
        kept_clusters: list[StoryCluster] = []
        outro_reserve = 20  # words held back for the sign-off
        budget_spent = False

        for cluster in clusters:  # clusters arrive ranked (sources, recency)
            if not cluster.summary or not cluster.summary.sentences:
                continue
            if budget_spent or (max_stories and len(stories) >= max_stories):
                continue  # remaining analysed clusters become extra stories
            lead = cluster.articles[0]
            tri = cluster.triangulation
            contested = bool(tri and tri.contested)

            # Narrate up to 3 summary sentences, but stop once a story has
            # ~70 spoken words - full-article sentences run long, and one
            # story shouldn't crowd the rest out of the 5-minute budget.
            candidate = [BriefingSegment(chapter=lead.title,
                                         text=cluster.summary.sentences[0])]
            spoken = len(cluster.summary.sentences[0].split())
            for sentence in cluster.summary.sentences[1:3]:
                if spoken >= 70:
                    break
                candidate.append(BriefingSegment(text=sentence))
                spoken += len(sentence.split())
            if contested:
                candidate.append(BriefingSegment(
                    text=(f"Coverage of this story is contested: across "
                          f"{tri.n_sources} sources, framing diverges notably — "
                          f"worth reading more than one account.")))

            if (_word_count(segments) + _word_count(candidate)
                    > self.word_budget - outro_reserve):
                budget_spent = True
                continue

            segments.extend(candidate)
            kept_clusters.append(cluster)
            stories.append(self._make_story(cluster, topics, topic_label,
                                            feature=not stories))

        # The analysed clusters that didn't fit the spoken briefing still make
        # full stories - they fill Read's per-topic sections. Interleave by
        # section (best of each section first, then second-best, ...) so one
        # heavily-covered topic can't crowd the rest out of the cap.
        kept_ids = {c.id for c in kept_clusters}
        by_section: dict[str, list[StoryCluster]] = {}
        for cluster in clusters:
            if (cluster.id in kept_ids
                    or not cluster.summary or not cluster.summary.sentences):
                continue
            by_section.setdefault(cluster.section, []).append(cluster)
        extra_clusters: list[StoryCluster] = []
        depth = 0
        while len(extra_clusters) < self.max_extra_stories:
            row = [group[depth] for group in by_section.values()
                   if len(group) > depth]
            if not row:
                break
            extra_clusters.extend(row)
            depth += 1
        extra_stories = [
            self._make_story(cluster, topics, topic_label, feature=False)
            for cluster in extra_clusters[: self.max_extra_stories]]

        segments.append(BriefingSegment(
            chapter="That's your briefing",
            text="That's everything from Cura for now — see the full edition for "
                 "sources and coverage spreads."))
        words = _word_count(segments)
        # Verify view compares the most contested story (else the lead)
        compare_cluster = next(
            (c for c in kept_clusters if c.triangulation and c.triangulation.contested),
            kept_clusters[0] if kept_clusters else None)
        return Briefing(stories=stories, segments=segments, clusters=kept_clusters,
                        word_count=words,
                        est_minutes=words / self.words_per_minute,
                        compare=(_build_compare(compare_cluster)
                                 if compare_cluster else None),
                        trends=_build_trends(kept_clusters),
                        extra_stories=extra_stories)
