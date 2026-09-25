from cura.summarize.base import split_sentences
from cura.summarize.textrank import TextRankSummarizer

DOC = ("The central bank raised interest rates by a quarter point on Tuesday. "
       "Officials said the decision reflected persistent inflation in services. "
       "Markets had widely expected the move and reacted calmly. "
       "The bank also signalled that further increases remain possible this year. "
       "Analysts noted that housing costs continue to drive the inflation numbers. "
       "Separately, the bank published new staff who forecast slower growth. "
       "Consumer groups criticised the decision as painful for mortgage holders.")


def test_split_sentences():
    assert len(split_sentences(DOC)) == 7
    assert split_sentences("") == []


def test_textrank_is_extractive_and_bounded():
    summary = TextRankSummarizer().summarize(DOC, max_sentences=3)
    assert len(summary.sentences) == 3
    original = split_sentences(DOC)
    for sentence in summary.sentences:
        assert sentence in original  # purely extractive
    # original document order preserved
    indices = [original.index(s) for s in summary.sentences]
    assert indices == sorted(indices)


def test_textrank_short_text_passthrough():
    summary = TextRankSummarizer().summarize("One sentence only.", max_sentences=3)
    assert summary.sentences == ["One sentence only."]
