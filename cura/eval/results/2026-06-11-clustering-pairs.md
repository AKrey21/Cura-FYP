# Event clustering - pair-labelled benchmark (2026-06-11)

**Question.** Does embedding-based clustering (`.[embeddings]`,
all-MiniLM-L6-v2) beat the TF-IDF leader baseline enough to become the
default? Both run the identical leader algorithm + shared-entity gate
(`leader_cluster`), so the comparison isolates the document representation.

**Method.** From a live 1,000-article corpus (rolling store + that day's
fetch), 60 cross-outlet candidate pairs sampled adversarially: top-20 by
TF-IDF similarity, top-20 by embedding similarity (so the set favours
neither method), and 20 from a random mid-similarity band (supplying
negatives, including hard ones - two different World Cup stories, two
different election results). Labelled same-event yes/no by a **declared LLM
annotator** (Claude Fable 5) from titles + leads: 42 same-event / 18
different. Pair-level same-event judgement is far more objective than the
triangulation study's "contested" construct, so LLM labels carry more
weight here, but the disclosure stands. Score: a labelled pair counts as
predicted-same when both articles land in the same cluster.

Reproduce: `python -m cura export-clustering-pairs` → label →
`python -m cura eval-clustering --pairs … --snapshot …`.

## Results (pair precision / recall / F1)

| clusterer | threshold | P | R | F1 | clusters |
|---|---|---|---|---|---|
| TF-IDF + gate | 0.14 (then-default) | 1.000 | 0.857 | 0.923 | 608 |
| **TF-IDF + gate** | **0.12 (sweep opt.)** | **1.000** | **0.905** | **0.950** | 556 |
| embeddings + gate | 0.45 (then-default) | 1.000 | 0.833 | 0.909 | 692 |
| embeddings + gate | 0.35 (sweep opt.) | 0.975 | 0.929 | 0.951 | 562 |
| embeddings + gate | 0.50 | 1.000 | 0.905 | 0.950 | 741 |

## Decisions

1. **TF-IDF stays the default.** At each method's optimum the benchmark is
   a statistical tie (0.950 vs 0.951 - a one-pair difference at n=60),
   and the baseline costs nothing while embeddings add a ~90 MB model and
   ~30–60 s of CPU encoding per edition build. The stretch is retained as
   an opt-in (`--embed-cluster`) with its default moved to no advantage -
   left at 0.45 pending a larger labelled set.
2. **`SIMILARITY_THRESHOLD` 0.14 → 0.12** - recall +4.8 pts at unchanged
   perfect precision. The earlier fear about lowering the threshold
   (cross-event chaff in the 0.10–0.15 band) is handled by the entity
   gate, which this benchmark shows is the load-bearing component: *both*
   representations hit precision 1.000 with it in place.
3. **The entity gate generalises.** It was added for TF-IDF's
   same-vocabulary failure mode but gives the embedding clusterer perfect
   precision too at thresholds ≥0.40.

## Caveats

- n=60 pairs, single corpus day, LLM labels (declared). The positive class
  dominates the top-similarity buckets; hard negatives come mainly from
  the random band. A second day's export + the author spot-checking ~15
  pairs would firm this up cheaply.
- Greedy leader clustering is non-monotonic in the threshold (seed
  assignment changes), visible as recall wobble across the sweep - report
  the sweep, not a single point.
