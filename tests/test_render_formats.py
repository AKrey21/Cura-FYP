import html
import pathlib

import pytest

from cura.briefing.render_newspaper import render_newspaper
from cura.cli import main
from cura.orchestrator import Pipeline
from cura.tts.webspeech import render_audio_player

FIXTURE = pathlib.Path(__file__).parent.parent / "examples" / "sample_articles.json"


@pytest.fixture
def briefing(sample_articles):
    result, _ = Pipeline().run(articles=sample_articles)
    return result


def test_newspaper_contains_all_stories(briefing):
    page = render_newspaper(briefing)
    assert page.startswith("<!doctype html>")
    assert "The Cura Daily" in page
    for story in briefing.stories:
        assert html.escape(story.headline) in page
    assert "contested coverage" in page          # fed story is contested
    assert "The Daily, Briefly" in page          # sidebar present


def test_newspaper_escapes_html(briefing):
    briefing.stories[0].headline = 'Markets <script>alert("x")</script> rally'
    page = render_newspaper(briefing)
    assert "<script>alert" not in page
    assert "&lt;script&gt;" in page


def test_audio_player_embeds_transcript(briefing):
    page = render_audio_player(briefing)
    assert "speechSynthesis" in page
    for seg in briefing.segments:
        assert html.escape(seg.text) in page     # visible transcript
    assert "const SEGMENTS" in page              # narration data
    assert "not supported" in page               # unsupported-browser notice


def test_cli_format_dispatch(tmp_path):
    for fmt, marker in [("newspaper", "The Cura Daily"),
                        ("audio", "speechSynthesis"),
                        ("json", '"briefing"')]:
        out = tmp_path / f"out-{fmt}"
        assert main(["run", "--input", str(FIXTURE), "--format", fmt,
                     "--out", str(out)]) == 0
        assert marker in out.read_text(encoding="utf-8")
