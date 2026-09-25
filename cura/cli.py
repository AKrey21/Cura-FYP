# PROVENANCE: ORIGINAL - command-line interface and command wiring.
# Third-party: argparse (stdlib). See PROVENANCE.md.
"""Cura CLI.

  python -m cura run --topics technology economy        # live ingestion
  python -m cura run --input examples/sample_articles.json   # offline
  python -m cura run --input ... --format newspaper --out daily.html
  python -m cura run --input ... --format audio --out brief.html
  python -m cura eval-stance --data labelled.csv [--transformer]
  python -m cura eval-summary --data pairs.json [--abstractive]
  python -m cura export-triangulation --out annotate.csv      # blind pack
  python -m cura eval-triangulation --data annotate.csv --model annotate.model.json [--sweep]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from cura.contracts import Article
from cura.briefing.render_text import render_text
from cura.orchestrator import Pipeline
from cura.progress import step


def load_articles_json(path: str) -> list[Article]:
    with open(path, encoding="utf-8") as fh:
        rows = json.load(fh)
    articles = []
    for r in rows:
        published = (datetime.fromisoformat(r["published"]).astimezone(timezone.utc)
                     if r.get("published") else None)
        articles.append(Article(id=r["id"], source=r["source"], url=r.get("url", ""),
                                title=r["title"], body=r.get("body", ""),
                                published=published,
                                source_kind=r.get("source_kind", "news"),
                                image=r.get("image", "")))
    return articles


def load_feeds_json(path: str) -> list[dict]:
    """Custom feed list: JSON array of {source, topic, url} objects."""
    with open(path, encoding="utf-8") as fh:
        feeds = json.load(fh)
    for f in feeds:
        if not isinstance(f, dict) or "source" not in f or "url" not in f:
            raise SystemExit(
                'cura: --feeds entries must be {"source", "url"[, "topic"]} '
                f"objects, got: {f!r}")
    return feeds


def _make_summarizer(args):
    """The stretch summariser when --abstractive is passed, else None
    (Pipeline defaults to the TextRank baseline)."""
    if not getattr(args, "abstractive", False):
        return None
    try:
        with step(f"loading abstractive summariser ({args.abstractive_model})"):
            from cura.summarize.abstractive import AbstractiveSummarizer
            return AbstractiveSummarizer(args.abstractive_model)
    except ImportError as exc:
        raise SystemExit(f"cura: {exc}") from exc


def _make_stance_classifier(args):
    """The stretch stance model when --stance-transformer is passed, else
    None (Pipeline defaults to the VADER baseline). Adopted on evidence:
    macro-F1 0.712 vs 0.528 (cura/eval/results/2026-06-11-stance-*.md)."""
    if not getattr(args, "stance_transformer", False):
        return None
    try:
        with step(f"loading stance transformer ({args.stance_model})"):
            from cura.stance.transformer import TransformerStanceClassifier
            return TransformerStanceClassifier(args.stance_model)
    except ImportError as exc:
        raise SystemExit(f"cura: {exc}") from exc


def _make_clusterer(args):
    """The embedding clusterer when --embed-cluster is passed, else None
    (Pipeline defaults to the TF-IDF leader baseline)."""
    if not getattr(args, "embed_cluster", False):
        return None
    print("[cura] loading embedding clusterer (all-MiniLM-L6-v2) — "
          "first run downloads the model", file=sys.stderr)
    try:
        from cura.ingest.cluster_embed import embed_cluster_articles
        return embed_cluster_articles
    except ImportError as exc:
        raise SystemExit(f"cura: {exc}") from exc


def _cmd_run(args) -> int:
    pipeline = Pipeline(summarizer=_make_summarizer(args),
                        stance_classifier=_make_stance_classifier(args),
                        clusterer=_make_clusterer(args),
                        max_stories=args.max_stories,
                        feeds=load_feeds_json(args.feeds) if args.feeds else None,
                        store=not args.no_store)
    articles = load_articles_json(args.input) if args.input else None
    briefing, report = pipeline.run(topics=args.topics or None, articles=articles)

    fmt = "json" if args.json else args.format
    if fmt == "json":
        output = json.dumps(briefing.to_ui_dict(), indent=2)
    elif fmt == "newspaper":
        from cura.briefing.render_newspaper import render_newspaper
        output = render_newspaper(briefing)
    elif fmt == "audio":
        from cura.tts.webspeech import render_audio_player
        output = render_audio_player(briefing)
    else:
        output = render_text(briefing)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(output + "\n")
        print(f"wrote {args.out}")
    else:
        print(output)
    print("\nPer-stage latency:", file=sys.stderr)
    print(report.table(), file=sys.stderr)
    return 0


def _make_tts(args):
    """The neural narration engine when --neural-tts is passed, else None
    (Listen falls back to the Web Speech baseline in the browser).
    Provisional adoption - confirm with the MOS listening test
    (cura/eval/results/tts-protocol.md)."""
    if not getattr(args, "neural_tts", False):
        return None
    try:
        with step("loading Coqui TTS (first run downloads the voice)"):
            from cura.tts.server import CoquiTTS
            return CoquiTTS()
    except ImportError as exc:
        raise SystemExit(f"cura: {exc}") from exc


def _auto_serve_models(args):
    """`cura serve` picks the best installed stack on its own - installing
    an optional extra IS the opt-in, no flags needed. Explicit flags still
    work; --light forces the baselines (fast startup for dev). Auto choices
    follow the benchmarks: RoBERTa stance (macro-F1 0.712 vs 0.528) and
    Coqui narration (provisional, MOS pending); TextRank and TF-IDF stay
    default because BART lost faithfulness and embeddings only tied."""
    stance = _make_stance_classifier(args)
    tts = _make_tts(args)
    if not getattr(args, "light", False):
        if stance is None:
            try:
                from cura.stance.transformer import TransformerStanceClassifier
                with step("loading RoBERTa stance (auto; first run downloads ~500 MB)"):
                    stance = TransformerStanceClassifier(args.stance_model)
            except Exception:
                pass  # extra missing or model unavailable -> VADER baseline
        if tts is None:
            try:
                from cura.tts.server import CoquiTTS
                with step("loading Coqui narration (auto; first run downloads the voice)"):
                    tts = CoquiTTS()
            except Exception:
                pass  # extra missing -> Web Speech in the browser
    return stance, tts


def _cmd_serve(args) -> int:
    from cura.server import serve
    articles = load_articles_json(args.input) if args.input else None
    stance, tts = _auto_serve_models(args)
    serve(topics=args.topics or None, articles=articles, port=args.port,
          open_browser=not args.no_browser, refresh_minutes=args.refresh_minutes,
          summarizer=_make_summarizer(args),
          stance_classifier=stance,
          feeds=load_feeds_json(args.feeds) if args.feeds else None,
          store=not args.no_store, clusterer=_make_clusterer(args),
          tts=tts, present=getattr(args, "present", False))
    return 0


def _add_serve_args(p) -> None:
    """Arguments shared by the `serve` and `present` subcommands."""
    p.add_argument("--topics", nargs="*", help="topic keywords to personalise on")
    p.add_argument("--input", help="JSON file of articles (offline demo mode)")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--refresh-minutes", type=int, default=15,
                   help="re-run the pipeline this often")
    p.add_argument("--no-browser", action="store_true",
                   help="don't auto-open the browser")
    p.add_argument("--abstractive", action="store_true",
                   help="summarise with BART instead of the TextRank "
                        'baseline (needs pip install -e ".[abstractive]")')
    p.add_argument("--abstractive-model", default="facebook/bart-large-cnn")
    p.add_argument("--stance-transformer", action="store_true",
                   help="classify stance with fine-tuned RoBERTa instead "
                        "of the VADER baseline (needs pip install -e "
                        '".[stance-transformer]")')
    p.add_argument("--stance-model",
                   default="cardiffnlp/twitter-roberta-base-sentiment-latest")
    p.add_argument("--feeds",
                   help="JSON file of {source, topic, url} feed specs "
                        "(default: the built-in diverse feed set)")
    p.add_argument("--no-store", action="store_true",
                   help="don't merge live ingestion into the rolling "
                        "72h article store (~/.cura)")
    p.add_argument("--embed-cluster", action="store_true",
                   help="cluster with sentence embeddings instead of the "
                        'TF-IDF baseline (needs pip install -e ".[embeddings]")')
    p.add_argument("--neural-tts", action="store_true",
                   help="narrate Listen with server-rendered Coqui audio "
                        'instead of Web Speech (needs pip install -e ".[tts]")')
    p.add_argument("--light", action="store_true",
                   help="baselines only (VADER stance, Web Speech voice) — "
                        "fast startup; by default serve auto-uses whichever "
                        "stretch extras are installed")


def _cmd_eval_stance(args) -> int:
    from cura.eval import stance as stance_eval
    from cura.stance.vader import VaderStanceClassifier

    data = stance_eval.load_dataset(args.data)
    classifiers = [VaderStanceClassifier()]
    if args.transformer:
        from cura.stance.transformer import TransformerStanceClassifier
        classifiers.append(TransformerStanceClassifier(args.transformer_model))
    for clf in classifiers:
        print(stance_eval.evaluate(clf, data).table())
        print()
    return 0


def _cmd_export_stance_pack(args) -> int:
    from cura.eval import stance as stance_eval

    if args.input:
        articles = load_articles_json(args.input)
    else:
        from cura.ingest import store
        articles = store.load()
        if not articles:
            print("article store is empty — run a live ingestion first or "
                  "pass --input", file=sys.stderr)
            return 1
    n = stance_eval.export_headline_pack(articles, args.out, n=args.n)
    print(f"wrote {n} blind headlines -> {args.out} "
          f"(fill `label`: negative/neutral/positive; blanks are skipped)\n"
          f"score with: python -m cura eval-stance --data {args.out} --transformer")
    return 0


def _cmd_eval_summary(args) -> int:
    from cura.eval import summary as summary_eval
    from cura.summarize.textrank import TextRankSummarizer

    data = summary_eval.load_dataset(args.data)
    summarizers = [TextRankSummarizer()]
    if args.abstractive:
        from cura.summarize.abstractive import AbstractiveSummarizer
        summarizers.append(AbstractiveSummarizer(args.abstractive_model))
    for sm in summarizers:
        print(summary_eval.evaluate(sm, data).table())
        print()
    return 0


def _cmd_export_site(args) -> int:
    from cura.export_site import export_site
    stance, tts = _auto_serve_models(args)
    pipeline = Pipeline(summarizer=_make_summarizer(args),
                        stance_classifier=stance,
                        feeds=load_feeds_json(args.feeds) if args.feeds else None,
                        store=not args.no_store)
    articles = load_articles_json(args.input) if args.input else None
    report = export_site(args.out, pipeline=pipeline, tts=tts,
                         articles=articles, topics=args.topics or None,
                         editorial=args.editorial,
                         reader_topics=args.topics or None)
    print(f"static site -> {report['out']}: {report['stories']} stories, "
          f"{report['audio']} narration files, "
          f"editorial {'baked' if report['editorial'] else 'not baked'}")
    print("zero-API page: visitors cannot spend tokens (no key, no endpoints)")
    return 0


def _cmd_eval_latency(args) -> int:
    from cura.eval import latency as latency_eval

    pipeline = Pipeline(summarizer=_make_summarizer(args),
                        stance_classifier=_make_stance_classifier(args),
                        max_stories=args.max_stories)
    articles = load_articles_json(args.input) if args.input else None
    if articles is None:
        print(f"[cura] live mode: each of the {args.runs} runs ingests over "
              "the network", file=sys.stderr)
    result = latency_eval.evaluate(pipeline, runs=args.runs,
                                   topics=args.topics or None,
                                   articles=articles)
    print(result.table())
    return 0


def _cmd_export_clustering_pairs(args) -> int:
    from cura.eval import clustering as cl_eval

    if args.input:
        articles = load_articles_json(args.input)
    else:
        from cura.ingest import fetch_reddit, fetch_rss
        from cura.ingest.store import merge_and_save
        print("[cura] fetching live coverage…", file=sys.stderr)
        articles = merge_and_save(fetch_rss() + fetch_reddit())
    snapshot = args.out.rsplit(".", 1)[0] + ".snapshot.json"
    n = cl_eval.export_pair_annotation(articles, args.out, snapshot,
                                       per_bucket=args.per_bucket)
    print(f"wrote {n} candidate pairs -> {args.out} (label `same_event`: yes/no)"
          f"\ncorpus snapshot -> {snapshot}")
    print(f"score with: python -m cura eval-clustering --pairs {args.out} "
          f"--snapshot {snapshot}")
    return 0


def _cmd_eval_clustering(args) -> int:
    from cura.eval import clustering as cl_eval
    from cura.ingest.cluster import cluster_articles

    print(cl_eval.evaluate_pairs(args.snapshot, args.pairs, cluster_articles,
                                 "tf-idf + entity gate").table())
    from cura.ingest import cluster_embed
    if cluster_embed.available():
        print()
        print(cl_eval.evaluate_pairs(args.snapshot, args.pairs,
                                     cluster_embed.embed_cluster_articles,
                                     "embeddings + entity gate").table())
    else:
        print('\n(embeddings extra not installed — pip install -e ".[embeddings]" '
              "to compare the stretch clusterer)")
    return 0


def _cmd_export_tts_eval(args) -> int:
    from cura.eval import tts as tts_eval

    pipeline = Pipeline(store=False)
    articles = load_articles_json(args.input) if args.input else None
    briefing, _ = pipeline.run(topics=args.topics or None, articles=articles)
    # Story sentences only - the greeting/sign-off aren't representative
    sentences = [s.text for s in briefing.segments[1:-1]
                 if len(s.text.split()) >= 6][: args.sentences]
    print(f"[cura] rendering {len(sentences)} sentences with Coqui — "
          "first run downloads the model", file=sys.stderr)
    n = tts_eval.export_listening_test(sentences, args.out)
    print(f"wrote {n} stimuli + test.html -> {args.out}\n"
          f"open {args.out}/test.html in a browser (per rater), then score "
          f"with: python -m cura eval-tts --data <ratings.csv ...>")
    return 0


def _cmd_eval_tts(args) -> int:
    from cura.eval import tts as tts_eval

    print(tts_eval.evaluate(args.data).table())
    return 0


def _cmd_eval_user_study(args) -> int:
    from cura.eval import user_study as user_study_eval

    print(user_study_eval.evaluate(args.data).table())
    return 0


def _cmd_export_triangulation(args) -> int:
    from cura.eval import triangulation as tri_eval

    if args.input:
        articles = load_articles_json(args.input)
    else:
        from cura.ingest import fetch_reddit, fetch_rss
        feeds = load_feeds_json(args.feeds) if args.feeds else None
        print("[cura] fetching live coverage…", file=sys.stderr)
        articles = fetch_rss(feeds) + fetch_reddit()
    clusters = tri_eval.collect_clusters(
        articles, stance_classifier=_make_stance_classifier(args),
        min_sources=args.min_sources, limit=args.limit)
    sidecar = args.model or (args.out.rsplit(".", 1)[0] + ".model.json")
    n = tri_eval.export_annotation_pack(clusters, args.out, sidecar)
    print(f"wrote {n} stories -> {args.out} (annotate the `contested` column: "
          f"yes/no)\nmodel sidecar -> {sidecar} (don't read it while annotating)")
    print("score with: python -m cura eval-triangulation "
          f"--data {args.out} --model {sidecar} --sweep")
    return 0


def _cmd_eval_triangulation(args) -> int:
    from cura.eval import triangulation as tri_eval

    print(tri_eval.evaluate(args.data, args.model).table())
    if args.sweep:
        print()
        print(tri_eval.sweep(args.data, args.model))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cura", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="produce a briefing")
    p_run.add_argument("--topics", nargs="*", help="topic keywords to personalise on")
    p_run.add_argument("--input", help="JSON file of articles (offline mode)")
    p_run.add_argument("--max-stories", type=int, default=9)
    p_run.add_argument("--format", choices=["text", "json", "newspaper", "audio"],
                       default="text",
                       help="text feed, UI contract JSON, one-page newspaper HTML, "
                            "or Web Speech audio-player HTML")
    p_run.add_argument("--json", action="store_true",
                       help="shorthand for --format json")
    p_run.add_argument("--out", help="write output to a file")
    p_run.add_argument("--abstractive", action="store_true",
                       help="summarise with BART instead of the TextRank "
                            'baseline (needs pip install -e ".[abstractive]")')
    p_run.add_argument("--abstractive-model", default="facebook/bart-large-cnn")
    p_run.add_argument("--stance-transformer", action="store_true",
                       help="classify stance with fine-tuned RoBERTa instead "
                            "of the VADER baseline (needs pip install -e "
                            '".[stance-transformer]")')
    p_run.add_argument("--stance-model",
                       default="cardiffnlp/twitter-roberta-base-sentiment-latest")
    p_run.add_argument("--feeds",
                       help="JSON file of {source, topic, url} feed specs "
                            "(default: the built-in diverse feed set)")
    p_run.add_argument("--no-store", action="store_true",
                       help="don't merge live ingestion into the rolling "
                            "72h article store (~/.cura)")
    p_run.add_argument("--embed-cluster", action="store_true",
                       help="cluster with sentence embeddings instead of the "
                            'TF-IDF baseline (needs pip install -e ".[embeddings]")')
    p_run.set_defaults(func=_cmd_run)

    p_srv = sub.add_parser("serve", help="run the Cura web app (pipeline + UI)")
    _add_serve_args(p_srv)
    p_srv.add_argument("--present", action="store_true",
                       help="presentation mode for the demo video: wait for the "
                            "first edition, then open the browser straight into "
                            "the guided tour")
    p_srv.set_defaults(func=_cmd_serve)

    p_present = sub.add_parser(
        "present",
        help="serve in presentation mode (guided tour) for the demo video — "
             "an alias for `serve --present`")
    _add_serve_args(p_present)
    p_present.set_defaults(func=_cmd_serve, present=True)

    p_xsp = sub.add_parser("export-stance-pack",
                           help="blind headline sample from the article store "
                                "for hand-labelling (stance domain gap)")
    p_xsp.add_argument("--out", default="cura/eval/datasets/stance-headlines.csv")
    p_xsp.add_argument("--n", type=int, default=200)
    p_xsp.add_argument("--input", help="JSON articles file instead of the store")
    p_xsp.set_defaults(func=_cmd_export_stance_pack)

    p_es = sub.add_parser("eval-stance", help="macro-F1 + confusion matrix vs VADER")
    p_es.add_argument("--data", required=True, help="CSV with text,label columns")
    p_es.add_argument("--transformer", action="store_true",
                      help="also evaluate the transformer classifier")
    p_es.add_argument("--transformer-model",
                      default="cardiffnlp/twitter-roberta-base-sentiment-latest")
    p_es.set_defaults(func=_cmd_eval_stance)

    p_su = sub.add_parser("eval-summary", help="ROUGE + faithfulness vs TextRank")
    p_su.add_argument("--data", required=True,
                      help="JSON list of {document, reference} pairs")
    p_su.add_argument("--abstractive", action="store_true",
                      help="also evaluate the abstractive summariser")
    p_su.add_argument("--abstractive-model", default="facebook/bart-large-cnn")
    p_su.set_defaults(func=_cmd_eval_summary)

    p_xs = sub.add_parser("export-site",
                          help="write a static, zero-API edition "
                               "(GitHub Pages-ready; visitors can't spend tokens)")
    p_xs.add_argument("--out", default="_site")
    p_xs.add_argument("--input", help="JSON file of articles (offline mode; "
                                      "default: live ingestion)")
    p_xs.add_argument("--topics", nargs="*")
    p_xs.add_argument("--feeds", help="JSON file of {source, topic, url} feed specs")
    p_xs.add_argument("--editorial", action="store_true",
                      help="bake ONE Cleo editorial at export time "
                           "(your key, your cost — nothing ships to visitors)")
    p_xs.add_argument("--light", action="store_true",
                      help="baselines only (skip auto-detected stretch models)")
    p_xs.add_argument("--no-store", action="store_true")
    p_xs.add_argument("--stance-transformer", action="store_true")
    p_xs.add_argument("--stance-model",
                      default="cardiffnlp/twitter-roberta-base-sentiment-latest")
    p_xs.add_argument("--neural-tts", action="store_true")
    p_xs.set_defaults(func=_cmd_export_site)

    p_lat = sub.add_parser("eval-latency",
                           help="per-stage latency: mean/p95 over N runs")
    p_lat.add_argument("--input", help="JSON file of articles (offline mode, "
                                       "reproducible; default: live ingestion)")
    p_lat.add_argument("--runs", type=int, default=5)
    p_lat.add_argument("--topics", nargs="*")
    p_lat.add_argument("--max-stories", type=int, default=9)
    p_lat.add_argument("--abstractive", action="store_true",
                       help="measure the BART summariser instead of TextRank")
    p_lat.add_argument("--abstractive-model", default="facebook/bart-large-cnn")
    p_lat.add_argument("--stance-transformer", action="store_true",
                       help="measure the RoBERTa stance model instead of VADER")
    p_lat.add_argument("--stance-model",
                       default="cardiffnlp/twitter-roberta-base-sentiment-latest")
    p_lat.set_defaults(func=_cmd_eval_latency)

    p_xcp = sub.add_parser("export-clustering-pairs",
                           help="sample hard article pairs as a blind "
                                "annotation CSV + corpus snapshot")
    p_xcp.add_argument("--input", help="JSON file of articles (offline mode; "
                                       "default: live ingestion + store)")
    p_xcp.add_argument("--out", default="clustering_pairs.csv")
    p_xcp.add_argument("--per-bucket", type=int, default=20,
                       help="pairs per sampling bucket (tfidf-top, embed-top, "
                            "random band)")
    p_xcp.set_defaults(func=_cmd_export_clustering_pairs)

    p_ecl = sub.add_parser("eval-clustering",
                           help="pair precision/recall/F1 per clusterer on "
                                "labelled pairs")
    p_ecl.add_argument("--pairs", required=True,
                       help="the pairs CSV with `same_event` filled in")
    p_ecl.add_argument("--snapshot", required=True,
                       help="the corpus snapshot JSON from the export")
    p_ecl.set_defaults(func=_cmd_eval_clustering)

    p_xtts = sub.add_parser("export-tts-eval",
                            help="render briefing sentences with Coqui + a "
                                 "blind MOS listening-test page")
    p_xtts.add_argument("--input", help="JSON file of articles (offline mode; "
                                        "default: live ingestion)")
    p_xtts.add_argument("--topics", nargs="*")
    p_xtts.add_argument("--sentences", type=int, default=10)
    p_xtts.add_argument("--out", default="cura/eval/datasets/tts-listening-test",
                        help="output folder for stimuli + test.html")
    p_xtts.set_defaults(func=_cmd_export_tts_eval)

    p_etts = sub.add_parser("eval-tts",
                            help="aggregate listening-test ratings: MOS + CI "
                                 "per engine, paired diff, preference")
    p_etts.add_argument("--data", required=True, nargs="+",
                        help="one or more ratings CSVs from test.html")
    p_etts.set_defaults(func=_cmd_eval_tts)

    p_eus = sub.add_parser("eval-user-study",
                           help="aggregate questionnaire responses: Likert "
                                "medians/IQR, format ranks, contested agreement")
    p_eus.add_argument("--data",
                       default="cura/eval/datasets/user-study/responses.csv",
                       help="transcribed responses CSV (one row per participant)")
    p_eus.set_defaults(func=_cmd_eval_user_study)

    p_xt = sub.add_parser("export-triangulation",
                          help="export multi-source stories as a blind "
                               "annotation CSV + model sidecar")
    p_xt.add_argument("--input", help="JSON file of articles (offline mode; "
                                      "default: live ingestion)")
    p_xt.add_argument("--feeds", help="JSON file of {source, topic, url} feed specs")
    p_xt.add_argument("--out", default="triangulation_annotate.csv",
                      help="annotation CSV to write")
    p_xt.add_argument("--model", help="model sidecar JSON path "
                                      "(default: <out>.model.json)")
    p_xt.add_argument("--limit", type=int, default=30,
                      help="max stories to export")
    p_xt.add_argument("--min-sources", type=int, default=2,
                      help="only stories covered by at least this many sources")
    p_xt.add_argument("--stance-transformer", action="store_true",
                      help="use the RoBERTa stance model instead of VADER")
    p_xt.add_argument("--stance-model",
                      default="cardiffnlp/twitter-roberta-base-sentiment-latest")
    p_xt.set_defaults(func=_cmd_export_triangulation)

    p_et = sub.add_parser("eval-triangulation",
                          help="agreement between the contested flag and "
                               "human labels (+ threshold sweep)")
    p_et.add_argument("--data", required=True,
                      help="the annotation CSV with `contested` filled in")
    p_et.add_argument("--model", required=True, help="the model sidecar JSON")
    p_et.add_argument("--sweep", action="store_true",
                      help="also grid-search the spread/entropy thresholds")
    p_et.set_defaults(func=_cmd_eval_triangulation)

    args = parser.parse_args(argv)
    _force_utf8_output()
    return args.func(args)


def _force_utf8_output() -> None:
    """Briefing text carries em dashes, curly quotes and box-drawing glyphs;
    Windows pipes/redirects default to a legacy code page (cp1252) that cannot
    encode them and print() would crash. Emit UTF-8 everywhere, replacing
    anything a stream still cannot take rather than dying."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass  # exotic stream (tests, embedders) - leave it alone


if __name__ == "__main__":
    raise SystemExit(main())
