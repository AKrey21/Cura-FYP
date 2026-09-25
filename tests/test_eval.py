import csv
import json

import pytest

from cura.eval import stance as stance_eval
from cura.eval import summary as summary_eval
from cura.eval import triangulation as tri_eval
from cura.eval.summary import faithfulness
from cura.summarize.textrank import TextRankSummarizer


class PerfectClassifier:
    """Oracle that echoes the expected label - sanity-checks the metric plumbing."""
    name = "oracle"

    def __init__(self, lookup):
        self.lookup = lookup

    def classify(self, text):
        from cura.contracts import StanceResult
        label = self.lookup[text]
        return StanceResult(label=label, score=0.0, probs={}, method=self.name)


def test_stance_eval_metrics():
    data = [("a", "positive"), ("b", "negative"), ("c", "neutral"), ("d", "positive")]
    result = stance_eval.evaluate(PerfectClassifier(dict(data)), data)
    assert result.macro_f1 == 1.0 and result.accuracy == 1.0
    assert result.confusion[0][0] == 1  # one true negative classified negative
    assert "macro-F1" in result.table()


def test_stance_eval_csv_loader(tmp_path):
    csv_path = tmp_path / "stance.csv"
    csv_path.write_text("text,label\nGreat news,positive\nAwful crash,negative\n")
    data = stance_eval.load_dataset(str(csv_path))
    assert data == [("Great news", "positive"), ("Awful crash", "negative")]


def test_faithfulness_extractive_is_one():
    doc = ("The plant opened on Tuesday creating thousands of jobs. "
           "Officials praised the investment. Local residents raised traffic concerns.")
    summary = TextRankSummarizer().summarize(doc, max_sentences=2)
    assert faithfulness(summary.text, doc) == 1.0
    assert faithfulness("completely unrelated hallucinated content", doc) == 0.0


def _annotation_pack(tmp_path, sample_articles):
    clusters = tri_eval.collect_clusters(sample_articles, min_sources=2)
    csv_path = str(tmp_path / "annotate.csv")
    sidecar = str(tmp_path / "annotate.model.json")
    n = tri_eval.export_annotation_pack(clusters, csv_path, sidecar)
    return clusters, csv_path, sidecar, n


def test_triangulation_export_is_blind(tmp_path, sample_articles):
    clusters, csv_path, sidecar, n = _annotation_pack(tmp_path, sample_articles)
    assert n == len(clusters) >= 1

    with open(csv_path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == n
    for row in rows:
        # The annotator sees the coverage, never the model's verdict
        assert set(row) == {"id", "headline", "n_sources", "coverage",
                            "contested", "notes"}
        assert row["contested"] == ""
        assert "[" in row["coverage"]  # per-source "[Source] title - snippet"
        assert int(row["n_sources"]) >= 2

    model = tri_eval.load_sidecar(sidecar)
    assert {r["id"] for r in model} == {r["id"] for r in rows}
    for r in model:
        assert {"spread", "entropy", "contested", "n_sources"} <= set(r)


def test_triangulation_agreement_with_oracle_labels(tmp_path, sample_articles):
    # Fill the annotation column with the model's own flags: the scorer must
    # report perfect chance-corrected agreement (plumbing sanity check).
    clusters, csv_path, sidecar, _ = _annotation_pack(tmp_path, sample_articles)
    flags = {c.id: c.triangulation.contested for c in clusters}
    # The fixture set must exercise both classes for kappa to be defined
    assert len(set(flags.values())) == 2

    with open(csv_path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    rows[0]["contested"] = ""  # one unannotated row -> skipped, not crashed
    for row in rows[1:]:
        row["contested"] = "yes" if flags[row["id"]] else "no"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    result = tri_eval.evaluate(csv_path, sidecar)
    assert result.stats["n"] == len(rows) - 1
    assert result.skipped == 1
    assert result.stats["kappa"] == 1.0 and result.stats["accuracy"] == 1.0
    assert "Cohen's kappa" in result.table()

    sweep_table = tri_eval.sweep(csv_path, sidecar)
    assert "ranked by kappa" in sweep_table
    assert "*" in sweep_table  # the default thresholds are always shown


def test_triangulation_sweep_finds_separating_threshold(tmp_path):
    # Synthetic stories where spread 0.30 cleanly separates the classes:
    # the sweep's best operating point must score kappa 1.0.
    rows = [{"id": f"c{i}", "headline": "h", "n_sources": 2,
             "spread": 0.45 if i < 3 else 0.10, "entropy": 0.2,
             "contested": i < 3}
            for i in range(8)]
    sidecar = tmp_path / "model.json"
    sidecar.write_text(json.dumps(rows))
    csv_path = tmp_path / "annotated.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["id", "headline", "n_sources", "coverage",
                         "contested", "notes"])
        for r in rows:
            writer.writerow([r["id"], "h", 2, "x", "yes" if r["contested"] else "no", ""])

    table = tri_eval.sweep(str(csv_path), str(sidecar))
    top = table.splitlines()[2]  # best row of the ranked grid
    assert top.split()[2] == "1.000"  # kappa


def test_clustering_pair_benchmark_roundtrip(tmp_path, sample_articles):
    from cura.eval import clustering as cl_eval
    from cura.ingest.cluster import cluster_articles

    pairs_csv = str(tmp_path / "pairs.csv")
    snapshot = str(tmp_path / "pairs.snapshot.json")
    n = cl_eval.export_pair_annotation(sample_articles, pairs_csv, snapshot,
                                       per_bucket=5)
    assert n >= 5

    with open(pairs_csv, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert all(r["same_event"] == "" for r in rows)      # blind export
    assert all(r["a_source"] != r["b_source"] for r in rows)  # cross-outlet

    # Label with the fixture's known events (same id-prefix = same event)
    event = lambda aid: aid.split("-")[-1]  # noqa: E731 (a-bbc-fed -> fed)
    for r in rows:
        r["same_event"] = "yes" if event(r["a_id"]) == event(r["b_id"]) else "no"
    with open(pairs_csv, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    result = cl_eval.evaluate_pairs(snapshot, pairs_csv, cluster_articles,
                                    "tf-idf + entity gate")
    # The baseline clusters the fixture's three events perfectly
    assert result.f1 == 1.0 and result.n_pairs == len(rows)
    assert "pair precision" in result.table()


def test_tts_listening_test_export_and_scoring(tmp_path):
    from cura.eval import tts as tts_eval

    sentences = [f"Test sentence number {i} about the economy." for i in range(6)]
    rendered = []
    def fake_synth(text, path):
        rendered.append(text)
        with open(path, "wb") as fh:
            fh.write(b"RIFFfake")

    n = tts_eval.export_listening_test(sentences, str(tmp_path), synthesizer=fake_synth)
    assert n == 6 and rendered == sentences
    page = (tmp_path / "test.html").read_text(encoding="utf-8")
    assert "speechSynthesis" in page and "item_00.wav" in page
    # Blind A/B: the neural side varies across items (seeded, not constant)
    assert '"neural_side": "A"' in page and '"neural_side": "B"' in page
    assert all((tmp_path / f"item_{i:02d}.wav").exists() for i in range(6))

    # Synthetic ratings: coqui consistently better -> stats reflect it
    ratings = tmp_path / "ratings.csv"
    with open(ratings, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["rater", "item", "engine_a", "engine_b",
                         "mos_a", "mos_b", "preference"])
        for i in range(6):
            writer.writerow(["al", i, "coqui", "webspeech", 4, 2, "A"])
    result = tts_eval.evaluate([str(ratings)])
    assert result.n_items == 6 and result.n_raters == 1
    assert result.mos["coqui"]["mean"] == 4.0
    assert result.mos["webspeech"]["mean"] == 2.0
    assert result.paired_diff["mean"] == 2.0
    assert result.preference["coqui"] == 1.0
    assert "paired difference" in result.table()


def test_user_study_eval(tmp_path):
    from cura.eval import user_study as user_study_eval

    responses = tmp_path / "responses.csv"
    with open(responses, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["participant", "date", "order", "stack",
                         "U1", "U2", "U3", "T1", "T2", "T3",
                         "rank_text", "rank_audio", "rank_paper",
                         "daily_pick", "contested_agree", "O1", "O2"])
        writer.writerow(["P01", "2026-07-04", "text-audio-paper", "full",
                         4, 4, 3, 4, 5, 5, 1, 2, 3, "text", "yes",
                         "sources", "nothing"])
        writer.writerow(["P02", "2026-07-04", "audio-text-paper", "full",
                         5, 3, 4, 3, 3, 4, 2, 1, 3, "audio", "no",
                         "", "too long"])
    result = user_study_eval.evaluate(str(responses))
    assert result.n == 2
    assert result.likert["U1"]["mean"] == 4.5
    assert result.likert["T2"]["median"] == 4.0
    assert result.ranks["text"]["first_votes"] == 1
    assert result.daily_pick == {"text": 1, "audio": 1}
    assert result.contested_agree == {"yes": 1, "no": 1}
    assert result.open_answers["O1"] == [("P01", "sources")]  # blanks dropped
    assert result.notes == []
    assert "contested story shown: 1/2" in result.table()


def test_user_study_eval_keeps_nonresponse_and_ties_as_notes(tmp_path):
    from cura.eval import user_study as user_study_eval

    responses = tmp_path / "responses.csv"
    with open(responses, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["participant", "date", "order", "stack",
                         "U1", "U2", "U3", "T1", "T2", "T3",
                         "rank_text", "rank_audio", "rank_paper",
                         "daily_pick", "contested_agree", "O1", "O2"])
        # P01 skipped T2; P02 refused the forced ranking (text/audio tied 1st)
        writer.writerow(["P01", "2026-07-04", "text-audio-paper", "full",
                         4, 4, 3, 4, "", 5, 1, 2, 3, "text", "yes", "", ""])
        writer.writerow(["P02", "2026-07-04", "audio-text-paper", "full",
                         5, 3, 4, 3, 4, 4, 1, 1, 3, "audio", "no", "", ""])
    result = user_study_eval.evaluate(str(responses))
    assert result.likert["T2"]["n"] == 1 and result.likert["T2"]["mean"] == 4
    assert result.likert["U1"]["n"] == 2
    assert result.ranks["text"]["first_votes"] == 2  # tie counts for both
    assert result.ranks["audio"]["first_votes"] == 1
    assert len(result.notes) == 2
    assert any("T2 left blank" in n for n in result.notes)
    assert any("tied format ranks" in n for n in result.notes)
    assert "data notes" in result.table()


def test_user_study_eval_rejects_bad_rows(tmp_path):
    from cura.eval import user_study as user_study_eval

    responses = tmp_path / "responses.csv"
    header = ["participant", "date", "order", "stack",
              "U1", "U2", "U3", "T1", "T2", "T3",
              "rank_text", "rank_audio", "rank_paper",
              "daily_pick", "contested_agree", "O1", "O2"]
    with open(responses, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerow(["P01", "2026-07-04", "text-audio-paper", "full",
                         4, 4, 3, 4, 6, 5, 1, 2, 3, "text", "yes", "", ""])
    with pytest.raises(ValueError, match="outside 1–5"):
        user_study_eval.evaluate(str(responses))
    with open(responses, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerow(["P01", "2026-07-04", "text-audio-paper", "full",
                         4, 4, 3, 4, 4, 5, 1, 2, 5, "text", "yes", "", ""])
    with pytest.raises(ValueError, match="ranks must be 1–3"):
        user_study_eval.evaluate(str(responses))
    with open(responses, "w", newline="", encoding="utf-8") as fh:
        fh.write("participant,date\n")
    with pytest.raises(ValueError, match="no responses"):
        user_study_eval.evaluate(str(responses))


def test_percentile_interpolation():
    from cura.eval.latency import percentile
    assert percentile([], 0.95) == 0.0
    assert percentile([1.0], 0.95) == 1.0
    assert percentile([0.0, 1.0], 0.5) == 0.5


def test_latency_eval_offline(sample_articles):
    from cura.eval import latency as latency_eval
    from cura.orchestrator import Pipeline

    result = latency_eval.evaluate(Pipeline(), runs=2, articles=sample_articles)
    assert result.runs == 2 and result.mode == "offline fixture"
    assert {"ingest", "dedupe", "cluster", "summarize",
            "stance", "assemble"} <= set(result.stages)
    assert result.cold_seconds > 0
    assert result.total["max"] >= result.total["p95"] >= result.total["min"]
    assert "TOTAL" in result.table()


def test_summary_eval_end_to_end(tmp_path):
    doc = ("The central bank raised rates on Tuesday. Officials cited inflation. "
           "Markets reacted calmly to the widely expected move. "
           "Analysts noted housing costs continue to drive inflation.")
    pairs = [{"document": doc, "reference": "The central bank raised rates citing inflation."}]
    data_path = tmp_path / "pairs.json"
    data_path.write_text(json.dumps(pairs))
    result = summary_eval.evaluate(TextRankSummarizer(),
                                   summary_eval.load_dataset(str(data_path)))
    assert result.rouge1 > 0.2
    assert result.faithfulness == 1.0
    assert result.n == 1
