import pathlib

import pytest

from cura.cli import load_articles_json

FIXTURE = pathlib.Path(__file__).parent.parent / "examples" / "sample_articles.json"


@pytest.fixture
def sample_articles():
    return load_articles_json(str(FIXTURE))
