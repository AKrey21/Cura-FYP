# PROVENANCE: ORIGINAL - package re-exports. See PROVENANCE.md.
from cura.ingest.cluster import cluster_articles
from cura.ingest.dedupe import dedupe_articles
from cura.ingest.rss import DEFAULT_FEEDS, fetch_rss
from cura.ingest.reddit import DEFAULT_SUBREDDITS, fetch_reddit

__all__ = [
    "DEFAULT_FEEDS",
    "DEFAULT_SUBREDDITS",
    "cluster_articles",
    "dedupe_articles",
    "fetch_reddit",
    "fetch_rss",
]
