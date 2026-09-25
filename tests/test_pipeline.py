import json

from cura.briefing.render_text import render_text
from cura.contracts import Article, StoryCluster, Summary
from cura.orchestrator import Pipeline


class ExplodingSummarizer:
    name = "exploding"

    def summarize(self, text, max_sentences=3):
        raise RuntimeError("stretch model fell over")


def test_end_to_end_offline(sample_articles):
    briefing, report = Pipeline().run(articles=sample_articles)

    assert briefing.stories, "briefing should contain stories"
    assert briefing.est_minutes <= 5.5  # ~5-minute budget
    stage_names = [s.name for s in report.stages]
    assert stage_names == ["ingest", "dedupe", "cluster", "summarize", "stance", "assemble"]
    assert report.total_seconds > 0

    # The Fed story (4 sources, divergent framing) should surface and be contested
    fed = briefing.clusters[0]
    assert fed.triangulation is not None
    assert fed.triangulation.n_sources == 4
    assert fed.triangulation.contested


def test_ui_contract_shape(sample_articles):
    briefing, _ = Pipeline().run(articles=sample_articles)
    ui = briefing.to_ui_dict()
    json.dumps(ui)  # must be serialisable

    story = ui["stories"][0]
    for key in ("id", "section", "headline", "dek", "tldr", "sources", "confidence",
                "confidenceLabel", "timestamp", "why", "minutes"):
        assert key in story, f"Story contract missing {key}"
    assert 1 <= story["confidence"] <= 5
    assert ui["stories"][0]["feature"] is True

    # Story detail content: real body paragraphs + the articles behind them
    assert story["body"], "live stories should carry article-page paragraphs"
    assert all(isinstance(p, str) and p for p in story["body"])
    assert story["citations"], "live stories should cite their source articles"
    for c in story["citations"]:
        assert c["source"] and c["title"] and "url" in c
    # The fixture articles carry images, so stories should too
    assert story["image"].startswith("https://")

    # Coverage spread: outlet-lean distribution over >=2 news outlets
    assert sum(story["bias"].values()) == 100
    assert set(story["bias"]) == {"left", "center", "right"}

    # Verify view: per-source comparison of the most contested story
    compare = ui["compare"]
    assert compare["storyId"] in {s["id"] for s in ui["stories"]}
    assert 2 <= len(compare["sources"]) <= 3
    for col in compare["sources"]:
        assert col["name"] and col["headline"] and col["quote"]
        assert col["lean"] in {"CRITICAL", "NEUTRAL", "SUPPORTIVE"}
    assert compare["agree"] and compare["differ"]

    # Trends: mention counts across the edition's sources
    assert ui["trends"], "edition should carry live trends"
    for t in ui["trends"]:
        assert t["rank"] >= 1 and t["label"] and t["delta"] and t["section"]

    for segment in ui["briefing"]:
        assert segment["text"]  # CURA_BRIEFING: sentence-level text always present
    assert "chapter" in ui["briefing"][0]


def test_fallback_to_baseline_on_model_failure(sample_articles):
    briefing, report = Pipeline(summarizer=ExplodingSummarizer()).run(
        articles=sample_articles)
    assert briefing.stories, "fallback should still produce a briefing"
    summarize_stage = next(s for s in report.stages if s.name == "summarize")
    assert summarize_stage.fallback and "baseline" in summarize_stage.fallback
    assert all(c.summary.method == "textrank" for c in briefing.clusters)


def test_topic_filtering_applies_to_offline_articles(sample_articles):
    briefing, _ = Pipeline().run(topics=["semiconductor"], articles=sample_articles)
    assert briefing.stories, "topic with coverage should yield stories"
    # Every story must actually match the topic - offline (--input) runs
    # must filter too, not just label everything as a match.
    for story, cluster in zip(briefing.stories, briefing.clusters):
        corpus = " ".join(f"{a.title} {a.body}" for a in cluster.articles).casefold()
        assert "semiconductor" in corpus
        assert story.why.startswith("Matches your topics")
    headlines = " ".join(s.headline.casefold() for s in briefing.stories)
    assert "federal reserve" not in headlines and "heatwave" not in headlines


def test_topic_filter_matches_feed_section_tags(sample_articles):
    # A topic must also match the feed's section tag - "Technology" should
    # select the technology desks even when the word never appears in prose.
    for a in sample_articles:
        if "heat" in a.id:
            a.topic = "Zebras"  # word guaranteed absent from the text
    briefing, _ = Pipeline().run(topics=["zebras"], articles=sample_articles)
    headlines = " ".join(s.headline.casefold() for s in briefing.stories)
    assert "heatwave" in headlines
    assert "federal reserve" not in headlines


def test_render_text_smoke(sample_articles):
    briefing, _ = Pipeline().run(articles=sample_articles)
    text = render_text(briefing)
    assert "CURA" in text and "CONTESTED" in text and "Transcript" in text


def test_summary_text_drawn_from_articles(sample_articles):
    briefing, _ = Pipeline().run(articles=sample_articles)
    for cluster in briefing.clusters:
        assert isinstance(cluster.summary, Summary)
        corpus = " ".join(f"{a.title}. {a.body}" for a in cluster.articles)
        for sentence in cluster.summary.sentences:
            assert sentence in corpus  # extractive baseline: no hallucination


def test_coverage_bias_excludes_social_and_pins_to_100():
    from cura.briefing.assemble import _coverage_bias
    from cura.contracts import Article, StoryCluster

    def art(uid, source, kind="news"):
        return Article(id=uid, source=source, url=f"https://x.test/{uid}",
                       title="t", body="b", source_kind=kind)

    # three outlets, one per lean -> 33/33/33 rounds up to a 100 total
    spread = _coverage_bias(StoryCluster(id="c", articles=[
        art("a1", "Fox News"), art("a2", "The Guardian"), art("a3", "BBC"),
        art("a4", "Reddit r/news", kind="social")]))
    assert sum(spread.values()) == 100
    assert spread["left"] >= 33 and spread["right"] >= 33  # reddit not counted

    # a single outlet is not a spread
    assert _coverage_bias(StoryCluster(id="c2", articles=[art("b1", "BBC")])) is None


def _mini_cluster(uid, section):
    article = Article(id=uid, source=f"Outlet {uid}",
                      url=f"https://x.test/{uid}",
                      title=f"{section} headline {uid}",
                      body=f"{section} report {uid} first sentence. "
                           f"{section} report {uid} second sentence.")
    return StoryCluster(id=uid, articles=[article], section=section,
                        summary=Summary(text="", sentences=[
                            f"{section} summary {uid} one.",
                            f"{section} summary {uid} two."], method="textrank"))


def test_analysed_pool_tops_up_underrepresented_topics():
    # Coverage rank alone fills the analysis window with the dominant topic
    # (World outlets out-publish everyone); the pool must top up the other
    # topics so Read's sections have material.
    clusters = ([_mini_cluster(f"w{i}", "World") for i in range(6)]
                + [_mini_cluster(f"t{i}", "Technology") for i in range(2)]
                + [_mini_cluster("h0", "Health")])
    pool = Pipeline(max_stories=2, section_depth=2)._select_pool(clusters)
    sections = [c.section for c in pool]
    assert sections[:4] == ["World"] * 4      # ranked front stays untouched
    assert sections.count("Technology") == 2  # topped up to section_depth
    assert sections.count("Health") == 1      # everything the topic has
    assert sections.count("World") == 4       # dominant topic not topped further


def test_extra_stories_interleave_sections():
    from cura.briefing.assemble import BriefingAssembler
    clusters = ([_mini_cluster(f"w{i}", "World") for i in range(3)]
                + [_mini_cluster(f"t{i}", "Technology") for i in range(2)]
                + [_mini_cluster("h0", "Health")])
    briefing = BriefingAssembler(max_extra_stories=4).assemble(
        clusters, max_stories=1)
    assert len(briefing.stories) == 1
    # Round-robin across sections - best of each first - so the dominant
    # topic can't crowd the others out of the extras cap.
    assert [s.section for s in briefing.extra_stories] == [
        "World", "Technology", "Health", "World"]


def test_extra_stories_beyond_briefing_cap(sample_articles):
    # Cap the briefing at 1 story: the other analysed clusters must surface
    # as full extra stories (moreStories) instead of being dropped.
    briefing, _ = Pipeline(max_stories=1).run(articles=sample_articles)
    assert len(briefing.stories) == 1
    assert briefing.extra_stories, "analysed clusters should become extras"
    ui = briefing.to_ui_dict()
    ids = {s["id"] for s in ui["stories"]}
    for extra in ui["moreStories"]:
        assert extra["id"] not in ids          # disjoint from the briefing
        assert extra["body"] and extra["tldr"]  # full story treatment
        assert extra["feature"] is False
