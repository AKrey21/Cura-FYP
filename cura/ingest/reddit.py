# PROVENANCE: ORIGINAL - Reddit public-JSON ingestion and normalisation.
# Third-party: urllib (stdlib); no Reddit SDK. See PROVENANCE.md.
"""Social-media ingestion via Reddit's public JSON listings (no API key)."""

from __future__ import annotations

import hashlib
import html
import json
import urllib.request
from datetime import datetime, timezone

from cura.contracts import Article

DEFAULT_SUBREDDITS = ["worldnews", "news", "technology"]
SUBREDDIT_TOPICS = {"worldnews": "World", "technology": "Technology"}
_UA = "cura-fyp/0.1 (news-intelligence research project)"


def _post_image(data: dict) -> str:
    """Preview image when the post has one (URLs arrive HTML-escaped)."""
    try:
        url = data["preview"]["images"][0]["source"]["url"]
        return html.unescape(url)
    except (KeyError, IndexError, TypeError):
        pass
    thumb = data.get("thumbnail") or ""
    return thumb if thumb.startswith("http") else ""


def _post_to_article(subreddit: str, post: dict) -> Article:
    data = post.get("data", {})
    title = (data.get("title") or "").strip()
    url = data.get("url") or f"https://reddit.com{data.get('permalink', '')}"
    created = data.get("created_utc")
    published = (datetime.fromtimestamp(created, tz=timezone.utc) if created else None)
    uid = hashlib.sha1(f"reddit|{data.get('id', title)}".encode()).hexdigest()[:12]
    return Article(id=f"a-{uid}", source=f"Reddit r/{subreddit}", url=url,
                   title=title, body=(data.get("selftext") or "").strip(),
                   published=published, topic=SUBREDDIT_TOPICS.get(subreddit),
                   source_kind="social", image=_post_image(data))


def parse_listing(subreddit: str, listing: dict) -> list[Article]:
    """Normalise an already-fetched listing dict (testable offline)."""
    posts = listing.get("data", {}).get("children", [])
    return [_post_to_article(subreddit, p) for p in posts
            if p.get("data", {}).get("title")]


def fetch_reddit(subreddits: list[str] | None = None, limit: int = 25) -> list[Article]:
    articles: list[Article] = []
    for sub in subreddits or DEFAULT_SUBREDDITS:
        try:
            req = urllib.request.Request(
                f"https://www.reddit.com/r/{sub}/hot.json?limit={limit}",
                headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=15) as resp:
                articles.extend(parse_listing(sub, json.load(resp)))
        except Exception:
            continue
    return articles
