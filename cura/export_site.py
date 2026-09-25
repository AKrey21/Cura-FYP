# PROVENANCE: ORIGINAL - static, zero-API site export (reuses cura.server).
# Stdlib only. See PROVENANCE.md.
"""Static site export - the public, zero-token-risk deployment.

``cura export-site`` runs the pipeline once and writes a fully static
edition (GitHub Pages-ready): the design assets, an index.html with the
edition inlined, the neural narration as plain WAV files, and - optionally -
ONE pre-generated Cleo editorial baked into the payload. No server ships and
no API key reaches the page, so visitors cannot spend tokens: the UI's own
gates hide on-demand briefing (no ``curaRequestBriefing``), fall back to the
scripted demo Cleo (no ``window.claude``), and parse onboarding briefs
locally. The press gate never appears (nothing to generate against), and a
baked editorial arrives pre-unlocked with the Wire/Edited toggle intact.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from cura.server import (DESIGN_DIR, EditionCache, _cleo_complete,
                         _editorial_prompt, _have_cleo, _load_dotenv,
                         _parse_editorial, build_index_html)

# What the static site needs from design/ (prototype shells + frames stay home)
_ASSET_DIRS = ("app", "components")


def export_site(out_dir: str, pipeline=None, tts=None,
                articles=None, topics=None,
                editorial: bool = False,
                reader_topics: list[str] | None = None) -> dict:
    """Build one edition and write the static site to `out_dir`.
    Returns a small report dict for logging/tests."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    cache = EditionCache(pipeline=pipeline, topics=topics,
                         articles=articles, tts=tts)
    edition = cache.get()

    # Narration becomes plain static files
    audio_count = 0
    if edition.get("audio") and cache._audio_dir:
        audio_dir = out / "audio"
        audio_dir.mkdir(exist_ok=True)
        rewritten = []
        for url in edition["audio"]:
            name = url.rsplit("/", 1)[-1]
            shutil.copy2(Path(cache._audio_dir) / name, audio_dir / name)
            rewritten.append("audio/" + name)
        edition["audio"] = rewritten
        audio_count = len(rewritten)

    # One editorial call at EXPORT time (the publisher's cost, not the
    # public's) - baked into the payload, pre-unlocked for every visitor.
    baked_editorial = False
    if editorial:
        _load_dotenv()
        if _have_cleo():
            edition["editorial"] = _parse_editorial(_cleo_complete(
                _editorial_prompt(edition, reader_topics), max_tokens=3000))
            baked_editorial = True
        else:
            print("[cura] export-site: no ANTHROPIC_API_KEY — "
                  "exporting the wire edition without an editorial")

    for sub in _ASSET_DIRS:
        dest = out / sub
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(DESIGN_DIR / sub, dest)
    (out / "index.html").write_text(
        build_index_html(edition, cleo_live=False, static_export=True),
        encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")  # serve app/ as-is

    return {"stories": len(edition.get("stories", []))
                       + len(edition.get("moreStories", [])),
            "audio": audio_count, "editorial": baked_editorial,
            "out": str(out)}
