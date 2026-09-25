# PROVENANCE: ORIGINAL - Google News coverage-expansion stage (an original
# ingestion idea). Third-party: feedparser; urllib (stdlib). See PROVENANCE.md.
"""Coverage expansion - ask Google News who else covered a story.

Our 72 feeds only show what those outlets happen to push; a story one outlet
broke can't be triangulated. For under-sourced clusters this stage queries
Google News' public search RSS (no key, no quota dance) with the story's
headline and recency window, and returns the other outlets' versions as new
articles - which then re-dedupe and re-cluster, converting single-source
stories into triangulatable multi-source ones. It also surfaces outlets with
no public RSS of their own (Reuters, AP, regional papers).

Notes on the feed's shape: each item's <source> tag carries the real outlet;
titles end with " - Outlet" (stripped so dedupe can match items we already
ingested); links are news.google.com redirects (they resolve in a browser,
but full-text extraction skips them); descriptions carry no prose, so these
articles are title-only - fine for stance (headlines carry framing) and for
the source count, while the body prose keeps coming from our own feeds.
"""

from __future__ import annotations

import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import feedparser

from cura.contracts import Article, StoryCluster
from cura.ingest.rss import _clean, _entry_to_article

_UA = "cura-fyp/0.1 (news-intelligence research project)"
MAX_QUERIES = 12      # under-sourced clusters queried per run
MAX_PER_QUERY = 5     # extra outlets adopted per story
MIN_SOURCES = 3       # clusters below this get an expansion query
RECENCY = "when:2d"

# <source> values that aren't news outlets: platforms, syndication mirrors
# (one outlet's wire copy under another's masthead would double-count the
# stance vote), and primary-source sites.
_SKIP_SOURCES = ("facebook", "youtube", "reddit", "twitter", "x.com",
                 "instagram", "tiktok", "msn", "yahoo", ".gov")


def _search_url(query: str) -> str:
    q = urllib.parse.quote(f"{query} {RECENCY}")
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def _fetch(url: str, timeout: int = 15) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _expand_one(cluster: StoryCluster, fetcher, per_query: int) -> list[Article]:
    seed = cluster.articles[0]
    try:
        parsed = feedparser.parse(fetcher(_search_url(seed.title)))
    except Exception:
        return []  # a failed query must not sink the briefing
    known = {a.source.casefold() for a in cluster.articles}
    found: list[Article] = []
    for entry in parsed.entries:
        outlet = _clean(dict(getattr(entry, "source", {}) or {}).get("title") or "")
        if (not outlet or outlet.casefold() in known
                or any(s in outlet.casefold() for s in _SKIP_SOURCES)):
            continue
        # topic=None: expansion articles support an existing story; they
        # shouldn't vote on the cluster's section.
        article = _entry_to_article(outlet, entry, topic=None)
        if article.title.endswith(f" - {outlet}"):
            article.title = article.title[: -len(f" - {outlet}")].rstrip()
        if not article.title:
            continue
        known.add(outlet.casefold())
        found.append(article)
        if len(found) == per_query:
            break
    return found


def expand_coverage(clusters: list[StoryCluster], fetcher=None,
                    max_queries: int = MAX_QUERIES,
                    per_query: int = MAX_PER_QUERY,
                    min_sources: int = MIN_SOURCES) -> list[Article]:
    """Extra coverage for the under-sourced clusters, best-ranked first.

    `fetcher(url) -> bytes` is injectable for offline tests.
    """
    fetch = fetcher or _fetch
    targets = [c for c in clusters if c.n_sources < min_sources][:max_queries]
    if not targets:
        return []
    with ThreadPoolExecutor(max_workers=min(8, len(targets))) as pool:
        batches = pool.map(lambda c: _expand_one(c, fetch, per_query), targets)
    return [a for batch in batches for a in batch]
