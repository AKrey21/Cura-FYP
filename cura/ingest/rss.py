# PROVENANCE: ORIGINAL - feed curation (DEFAULT_FEEDS), article normalisation,
# lead-image heuristics and parallel fetch. Third-party: feedparser parses the
# RSS/Atom; urllib + ThreadPoolExecutor (stdlib). See PROVENANCE.md.
"""RSS/Atom ingestion from traditional news outlets.

Each feed spec is {"source", "topic", "url"}: `source` is the outlet (one
stance vote per outlet regardless of how many of its feeds we read), `topic`
maps to the UI's section categories. The default set is deliberately diverse
 - editorial leans from Fox News to The Guardian, wires to regionals across
four continents - because the stance-triangulation metric is only meaningful
when sources can actually disagree. All defaults verified live (no 4xx, ≥5
entries) before inclusion.
"""

from __future__ import annotations

import hashlib
import html
import re
import urllib.request
from calendar import timegm
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import feedparser

from cura.contracts import Article

_UA = "cura-fyp/0.1 (news-intelligence research project)"

DEFAULT_FEEDS: list[dict[str, str]] = [
    # World - the proposal's outlets plus diverse leans and regions
    {"source": "BBC", "topic": "World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
    {"source": "CNN", "topic": "World", "url": "http://rss.cnn.com/rss/edition_world.rss"},
    {"source": "The Guardian", "topic": "World", "url": "https://www.theguardian.com/world/rss"},
    {"source": "CNA", "topic": "World", "url": "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml"},
    {"source": "Straits Times", "topic": "World", "url": "https://www.straitstimes.com/news/world/rss.xml"},
    {"source": "Al Jazeera", "topic": "World", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
    {"source": "Fox News", "topic": "World", "url": "https://moxie.foxnews.com/google-publisher/world.xml"},
    {"source": "NPR", "topic": "World", "url": "https://feeds.npr.org/1004/rss.xml"},
    {"source": "NYT", "topic": "World", "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"},
    {"source": "Sky News", "topic": "World", "url": "https://feeds.skynews.com/feeds/rss/world.xml"},
    {"source": "Deutsche Welle", "topic": "World", "url": "https://rss.dw.com/rdf/rss-en-world"},
    {"source": "SCMP", "topic": "World", "url": "https://www.scmp.com/rss/91/feed"},
    {"source": "NY Post", "topic": "World", "url": "https://nypost.com/world-news/feed/"},
    {"source": "ABC News", "topic": "World", "url": "https://abcnews.go.com/abcnews/internationalheadlines"},
    {"source": "CBS News", "topic": "World", "url": "https://www.cbsnews.com/latest/rss/world"},
    {"source": "NBC News", "topic": "World", "url": "https://feeds.nbcnews.com/nbcnews/public/world"},
    {"source": "The Independent", "topic": "World", "url": "https://www.independent.co.uk/news/world/rss"},
    {"source": "Euronews", "topic": "World", "url": "https://www.euronews.com/rss?level=theme&name=news"},
    {"source": "France 24", "topic": "World", "url": "https://www.france24.com/en/rss"},
    {"source": "ABC Australia", "topic": "World", "url": "https://www.abc.net.au/news/feed/51120/rss.xml"},
    {"source": "Times of India", "topic": "World", "url": "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms"},
    {"source": "Daily Mail", "topic": "World", "url": "https://www.dailymail.co.uk/news/worldnews/index.rss"},
    # Politics
    {"source": "Fox News", "topic": "Politics", "url": "https://moxie.foxnews.com/google-publisher/politics.xml"},
    {"source": "NPR", "topic": "Politics", "url": "https://feeds.npr.org/1014/rss.xml"},
    {"source": "Politico", "topic": "Politics", "url": "https://rss.politico.com/politics-news.xml"},
    {"source": "The Hill", "topic": "Politics", "url": "https://thehill.com/news/feed/"},
    {"source": "ABC News", "topic": "Politics", "url": "https://abcnews.go.com/abcnews/politicsheadlines"},
    {"source": "CBS News", "topic": "Politics", "url": "https://www.cbsnews.com/latest/rss/politics"},
    # Economy
    {"source": "BBC", "topic": "Economy", "url": "https://feeds.bbci.co.uk/news/business/rss.xml"},
    {"source": "The Guardian", "topic": "Economy", "url": "https://www.theguardian.com/uk/business/rss"},
    {"source": "NYT", "topic": "Economy", "url": "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml"},
    {"source": "CNBC", "topic": "Economy", "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100727362"},
    {"source": "Straits Times", "topic": "Economy", "url": "https://www.straitstimes.com/news/business/rss.xml"},
    {"source": "MarketWatch", "topic": "Economy", "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories"},
    {"source": "Fortune", "topic": "Economy", "url": "https://fortune.com/feed/"},
    {"source": "Forbes", "topic": "Economy", "url": "https://www.forbes.com/business/feed/"},
    {"source": "Business Insider", "topic": "Economy", "url": "https://www.businessinsider.com/rss"},
    # Technology
    {"source": "BBC", "topic": "Technology", "url": "https://feeds.bbci.co.uk/news/technology/rss.xml"},
    {"source": "CNN", "topic": "Technology", "url": "http://rss.cnn.com/rss/edition_technology.rss"},
    {"source": "The Guardian", "topic": "Technology", "url": "https://www.theguardian.com/uk/technology/rss"},
    {"source": "NYT", "topic": "Technology", "url": "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml"},
    {"source": "The Verge", "topic": "Technology", "url": "https://www.theverge.com/rss/index.xml"},
    {"source": "Ars Technica", "topic": "Technology", "url": "https://feeds.arstechnica.com/arstechnica/index"},
    {"source": "TechCrunch", "topic": "Technology", "url": "https://techcrunch.com/feed/"},
    {"source": "Wired", "topic": "Technology", "url": "https://www.wired.com/feed/rss"},
    {"source": "Engadget", "topic": "Technology", "url": "https://www.engadget.com/rss.xml"},
    {"source": "MIT Tech Review", "topic": "Technology", "url": "https://www.technologyreview.com/feed/"},
    # Science
    {"source": "BBC", "topic": "Science", "url": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"},
    {"source": "ScienceDaily", "topic": "Science", "url": "https://www.sciencedaily.com/rss/all.xml"},
    {"source": "New Scientist", "topic": "Science", "url": "https://www.newscientist.com/feed/home/"},
    {"source": "Nature", "topic": "Science", "url": "https://www.nature.com/nature.rss"},
    {"source": "Phys.org", "topic": "Science", "url": "https://phys.org/rss-feed/"},
    {"source": "Live Science", "topic": "Science", "url": "https://www.livescience.com/feeds/all"},
    # Climate
    {"source": "The Guardian", "topic": "Climate", "url": "https://www.theguardian.com/environment/rss"},
    {"source": "Grist", "topic": "Climate", "url": "https://grist.org/feed/"},
    {"source": "Inside Climate News", "topic": "Climate", "url": "https://insideclimatenews.org/feed/"},
    {"source": "Carbon Brief", "topic": "Climate", "url": "https://www.carbonbrief.org/feed/"},
    # Health
    {"source": "BBC", "topic": "Health", "url": "https://feeds.bbci.co.uk/news/health/rss.xml"},
    {"source": "NYT", "topic": "Health", "url": "https://rss.nytimes.com/services/xml/rss/nyt/Health.xml"},
    {"source": "STAT News", "topic": "Health", "url": "https://www.statnews.com/feed/"},
    {"source": "KFF Health News", "topic": "Health", "url": "https://kffhealthnews.org/feed/"},
    {"source": "Medical Xpress", "topic": "Health", "url": "https://medicalxpress.com/rss-feed/"},
    # Sports
    {"source": "BBC", "topic": "Sports", "url": "https://feeds.bbci.co.uk/sport/rss.xml"},
    {"source": "ESPN", "topic": "Sports", "url": "https://www.espn.com/espn/rss/news"},
    {"source": "Sky Sports", "topic": "Sports", "url": "https://www.skysports.com/rss/12040"},
    {"source": "CBS Sports", "topic": "Sports", "url": "https://www.cbssports.com/rss/headlines/"},
    {"source": "The Guardian", "topic": "Sports", "url": "https://www.theguardian.com/uk/sport/rss"},
    # Arts
    {"source": "The Guardian", "topic": "Arts", "url": "https://www.theguardian.com/culture/rss"},
    {"source": "NYT", "topic": "Arts", "url": "https://rss.nytimes.com/services/xml/rss/nyt/Arts.xml"},
    {"source": "Variety", "topic": "Arts", "url": "https://variety.com/feed/"},
    {"source": "Rolling Stone", "topic": "Arts", "url": "https://www.rollingstone.com/feed/"},
    {"source": "BBC", "topic": "Arts", "url": "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml"},
]

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_IMG_RE = re.compile(r"<img[^>]+src=[\"']([^\"']+)[\"']", re.IGNORECASE)


def _clean(text: str) -> str:
    text = html.unescape(_TAG_RE.sub(" ", text or ""))
    # Some feeds double-escape quotes in descriptions (\" / \')
    text = text.replace('\\"', '"').replace("\\'", "'")
    return _WS_RE.sub(" ", text).strip()


def _entry_image(entry) -> str:
    """Lead image URL from the common feed conventions: media:content /
    media:thumbnail (BBC, Guardian, CNA), image enclosures, else the first
    <img> embedded in the summary HTML. Prefers the largest media:content."""
    best, best_width = "", -1
    for media in (getattr(entry, "media_content", None) or []):
        url = media.get("url")
        if not url or media.get("medium") not in (None, "image"):
            continue
        try:
            width = int(media.get("width", 0))
        except (TypeError, ValueError):
            width = 0
        if width > best_width:
            best, best_width = url, width
    if best:
        return best
    for thumb in (getattr(entry, "media_thumbnail", None) or []):
        if thumb.get("url"):
            return thumb["url"]
    for enc in (getattr(entry, "enclosures", None) or []):
        if "image" in (enc.get("type") or "") and enc.get("href"):
            return enc["href"]
    match = _IMG_RE.search(getattr(entry, "summary", "") or "")
    return html.unescape(match.group(1)) if match else ""


def _entry_to_article(source: str, entry, topic: str | None = None) -> Article:
    title = _clean(getattr(entry, "title", ""))
    url = getattr(entry, "link", "") or ""
    body = _clean(getattr(entry, "summary", "") or getattr(entry, "description", ""))
    published = None
    if getattr(entry, "published_parsed", None):
        # feedparser normalises published_parsed to UTC, so convert with
        # timegm - mktime would reinterpret it in local time and skew
        # recency sorting and "min/hr ago" labels on non-UTC machines.
        published = datetime.fromtimestamp(timegm(entry.published_parsed), tz=timezone.utc)
    uid = hashlib.sha1(f"{source}|{url or title}".encode()).hexdigest()[:12]
    return Article(id=f"a-{uid}", source=source, url=url, title=title,
                   body=body, published=published, topic=topic,
                   source_kind="news", image=_entry_image(entry))


def parse_rss(source: str, content: str | bytes,
              topic: str | None = None) -> list[Article]:
    """Parse feed content already in hand (testable offline)."""
    parsed = feedparser.parse(content)
    return [_entry_to_article(source, e, topic) for e in parsed.entries
            if getattr(e, "title", None)]


def _fetch_one(spec: dict[str, str], limit: int) -> list[Article]:
    try:
        # Fetch ourselves (explicit timeout + UA - some outlets 403 the
        # default agent), then hand the bytes to feedparser.
        req = urllib.request.Request(spec["url"], headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read()
        return parse_rss(spec["source"], content, spec.get("topic"))[:limit]
    except Exception:
        return []  # one dead feed must not sink the briefing


def fetch_rss(feeds: list[dict[str, str]] | None = None,
              limit_per_feed: int = 15, max_workers: int = 8) -> list[Article]:
    """Fetch and normalise articles from each feed spec, in parallel."""
    specs = DEFAULT_FEEDS if feeds is None else feeds
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        batches = pool.map(lambda s: _fetch_one(s, limit_per_feed), specs)
    return [article for batch in batches for article in batch]
