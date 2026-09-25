# PROVENANCE: ORIGINAL - rolling 72h article store with first-seen pruning.
# Stdlib only (json, pathlib). See PROVENANCE.md.
"""Rolling article store - lets outlets that publish hours apart still meet.

RSS feeds are sliding windows of ~20-50 items: BBC covers a story at 09:00,
CNN at 18:00, and by then BBC's item has rolled out of its feed - the two
never co-exist in a single fetch, so the story looks single-source and can't
be triangulated. The store persists every live-ingested article for
``STORE_HOURS`` and each run clusters against the accumulated pool instead
of one snapshot.

Entries are pruned ``STORE_HOURS`` after they were *first seen* (feeds often
omit or backdate ``published``); re-sightings keep the original stamp so a
stale feed can't keep a story alive forever. Offline runs (``--input``)
never touch the store - fixtures must stay deterministic.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cura.contracts import Article

STORE_HOURS = 72
DEFAULT_PATH = Path.home() / ".cura" / "article_store.json"


def _to_dict(article: Article, first_seen: str) -> dict:
    return {
        "id": article.id, "source": article.source, "url": article.url,
        "title": article.title, "body": article.body,
        "published": article.published.isoformat() if article.published else None,
        "topic": article.topic, "source_kind": article.source_kind,
        "image": article.image, "first_seen": first_seen,
    }


def _from_dict(row: dict) -> Article:
    return Article(
        id=row["id"], source=row["source"], url=row.get("url", ""),
        title=row["title"], body=row.get("body", ""),
        published=(datetime.fromisoformat(row["published"])
                   if row.get("published") else None),
        topic=row.get("topic"), source_kind=row.get("source_kind", "news"),
        image=row.get("image", ""))


def load(path: Path | str | None = None) -> list[Article]:
    """Read the store without merging or pruning - for eval sampling
    (e.g. the stance headline pack), where old entries are still valid."""
    path = Path(path) if path else DEFAULT_PATH
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [_from_dict(row) for row in rows]


def merge_and_save(fresh: list[Article], path: Path | str | None = None,
                   hours: int = STORE_HOURS,
                   now: datetime | None = None) -> list[Article]:
    """Merge this run's articles into the store, prune old entries, persist,
    and return the full pool. Storage failures degrade to the fresh batch -
    a broken store must not sink the briefing."""
    path = Path(path) if path else DEFAULT_PATH
    now = now or datetime.now(timezone.utc)
    cutoff = (now - timedelta(hours=hours)).isoformat()

    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        rows = []
    kept = {row["id"]: row for row in rows
            if row.get("first_seen", "") >= cutoff}

    stamp = now.isoformat()
    for article in fresh:
        seen = kept.get(article.id)
        # Fresh copy wins (descriptions get amended) but the first-seen
        # stamp survives, so re-sightings don't reset the clock.
        kept[article.id] = _to_dict(article, seen["first_seen"] if seen else stamp)

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(list(kept.values())), encoding="utf-8")
    except OSError:
        return fresh
    return [_from_dict(row) for row in kept.values()]
