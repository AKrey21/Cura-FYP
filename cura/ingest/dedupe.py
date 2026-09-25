# PROVENANCE: ORIGINAL - URL-canonicalisation + normalised-title dedup (a common
# technique, implemented from scratch). Stdlib only. See PROVENANCE.md.
"""Deduplication by canonical URL and normalised title (design/HANDOFF.md #1)."""

from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit

from cura.contracts import Article

_PUNCT_RE = re.compile(r"[^\w\s]")
_WS_RE = re.compile(r"\s+")


def canonical_url(url: str) -> str:
    """Strip query strings (utm etc.), fragments, and trailing slashes."""
    if not url:
        return ""
    parts = urlsplit(url.strip().lower())
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))


def normalised_title(title: str) -> str:
    return _WS_RE.sub(" ", _PUNCT_RE.sub("", title.casefold())).strip()


def dedupe_articles(articles: list[Article]) -> list[Article]:
    """Keep the first occurrence per canonical URL and per normalised title."""
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    kept: list[Article] = []
    for a in articles:
        url_key = canonical_url(a.url)
        title_key = normalised_title(a.title)
        if (url_key and url_key in seen_urls) or (title_key and title_key in seen_titles):
            continue
        if url_key:
            seen_urls.add(url_key)
        if title_key:
            seen_titles.add(title_key)
        kept.append(a)
    return kept
