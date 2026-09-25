import math

from cura.contracts import StanceResult
from cura.stance.vader import VaderStanceClassifier
from cura.triangulate import label_entropy, triangulate


def test_vader_labels_and_contract():
    clf = VaderStanceClassifier()
    positive = clf.classify("A wonderful, hopeful triumph celebrated by everyone.")
    negative = clf.classify("A disastrous, dangerous failure that destroyed trust.")
    assert positive.label == "positive" and positive.score > 0
    assert negative.label == "negative" and negative.score < 0
    for result in (positive, negative):
        assert -1.0 <= result.score <= 1.0
        assert math.isclose(sum(result.probs.values()), 1.0, abs_tol=1e-6)
        assert set(result.probs) == set(StanceResult.LABELS)


def _stance(label, score):
    probs = {l: 0.05 for l in StanceResult.LABELS}
    probs[label] = 0.90
    return StanceResult(label=label, score=score, probs=probs, method="test")


def test_agreeing_sources_not_contested():
    tri = triangulate({"A": _stance("positive", 0.8), "B": _stance("positive", 0.7),
                       "C": _stance("positive", 0.75)})
    assert tri.n_sources == 3
    assert tri.spread < 0.1
    assert not tri.contested


def test_disagreeing_sources_contested():
    tri = triangulate({"A": _stance("positive", 0.8), "B": _stance("negative", -0.7)})
    assert tri.spread >= 0.35
    assert tri.contested


def test_single_source_never_contested():
    tri = triangulate({"A": _stance("negative", -0.9)})
    assert not tri.contested


def test_entropy_bounds():
    uniform = [{"negative": 1 / 3, "neutral": 1 / 3, "positive": 1 / 3}] * 3
    assert math.isclose(label_entropy(uniform), 1.0, abs_tol=1e-9)
    certain = [{"negative": 0.0, "neutral": 0.0, "positive": 1.0}] * 3
    assert label_entropy(certain) == 0.0
    assert label_entropy([]) == 0.0
