import json

import pytest

from cura.orchestrator import Pipeline
from cura.server import (EditionCache, _editorial_prompt, _parse_editorial,
                         build_index_html)


def test_edition_cache_offline_and_caches(sample_articles):
    cache = EditionCache(articles=sample_articles, ttl_seconds=3600)
    first = cache.get()
    assert first["stories"] and first["briefing"]
    assert cache.get() is first  # second call within TTL hits the cache


def test_build_index_html_injects_live_data(sample_articles):
    briefing, _ = Pipeline().run(articles=sample_articles)
    edition = briefing.to_ui_dict()

    html = build_index_html(edition, cleo_live=False)
    # Live data is inlined before the CDN scripts and parses back to the edition
    payload = html.split("window.CURA_LIVE = ", 1)[1].split(";</script>", 1)[0]
    assert json.loads(payload) == edition
    assert html.index("window.CURA_LIVE") < html.index('<script src=')
    # Merge runs as babel, right after data.jsx assigns the canned globals
    data_tag = '<script type="text/babel" src="app/data.jsx"></script>'
    merge_pos = html.index("window.CURA_STORIES = window.CURA_LIVE.stories")
    assert html.index(data_tag) < merge_pos
    assert merge_pos < html.index('src="app/read.jsx"')
    # No Cleo shim without a key - the UI's demo fallback takes over
    assert "window.claude" not in html


def test_build_index_html_cleo_shim(sample_articles):
    briefing, _ = Pipeline().run(articles=sample_articles)
    html = build_index_html(briefing.to_ui_dict(), cleo_live=True)
    assert "window.claude" in html and "/api/cleo" in html


def test_build_index_html_pending_polls_until_ready():
    html = build_index_html(None, cleo_live=False)
    assert "window.CURA_PENDING = true" in html
    assert "window.CURA_LIVE = null" in html
    assert "/api/edition" in html and "cura-live-ready" in html


def test_editorial_prompt_grounds_on_edition(sample_articles):
    briefing, _ = Pipeline().run(articles=sample_articles)
    edition = briefing.to_ui_dict()
    prompt = _editorial_prompt(edition)
    for story in edition["stories"]:
        assert story["id"] in prompt and story["headline"] in prompt
    assert "ONLY a JSON object" in prompt
    # The judgment layer is requested, not just rewritten words
    for key in ("prominence", "kickers", "captions", "sectionOrder", '"lead"'):
        assert key in prompt
    assert "hasImage" in prompt
    # bodies/citations are not sent - the editorial grounds on story-level facts
    assert "citations" not in prompt
    # No reader topics -> no personalised nightcap requested
    assert "nightcap" not in prompt
    personalised = _editorial_prompt(edition, ["Technology", "Climate"])
    assert "nightcap" in personalised and "Technology, Climate" in personalised


def test_parse_editorial_tolerates_fences_and_validates():
    fenced = ('```json\n{"note": "A Gulf-dominated evening.", "lead": "s-2",'
              ' "leadWhy": "w",'
              ' "prominence": {"s-1": "major", "s-2": "brief", "s-3": "huge"},'
              ' "kickers": {"s-1": "The Gulf"},'
              ' "captions": {"s-1": "Smoke over the strait."},'
              ' "sectionOrder": ["World", "Economy", 7],'
              ' "headlines": {"s-1": "The Strait closes."},'
              ' "nightcap": "Sleep well.",'
              ' "quotes": {"s-1": "q"}}\n```')
    ed = _parse_editorial(fenced)
    assert ed["note"].startswith("A Gulf")
    assert ed["lead"] == "s-2"
    assert ed["prominence"] == {"s-1": "major", "s-2": "brief"}  # "huge" dropped
    assert ed["kickers"]["s-1"] == "The Gulf"
    assert ed["captions"]["s-1"].startswith("Smoke")
    assert ed["sectionOrder"] == ["World", "Economy"]  # non-strings dropped
    assert ed["headlines"]["s-1"] == "The Strait closes."
    assert ed["nightcap"] == "Sleep well."
    # The old minimal shape still parses (judgment fields all optional)
    minimal = _parse_editorial('{"note": "n", "headlines": {"s-1": "h"}}')
    assert minimal["lead"] == "" and minimal["prominence"] == {}
    with pytest.raises(Exception):
        _parse_editorial("Sorry, I cannot help with that.")
    with pytest.raises(ValueError):
        _parse_editorial('{"headlines": {}}')  # missing note


def test_editorial_cached_per_edition_and_reset_on_rebuild(sample_articles):
    cache = EditionCache(articles=sample_articles, ttl_seconds=3600)
    cache.get()
    assert cache.get_editorial() is None
    cache.set_editorial({"note": "n", "leadWhy": "", "headlines": {}, "quotes": {}})
    assert cache.get_editorial()["note"] == "n"
    assert cache.peek()["editorial"]["note"] == "n"   # inlined for reloads
    cache._build()                                    # new edition
    assert cache.get_editorial() is None              # must be re-unlocked
    assert "editorial" not in cache.peek()


class FakeTTS:
    name = "fake"

    def __init__(self, fail_at=None):
        self.fail_at = fail_at
        self.calls = 0

    def synthesize_text(self, text, out_path):
        self.calls += 1
        if self.fail_at is not None and self.calls == self.fail_at:
            raise RuntimeError("synthesis fell over")
        with open(out_path, "wb") as fh:
            fh.write(b"RIFFfake")


def test_edition_cache_renders_neural_narration(sample_articles):
    cache = EditionCache(articles=sample_articles, ttl_seconds=3600,
                         tts=FakeTTS())
    edition = cache.get()
    # One audio URL per briefing segment, same order, so the Listen view's
    # transcript sync and chapter seeking work unchanged
    assert len(edition["audio"]) == len(edition["briefing"])
    assert edition["audio"][0] == "/api/audio/000.wav"
    # The route resolver serves only the current edition's files
    assert cache.audio_path("000.wav") is not None
    assert cache.audio_path("999.wav") is None
    assert cache.audio_path("../secrets.txt") is None


def test_edition_cache_narration_failure_falls_back(sample_articles):
    cache = EditionCache(articles=sample_articles, ttl_seconds=3600,
                         tts=FakeTTS(fail_at=3))
    edition = cache.get()
    assert "audio" not in edition       # UI falls back to Web Speech
    assert edition["stories"]           # the edition itself still ships
    assert cache.audio_path("000.wav") is None


def test_edition_cache_on_demand_request(sample_articles):
    import time
    cache = EditionCache(articles=sample_articles, ttl_seconds=3600)
    default = cache.get()
    assert default["topics"] == [] and default["builtAt"] > 0

    cache.request(["semiconductor"])   # non-blocking background rebuild
    edition = None
    deadline = time.time() + 30
    while time.time() < deadline:
        edition = cache.peek()
        if edition and edition["topics"] == ["semiconductor"]:
            break
        time.sleep(0.05)
    assert edition["topics"] == ["semiconductor"]
    headlines = " ".join(s["headline"].casefold() for s in edition["stories"])
    assert "federal reserve" not in headlines  # filtered to the request

    cache.request(None)                # back to the daily edition
    deadline = time.time() + 30
    while time.time() < deadline:
        edition = cache.peek()
        if edition and edition["topics"] == []:
            break
        time.sleep(0.05)
    assert edition["topics"] == []


def test_build_index_html_carries_brief_api(sample_articles):
    briefing, _ = Pipeline().run(articles=sample_articles)
    html = build_index_html(briefing.to_ui_dict(), cleo_live=False)
    assert "curaRequestBriefing" in html and "/api/brief" in html
    # pending variant carries it too - Settings can re-curate from day one
    assert "curaRequestBriefing" in build_index_html(None, cleo_live=False)


def test_export_site_is_static_and_tokenless(sample_articles, tmp_path):
    from cura.export_site import export_site

    report = export_site(str(tmp_path / "site"), articles=sample_articles,
                         tts=FakeTTS())
    site = tmp_path / "site"
    html = (site / "index.html").read_text(encoding="utf-8")
    # The edition is inlined, but nothing on the page can spend tokens
    assert "window.CURA_LIVE" in html
    assert "curaRequestBriefing" not in html   # no on-demand endpoint
    assert "window.claude" not in html         # no model shim
    assert "/api/" not in html                 # no backend at all
    # Narration ships as plain static files with relative paths
    assert report["audio"] > 0
    assert '"audio/000.wav"' in html
    assert (site / "audio" / "000.wav").exists()
    # The app's modules travel with the page
    assert (site / "app" / "read.jsx").exists()
    assert (site / "components" / "tweaks-panel.jsx").exists()
    assert (site / ".nojekyll").exists()
    # No key in this environment -> no editorial baked, wire edition ships
    assert report["editorial"] is False and report["stories"] > 0


def test_edition_cache_peek_never_blocks(sample_articles):
    import time
    cache = EditionCache(articles=sample_articles, ttl_seconds=3600)
    t0 = time.perf_counter()
    first = cache.peek()           # kicks a background build
    assert time.perf_counter() - t0 < 0.05, "peek must not run the pipeline"
    assert first is None or "stories" in first
    deadline = time.time() + 30
    while cache.peek() is None and time.time() < deadline:
        time.sleep(0.05)
    assert cache.peek()["stories"]
