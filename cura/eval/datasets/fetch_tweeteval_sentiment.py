# PROVENANCE: ORIGINAL - fetch script. The TweetEval / SemEval-2017 Task 4A
# dataset itself is a third-party benchmark (Rosenthal et al., 2017; Barbieri
# et al., 2020), pulled via the Hugging Face datasets-server REST API. Stdlib
# urllib. See PROVENANCE.md.
"""Fetch a TweetEval sentiment test sample for the stance benchmark.

TweetEval's sentiment task is the SemEval-2017 Task 4A benchmark (3-class
tweet sentiment) - the standard dataset VADER itself is reported on, and the
one cura/eval/datasets/README.md suggests. Rows come from the Hugging Face
datasets-server REST API (no extra dependencies) and are written as the eval
CLI's CSV format (text,label). Chunks are spread across the test split so a
label-ordered file can't skew the sample; report the class balance the eval
prints.

    python cura/eval/datasets/fetch_tweeteval_sentiment.py [n] [out.csv]

Defaults: n=1000, out=cura/eval/datasets/tweeteval_sentiment_test_<n>.csv
"""

from __future__ import annotations

import csv
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://datasets-server.huggingface.co/rows"
DATASET = "cardiffnlp/tweet_eval"
CONFIG = "sentiment"
SPLIT = "test"          # 12,284 rows
SPLIT_SIZE = 12_284
PAGE = 100              # API maximum per request
LABELS = {0: "negative", 1: "neutral", 2: "positive"}


def fetch(n: int) -> list[dict]:
    # Spread the chunks evenly across the split instead of taking the head
    chunks = max(1, n // PAGE)
    stride = max(PAGE, (SPLIT_SIZE - PAGE) // chunks)
    rows: list[dict] = []
    offset = 0
    while len(rows) < n and offset + PAGE <= SPLIT_SIZE:
        query = urllib.parse.urlencode({
            "dataset": DATASET, "config": CONFIG, "split": SPLIT,
            "offset": offset, "length": min(PAGE, n - len(rows)),
        })
        with urllib.request.urlopen(f"{API}?{query}", timeout=30) as resp:
            payload = json.load(resp)["rows"]
        rows.extend({"text": r["row"]["text"],
                     "label": LABELS[r["row"]["label"]]} for r in payload)
        offset += stride
        print(f"  fetched {len(rows)}/{n}")
    return rows


def main() -> int:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else (
        Path(__file__).parent / f"tweeteval_sentiment_test_{n}.csv")
    rows = fetch(n)
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["text", "label"])
        writer.writeheader()
        writer.writerows(rows)
    balance = {label: sum(1 for r in rows if r["label"] == label)
               for label in LABELS.values()}
    print(f"wrote {out} ({len(rows)} rows, split={SPLIT}, balance={balance})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
