# PROVENANCE: ORIGINAL - fetch script. The CNN/DailyMail dataset itself is a
# third-party benchmark (Hermann et al., 2015; See et al., 2017), pulled via the
# Hugging Face datasets-server REST API. Stdlib urllib. See PROVENANCE.md.
"""Fetch a CNN/DailyMail test-split sample for the summarisation benchmark.

Pulls rows from the Hugging Face datasets-server REST API (no extra
dependencies) and writes the eval CLI's format: a JSON list of
{"document", "reference"} pairs. Document the sample size and split in the
report; the file itself is not committed (news text is copyrighted).

    python cura/eval/datasets/fetch_cnn_dailymail.py [n] [out.json]

Defaults: n=300 (between the 200-500 the datasets README suggests),
out=cura/eval/datasets/cnn_dailymail_test_<n>.json
"""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://datasets-server.huggingface.co/rows"
DATASET = "abisee/cnn_dailymail"
CONFIG = "3.0.0"
SPLIT = "test"
PAGE = 100  # API maximum per request


def fetch(n: int) -> list[dict]:
    pairs: list[dict] = []
    for offset in range(0, n, PAGE):
        query = urllib.parse.urlencode({
            "dataset": DATASET, "config": CONFIG, "split": SPLIT,
            "offset": offset, "length": min(PAGE, n - offset),
        })
        with urllib.request.urlopen(f"{API}?{query}", timeout=30) as resp:
            rows = json.load(resp)["rows"]
        pairs.extend({"document": r["row"]["article"],
                      "reference": r["row"]["highlights"]} for r in rows)
        print(f"  fetched {len(pairs)}/{n}")
    return pairs


def main() -> int:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else (
        Path(__file__).parent / f"cnn_dailymail_test_{n}.json")
    pairs = fetch(n)
    out.write_text(json.dumps(pairs, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {out} ({len(pairs)} pairs, split={SPLIT}, config={CONFIG})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
