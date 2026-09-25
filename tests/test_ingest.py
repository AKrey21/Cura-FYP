from cura.ingest.cluster import cluster_articles
from cura.ingest.dedupe import canonical_url, dedupe_articles, normalised_title
from cura.ingest.reddit import parse_listing
from cura.ingest.rss import parse_rss

RSS_SAMPLE = """<?xml version="1.0"?>
<rss version="2.0"><channel><title>Test</title>
<item><title>Hello &amp; goodbye</title>
<link>https://example.com/a</link>
<description>&lt;p&gt;Body text here.&lt;/p&gt;</description>
<pubDate>Tue, 10 Jun 2026 06:00:00 GMT</pubDate></item>
</channel></rss>"""

RSS_MEDIA_SAMPLE = """<?xml version="1.0"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/"><channel>
<item><title>With thumbnail</title><link>https://example.com/t</link>
<media:thumbnail url="https://img.example.com/thumb.jpg"/></item>
<item><title>With media content</title><link>https://example.com/m</link>
<media:content url="https://img.example.com/small.jpg" medium="image" width="240"/>
<media:content url="https://img.example.com/large.jpg" medium="image" width="1024"/></item>
<item><title>With embedded img</title><link>https://example.com/e</link>
<description>&lt;img src="https://img.example.com/inline.jpg"&gt;Lead text.</description></item>
<item><title>No image at all</title><link>https://example.com/n</link>
<description>Plain text.</description></item>
</channel></rss>"""


def test_parse_rss_normalises_html_and_dates():
    articles = parse_rss("TestSource", RSS_SAMPLE)
    assert len(articles) == 1
    a = articles[0]
    assert a.title == "Hello & goodbye"
    assert a.body == "Body text here."
    assert a.source == "TestSource"
    # The pubDate is 06:00 GMT - must come through as exactly 06:00 UTC
    # regardless of the machine's local timezone (regression: mktime skew).
    from datetime import datetime, timezone
    assert a.published == datetime(2026, 6, 10, 6, 0, 0, tzinfo=timezone.utc)


def test_parse_rss_extracts_images():
    by_title = {a.title: a for a in parse_rss("TestSource", RSS_MEDIA_SAMPLE)}
    assert by_title["With thumbnail"].image == "https://img.example.com/thumb.jpg"
    # Largest media:content wins
    assert by_title["With media content"].image == "https://img.example.com/large.jpg"
    assert by_title["With embedded img"].image == "https://img.example.com/inline.jpg"
    assert by_title["No image at all"].image == ""


def test_parse_reddit_listing_extracts_preview_image():
    listing = {"data": {"children": [
        {"data": {"id": "p1", "title": "Post with preview",
                  "url": "https://example.com/p1", "created_utc": 1750000000,
                  "preview": {"images": [{"source": {
                      "url": "https://preview.redd.it/x.jpg?width=960&amp;auto=webp"}}]}}},
        {"data": {"id": "p2", "title": "Post with self thumbnail",
                  "url": "https://example.com/p2", "thumbnail": "self"}},
    ]}}
    a1, a2 = parse_listing("news", listing)
    assert a1.image == "https://preview.redd.it/x.jpg?width=960&auto=webp"  # unescaped
    assert a2.image == ""


def test_fulltext_upgrades_bodies_and_tolerates_failure():
    import pytest
    pytest.importorskip("trafilatura")
    from cura.contracts import Article
    from cura.ingest.fulltext import fetch_full_text

    para = ("The negotiators met for a third consecutive day in Vienna, "
            "where diplomats described the mood as cautious but constructive. ")
    page = ("<html><body><main><article>"
            + "".join(f"<p>{para}Paragraph {i} adds further detail about the "
                      f"talks and the positions of each delegation.</p>"
                      for i in range(6))
            + "</article></main></body></html>")

    ok = Article(id="a1", source="BBC", url="https://example.com/full",
                 title="Talks continue", body="Short feed description.")
    boom = Article(id="a2", source="CNN", url="https://example.com/blocked",
                   title="Other story", body="Feed description stays.")
    reddit = Article(id="a3", source="Reddit r/news",
                     url="https://reddit.com/r/news/x", title="Thread",
                     body="Self post.")

    def fetcher(url):
        if "blocked" in url:
            raise OSError("403")
        return page

    upgraded = fetch_full_text([ok, boom, reddit], fetcher=fetcher)
    assert upgraded == 1
    assert "Vienna" in ok.body and len(ok.body) > 500
    assert boom.body == "Feed description stays."   # failure -> keep feed text
    assert reddit.body == "Self post."              # comment pages skipped


def test_fulltext_drops_nav_soup_sentences():
    import pytest
    pytest.importorskip("trafilatura")
    from cura.contracts import Article
    from cura.ingest.fulltext import fetch_full_text

    prose = ("The committee announced its findings on Wednesday after a "
             "six-month investigation into the matter. ")
    page = ("<html><body><main><article>"
            "<p>scores | schedule | bracket | offseason guides | more "
            "coverage and endless navigation links that extraction kept</p>"
            + "".join(f"<p>{prose}Paragraph {i} expands on the findings and "
                      f"the panel's recommendations in detail.</p>"
                      for i in range(6))
            + "</article></main></body></html>")
    art = Article(id="a1", source="ESPN", url="https://example.com/nav",
                  title="Findings", body="Short feed description.")
    assert fetch_full_text([art], fetcher=lambda url: page) == 1
    assert "|" not in art.body          # nav soup never reaches summaries/TTS
    assert "committee" in art.body


def test_canonical_url_strips_tracking():
    assert (canonical_url("https://Example.com/a/?utm_source=x#frag")
            == canonical_url("https://example.com/a"))


def test_normalised_title_ignores_case_and_punctuation():
    assert normalised_title("Fed signals cut!") == normalised_title("fed signals  cut")


def test_dedupe_drops_url_and_title_duplicates(sample_articles):
    deduped = dedupe_articles(sample_articles)
    # a-cnn-chip-dupe shares both a canonical URL and a title with a-cna-chip
    ids = {a.id for a in deduped}
    assert "a-cnn-chip-dupe" not in ids
    assert len(deduped) == len(sample_articles) - 1


def test_cluster_groups_same_event(sample_articles):
    clusters = cluster_articles(dedupe_articles(sample_articles))
    # Three underlying events in the fixture: Fed rates, chip fab, heatwave
    assert len(clusters) == 3
    biggest = clusters[0]
    assert biggest.n_sources == 4  # Fed story: BBC, CNN, ST, Reddit
    titles = " ".join(a.title.lower() for a in biggest.articles)
    assert "rate" in titles or "fed" in titles


def test_cluster_separates_same_domain_different_events():
    # Regression: two unrelated baseball stories merged into one "story" on a
    # live run (a Congressional charity game led a page whose body was a Las
    # Vegas ballpark feature). Shared domain vocabulary crosses the cosine
    # threshold; the entity gate must keep events apart - they share no names.
    from cura.contracts import Article

    def art(uid, title, body):
        return Article(id=uid, source=f"Outlet {uid}",
                       url=f"https://x.test/{uid}", title=title, body=body)

    congress = [
        art("hill", "Republicans dominate Democrats to extend Congressional "
                    "baseball winning streak",
            "Republican lawmakers continued their dominance in the annual "
            "Congressional Baseball Game for Charity on Wednesday night at "
            "Nationals Park, topping the Democrats and extending the club's "
            "winning streak to six consecutive seasons of the charity game."),
        art("politico", "GOP routs Democrats in Congressional baseball game "
                        "again",
            "Republican lawmakers won the annual Congressional Baseball Game "
            "for Charity at Nationals Park on Wednesday, extending their "
            "winning streak over the Democrats to six straight seasons."),
    ]
    ballpark = art("espn", "Inside the Las Vegas ballpark rising on Tropicana "
                           "Boulevard",
                   "Baseball in this ballpark needs to call a cab. The owner's "
                   "enthusiasm is rooted twenty miles down the road, where his "
                   "two billion dollar futuristic ballpark on Tropicana "
                   "Boulevard is beginning to take shape ahead of the team's "
                   "opening season of baseball games in the new stadium.")
    clusters = cluster_articles(congress + [ballpark])
    by_id = {a.id: c.id for c in clusters for a in c.articles}
    # Same event still groups; same vocabulary alone must not
    assert by_id["hill"] == by_id["politico"]
    assert by_id["espn"] != by_id["hill"]


GNEWS_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>"fed" - Google News</title>
<item><title>Fed signals rate cut in September - Reuters</title>
  <link>https://news.google.com/rss/articles/abc1</link>
  <source url="https://www.reuters.com">Reuters</source></item>
<item><title>Fed poised to cut rates - BBC</title>
  <link>https://news.google.com/rss/articles/abc2</link>
  <source url="https://www.bbc.com">BBC</source></item>
<item><title>Powell hints at easing - facebook.com</title>
  <link>https://news.google.com/rss/articles/abc3</link>
  <source url="https://www.facebook.com">facebook.com</source></item>
<item><title>Markets rally on Fed signal - MarketWatch</title>
  <link>https://news.google.com/rss/articles/abc4</link>
  <source url="https://www.marketwatch.com">MarketWatch</source></item>
<item><title>Rate cut bets firm up - Bloomberg</title>
  <link>https://news.google.com/rss/articles/abc5</link>
  <source url="https://www.bloomberg.com">Bloomberg</source></item>
</channel></rss>"""


def test_expand_coverage_adopts_new_outlets_only():
    from cura.contracts import Article, StoryCluster
    from cura.ingest.expand import expand_coverage

    seed = Article(id="a1", source="BBC", url="https://bbc.test/fed",
                   title="Fed signals rate cut", body="b")
    single = StoryCluster(id="c1", articles=[seed], section="Economy")
    well_sourced = StoryCluster(id="c2", section="Economy", articles=[
        Article(id=f"w{i}", source=f"Outlet {i}", url=f"https://x.test/{i}",
                title="Well covered story", body="b") for i in range(3)])

    queried = []
    def fetcher(url):
        queried.append(url)
        return GNEWS_SAMPLE.encode()

    extra = expand_coverage([single, well_sourced], fetcher=fetcher,
                            per_query=2)
    # Only the under-sourced cluster gets a query
    assert len(queried) == 1 and "news.google.com" in queried[0]
    # BBC already covers the story; facebook.com is not an outlet
    assert [a.source for a in extra] == ["Reuters", "MarketWatch"]  # capped at 2
    reuters = extra[0]
    assert reuters.title == "Fed signals rate cut in September"  # suffix stripped
    assert reuters.topic is None        # no vote on the cluster's section
    assert reuters.source_kind == "news"


def test_expand_coverage_failed_query_returns_nothing():
    from cura.contracts import Article, StoryCluster
    from cura.ingest.expand import expand_coverage

    cluster = StoryCluster(id="c1", articles=[
        Article(id="a1", source="BBC", url="https://bbc.test/x",
                title="t", body="b")])
    def fetcher(url):
        raise OSError("network down")
    assert expand_coverage([cluster], fetcher=fetcher) == []


def test_embed_clusterer_matches_baseline_contract(sample_articles):
    import pytest

    from cura.ingest import cluster_embed
    if not cluster_embed.available():
        pytest.skip('embeddings extra not installed (pip install -e ".[embeddings]")')
    clusters = cluster_embed.embed_cluster_articles(
        dedupe_articles(sample_articles))
    # Same three fixture events as the TF-IDF baseline, same contract
    assert len(clusters) == 3
    assert clusters[0].n_sources == 4  # Fed story: BBC, CNN, ST, Reddit
    assert all(c.section for c in clusters)


def test_pipeline_falls_back_when_clusterer_explodes(sample_articles):
    from cura.orchestrator import Pipeline

    def exploding(articles):
        raise RuntimeError("embedding model fell over")

    briefing, report = Pipeline(clusterer=exploding).run(articles=sample_articles)
    assert briefing.stories, "fallback should still produce a briefing"
    cluster_stage = next(s for s in report.stages if s.name == "cluster")
    assert cluster_stage.fallback == "tf-idf baseline"


def test_store_accumulates_and_prunes(tmp_path):
    from datetime import datetime, timedelta, timezone

    from cura.contracts import Article
    from cura.ingest.store import merge_and_save

    def art(uid, title="t"):
        return Article(id=uid, source="BBC", url=f"https://x.test/{uid}",
                       title=title, body="b",
                       published=datetime(2026, 6, 10, tzinfo=timezone.utc))

    path = tmp_path / "store.json"
    t0 = datetime(2026, 6, 11, 9, 0, tzinfo=timezone.utc)

    # Run 1: two articles enter the pool
    pool = merge_and_save([art("a1"), art("a2")], path=path, now=t0)
    assert {a.id for a in pool} == {"a1", "a2"}

    # Run 2, twelve hours on: a1 rolled out of its feed but stays pooled;
    # a2 re-sighted with an amended title (fresh copy wins)
    pool = merge_and_save([art("a2", title="amended"), art("a3")],
                          path=path, now=t0 + timedelta(hours=12))
    assert {a.id for a in pool} == {"a1", "a2", "a3"}
    assert next(a for a in pool if a.id == "a2").title == "amended"
    # Round-trip preserves typed fields
    assert all(a.published.tzinfo is not None for a in pool)

    # Run 3, past the 72h horizon for run-1 entries: a1 ages out; a2's
    # re-sighting must NOT have reset its clock, so it ages out too
    pool = merge_and_save([art("a4")], path=path,
                          now=t0 + timedelta(hours=73))
    assert {a.id for a in pool} == {"a3", "a4"}


def test_store_failure_degrades_to_fresh_batch(tmp_path):
    from cura.contracts import Article
    from cura.ingest.store import merge_and_save

    fresh = [Article(id="a1", source="BBC", url="https://x.test/a1",
                     title="t", body="b")]
    corrupt = tmp_path / "store.json"
    corrupt.write_text("{not json", encoding="utf-8")
    pool = merge_and_save(fresh, path=corrupt)
    assert [a.id for a in pool] == ["a1"]  # corrupt store starts over


def test_cluster_section_is_majority_topic(sample_articles):
    # Feed-tagged topics drive the section; untagged articles don't vote
    for a in sample_articles:
        if "fed" in a.title.lower() or "rate" in a.title.lower():
            a.topic = "Economy"
    clusters = cluster_articles(dedupe_articles(sample_articles))
    by_section = {c.section for c in clusters}
    assert "Economy" in by_section          # the tagged Fed cluster
    assert "Top Stories" in by_section      # untagged clusters keep default
