# PROVENANCE: ORIGINAL - user-study aggregation (Likert summaries, format
# rankings, contested-flag agreement). Stdlib only. See PROVENANCE.md.
"""User-study evaluation - usefulness / trust / format preference.

The evaluation plan requires a small study (5–8 participants) on usefulness,
trust, and format preference. Sessions are run in person on the paper
questionnaire (``datasets/user-study/questionnaire.html``, printed); the
researcher transcribes each form into one row of ``responses.csv``.
``evaluate`` aggregates the rows: per-item Likert distributions with median
and IQR (n is far too small for parametric CIs - medians and raw counts are
the honest statistics), mean rank + first-place votes per format, the
"which would you open tomorrow" split, agreement with the contested flag,
and the open answers verbatim (thematic grouping stays a human judgement).

Real forms are imperfect. A skipped Likert item is transcribed as a blank
cell - excluded from that item's statistics, with per-item n reported - and
a refused forced ranking (tied ranks) is kept exactly as the participant
wrote it. Both are surfaced as data notes rather than silently repaired,
so the report can disclose them. Out-of-range values still fail loudly:
those are transcription slips, not participant behaviour.

Participants must be human - their trust in a briefing is the measurand;
an LLM proxy would be circular.
"""

from __future__ import annotations

import csv
import statistics
from dataclasses import dataclass

LIKERT_ITEMS = {
    "U1": "useful overview of the day's news",
    "U2": "right amount of detail for a quick catch-up",
    "U3": "would use as part of my daily routine",
    "T1": "trust it to represent the stories accurately",
    "T2": "'contested' label matched my own sense",
    "T3": "seeing disagreement raises my trust",
}
FORMATS = {"text": "rank_text", "audio": "rank_audio", "paper": "rank_paper"}


@dataclass
class UserStudyResult:
    n: int
    orders: dict            # presentation order -> count (counterbalancing)
    likert: dict            # item -> {n, dist, median, iqr, mean}
    ranks: dict             # format -> {mean_rank, first_votes}
    daily_pick: dict        # format -> count
    contested_agree: dict   # yes/no -> count
    open_answers: dict      # "O1"/"O2" -> [(participant, text)]
    notes: list             # data anomalies kept as recorded (blanks, tied ranks)

    def table(self) -> str:
        lines = [f"user study — {self.n} participant(s)"]
        orders = ", ".join(f"{o} ×{c}" for o, c in sorted(self.orders.items()))
        lines += [f"orders: {orders}", "",
                  f"{'item':<6} {'n':>3} {'1':>3} {'2':>3} {'3':>3} {'4':>3} {'5':>3} "
                  f"{'median':>7} {'IQR':>9} {'mean':>6}"]
        for item, s in self.likert.items():
            dist = " ".join(f"{s['dist'][v]:>3}" for v in range(1, 6))
            iqr = f"[{s['iqr'][0]:.0f}, {s['iqr'][1]:.0f}]"
            lines.append(f"{item:<6} {s['n']:>3} {dist} {s['median']:>7.1f} {iqr:>9} "
                         f"{s['mean']:>6.2f}   {LIKERT_ITEMS[item]}")
        lines += ["", f"{'format':<8} {'mean rank':>10} {'1st votes':>10} "
                      f"{'open tomorrow':>14}"]
        for fmt in FORMATS:
            r = self.ranks[fmt]
            lines.append(f"{fmt:<8} {r['mean_rank']:>10.2f} {r['first_votes']:>10} "
                         f"{self.daily_pick.get(fmt, 0):>14}")
        yes = self.contested_agree.get("yes", 0)
        lines.append(f"\ncontested story shown: {yes}/{self.n} agreed it was contested")
        if self.notes:
            lines.append("\ndata notes (kept as recorded — disclose in the report):")
            lines += [f"  {note}" for note in self.notes]
        for key, question in (("O1", "what would raise trust"),
                              ("O2", "missing or confusing")):
            lines.append(f"\n{key} — {question}:")
            lines += [f"  {p}: {text}" for p, text in self.open_answers[key]]
        return "\n".join(lines)


def load_responses(path: str) -> tuple[list[dict], list[str]]:
    """One row per participant. Returns (rows, notes): out-of-range or
    malformed values raise (transcription slips must surface immediately);
    blank Likert cells and tied ranks are legitimate participant behaviour
    and come back as notes instead."""
    with open(path, newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r.get("participant", "").strip()]
    if not rows:
        raise ValueError(f"no responses in {path} — transcribe the paper "
                         "questionnaires first (one row per participant)")
    notes = []
    for row in rows:
        p = row["participant"]
        for item in LIKERT_ITEMS:
            raw = row[item].strip()
            if not raw:
                notes.append(f"{p}: {item} left blank — excluded from that "
                             "item's stats")
            elif int(raw) not in range(1, 6):
                raise ValueError(f"{p}: {item}={raw} outside 1–5")
        ranks = {fmt: int(row[col]) for fmt, col in FORMATS.items()}
        if set(ranks.values()) - {1, 2, 3}:
            raise ValueError(f"{p}: format ranks must be 1–3, got {ranks}")
        if sorted(ranks.values()) != [1, 2, 3]:
            pretty = ", ".join(f"{f}={v}" for f, v in ranks.items())
            notes.append(f"{p}: tied format ranks ({pretty})")
        if row["daily_pick"] not in FORMATS:
            raise ValueError(f"{p}: daily_pick={row['daily_pick']!r} "
                             f"(expected one of {sorted(FORMATS)})")
        if row["contested_agree"] not in ("yes", "no"):
            raise ValueError(f"{p}: contested_agree={row['contested_agree']!r} "
                             "(expected yes/no)")
    return rows, notes


def evaluate(path: str) -> UserStudyResult:
    rows, notes = load_responses(path)

    likert = {}
    for item in LIKERT_ITEMS:
        values = sorted(int(r[item]) for r in rows if r[item].strip())
        quartiles = statistics.quantiles(values, n=4) if len(values) > 1 else \
            [values[0], values[0], values[0]]
        likert[item] = {
            "n": len(values),
            "dist": {v: values.count(v) for v in range(1, 6)},
            "median": statistics.median(values),
            "iqr": (quartiles[0], quartiles[2]),
            "mean": statistics.mean(values),
        }

    ranks = {}
    for fmt, col in FORMATS.items():
        values = [int(r[col]) for r in rows]
        ranks[fmt] = {"mean_rank": statistics.mean(values),
                      "first_votes": values.count(1)}

    def _count(col: str) -> dict:
        out: dict[str, int] = {}
        for r in rows:
            out[r[col]] = out.get(r[col], 0) + 1
        return out

    return UserStudyResult(
        n=len(rows),
        orders=_count("order"),
        likert=likert,
        ranks=ranks,
        daily_pick=_count("daily_pick"),
        contested_agree=_count("contested_agree"),
        open_answers={key: [(r["participant"], r[key].strip()) for r in rows
                            if r[key].strip()] for key in ("O1", "O2")},
        notes=notes,
    )
