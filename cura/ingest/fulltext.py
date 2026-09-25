# PROVENANCE: ORIGINAL - fetch orchestration, gain-gating and sentence cleanup.
# Third-party: trafilatura performs the article-text extraction; urllib (stdlib).
# See PROVENANCE.md.
"""Full-article text extraction - the optional stretch for ingestion.

RSS descriptions are one to three sentences, which starves every downstream
model. This stage fetches each article's actual page in parallel and extracts
the main text with trafilatura (optional extra: ``pip install -e ".[fulltext]"``).

It degrades gracefully, per the project conventions: extra not installed →
the stage is a no-op and the run report says so; an individual page that
fails, blocks us, or yields less text than the feed already gave us → that
article keeps its feed description.
"""

from __future__ import annotations

import urllib.request
from concurrent.futures import ThreadPoolExecutor

from cura.contracts import Article

_UA = "cura-fyp/0.1 (news-intelligence research project)"
# Only adopt an extraction meaningfully longer than the feed description
MIN_GAIN_CHARS = 200
# Bound downstream compute: keep the lead of very long articles
MAX_BODY_CHARS = 4000
# Pages whose main text isn't the article (comment threads, listings,
# Google News JS-redirect interstitials from the expansion stage)
_SKIP_DOMAINS = ("reddit.com", "redd.it", "youtube.com", "youtu.be",
                 "news.google.com")


def available() -> bool:
    try:
        import trafilatura  # noqa: F401
        return True
    except ImportError:
        return False


def _fetch_html(url: str, timeout: int = 12) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def _cap(text: str) -> str:
    if len(text) <= MAX_BODY_CHARS:
        return text
    cut = text[:MAX_BODY_CHARS]
    # Trim the trailing partial sentence so the corpus stays sentence-clean
    last_stop = max(cut.rfind("."), cut.rfind("!"), cut.rfind("?"))
    return cut[: last_stop + 1] if last_stop > 0 else cut


def fetch_full_text(articles: list[Article], max_workers: int = 8,
                    timeout: int = 12, fetcher=None) -> int:
    """Upgrade article bodies in place; returns how many were upgraded.

    `fetcher(url) -> html` is injectable for offline tests.
    """
    import trafilatura

    fetch = fetcher or (lambda url: _fetch_html(url, timeout=timeout))

    def upgrade(article: Article) -> int:
        url = article.url
        if not url.startswith("http") or any(d in url for d in _SKIP_DOMAINS):
            return 0
        try:
            # favor_precision: drop boilerplate (related-story headlines, nav)
            # at the cost of some recall - junk text poisons the summariser.
            text = trafilatura.extract(fetch(url), include_comments=False,
                                       include_tables=False,
                                       favor_precision=True) or ""
        except Exception:
            return 0
        text = " ".join(text.split()).strip()
        # Nav soup that survives extraction ("scores | schedule | bracket")
        # is never prose - and as one giant "sentence" it poisons summaries
        # and stalls TTS. Drop pipe-bearing sentences.
        if "|" in text:
            from cura.summarize.base import split_sentences
            text = " ".join(s for s in split_sentences(text) if "|" not in s)
        if len(text) > len(article.body) + MIN_GAIN_CHARS:
            article.body = _cap(text)
            return 1
        return 0

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        return sum(pool.map(upgrade, articles))
