"""Guards on the report's reference set.

The offline source PDFs are gitignored (165 MB of third-party material), so the
content check skips when they are absent. It runs locally, where the files live,
and fails if any stored copy stops matching the citation it stands for.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / "report" / "references-ieee.md"
PDFS = ROOT / "report" / "references-pdfs"
VERIFY = ROOT / "report" / "verify_reference_pdfs.py"

if not REFS.exists():  # the published repo carries only the report PDF
    pytest.skip("report sources are not in this checkout", allow_module_level=True)


def _entries() -> dict[int, str]:
    out = {}
    for line in REFS.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*-\s*\[(\d+)\]\s*(.+?)\s*$", line)
        if m:
            out[int(m.group(1))] = m.group(2)
    return out


def test_reference_numbering_is_contiguous():
    nums = sorted(_entries())
    assert nums == list(range(1, len(nums) + 1)), "reference numbers must run 1..N with no gaps"


def test_every_citation_in_the_report_has_an_entry():
    report = (ROOT / "report" / "REPORT.md").read_text(encoding="utf-8")
    body = report.split("## References")[0]
    cited = {int(n) for n in re.findall(r"\[(\d{1,2})\]", body)}
    listed = set(_entries())
    assert cited <= listed, f"cited but not in the reference list: {sorted(cited - listed)}"


@pytest.mark.skipif(not (PDFS / "manifest.json").exists(),
                    reason="offline reference PDFs not present (gitignored; "
                           "run python report/fetch_references.py)")
def test_offline_copies_match_their_citations():
    """Each stored PDF must contain the author and title it is filed under.

    This is what catches a wrong DOI, arXiv ID or catalogue ID: an identifier
    pointing at some other work yields a file that does not carry the cited
    author and title.
    """
    r = subprocess.run([sys.executable, str(VERIFY)], capture_output=True, text=True)
    assert r.returncode == 0, f"reference PDFs failed verification:\n{r.stdout[-2000:]}"
