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


# ------------------------------------------------------------ needs survey --
# Retrospective needs survey, September 2026 (``datasets/user-study/
# needs-survey-2026-09.md``): twelve questions to the same eight participants,
# matched by code, gathered AFTER the design to check the literature-derived
# requirements against the intended audience. n = 8, so every statistic is a
# count ("six of eight"), never a percentage. Multi-select cells hold
# semicolon-separated options; "other" text, the two open questions and the
# participants' asides (``notes``) stay verbatim, and the thematic coding of
# the open answers remains a human judgement.

SURVEY_OPTIONS = {
    "q1_frequency": ("several times a day", "about once a day",
                     "a few times a week", "less often"),
    "q2_sources": ("news apps or websites", "social media", "messaging groups",
                   "podcasts or radio", "TV", "email newsletters", "other"),
    "q3_avoid": ("never", "sometimes", "often"),
    "q4_reasons": ("too much of it", "too negative",
                   "cannot tell what to trust", "no time", "other"),
    "q5_length": ("under two minutes", "about five minutes",
                  "about ten minutes", "fifteen minutes or more"),
    "q6_format": ("text summary", "audio", "single page"),
    "q7_time": ("morning", "lunch", "evening", "no set time"),
    "q8_noticed": ("often", "sometimes", "rarely", "never"),
    "q9_response": ("read more than one outlet", "go with the outlet I trust",
                    "ignore it", "not sure which to believe"),
    "q10_trust": ("which outlets", "how many outlets", "open the original",
                  "where outlets disagree", "single-outlet warning",
                  "person or AI", "other"),
}
SURVEY_MULTI = ("q2_sources", "q4_reasons", "q10_trust")   # tick all that apply
SURVEY_OPEN = {"q11_annoying": "most annoying thing about keeping up",
               "q12_briefing": "how a daily briefing should work"}
SURVEY_LABELS = {
    "q1_frequency": "Q1 how often they check the news",
    "q2_sources": "Q2 where they get it (tick all)",
    "q3_avoid": "Q3 deliberately avoid the news",
    "q4_reasons": "Q4 why (tick all; those who avoid)",
    "q5_length": "Q5 how long a daily catch-up should take",
    "q6_format": "Q6 the one format they would keep",
    "q7_time": "Q7 when in the day",
    "q8_noticed": "Q8 noticed outlets telling a story differently",
    "q9_response": "Q9 what they do then",
    "q10_trust": "Q10 what would make them trust a summary (tick all)",
}


@dataclass
class NeedsSurveyResult:
    n: int
    counts: dict        # question -> {option: count}, questionnaire order
    answered: dict      # question -> participants who answered it
    who: dict           # question -> {option: [participant codes]}
    other: dict         # question -> [(participant, "other" text)]
    open_answers: dict  # q11/q12 -> [(participant, text)]
    notes: list         # blanks kept as recorded

    def table(self) -> str:
        lines = [f"needs survey — {self.n} participant(s)"]
        for q, label in SURVEY_LABELS.items():
            lines += ["", f"{label}  ({self.answered[q]} of {self.n} answered)"]
            for opt, c in self.counts[q].items():
                codes = ", ".join(self.who[q][opt])
                lines.append(f"  {opt:<28} {c:>2} of {self.n}   {codes}")
            for p, text in self.other.get(q, []):
                lines.append(f"    other, {p}: {text}")
        if self.notes:
            lines.append("\ndata notes (kept as recorded):")
            lines += [f"  {note}" for note in self.notes]
        for key, question in SURVEY_OPEN.items():
            lines.append(f"\n{key[:3].upper()} — {question}:")
            lines += [f"  {p}: {text}" for p, text in self.open_answers[key]]
        return "\n".join(lines)


def _ticked(question: str, raw: str) -> list[str]:
    return [t.strip() for t in raw.split(";")] if question in SURVEY_MULTI else [raw]


def load_survey(path: str) -> tuple[list[dict], list[str]]:
    """One row per participant. An option outside the questionnaire raises
    (a transcription slip); a blank answer is kept and reported as a note."""
    with open(path, newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r.get("participant", "").strip()]
    if not rows:
        raise ValueError(f"no responses in {path}")
    notes = []
    for row in rows:
        p = row["participant"]
        for q, options in SURVEY_OPTIONS.items():
            raw = row[q].strip()
            if not raw:
                if q == "q4_reasons" and row["q3_avoid"].strip() == "never":
                    notes.append(f"{p}: Q4 not applicable (never avoids the news)")
                else:
                    notes.append(f"{p}: {q} left blank")
                continue
            for t in _ticked(q, raw):
                if t not in options:
                    raise ValueError(f"{p}: {q}={t!r} is not a questionnaire option")
            other_col = q.split("_")[0] + "_other"
            if "other" in _ticked(q, raw) and not row.get(other_col, "").strip():
                notes.append(f"{p}: {q} ticked 'other' with no text")
    return rows, notes


def needs_survey(path: str) -> NeedsSurveyResult:
    rows, notes = load_survey(path)
    counts, answered, who, other = {}, {}, {}, {}
    for q, options in SURVEY_OPTIONS.items():
        counts[q] = {opt: 0 for opt in options}
        who[q] = {opt: [] for opt in options}
        answered[q] = 0
        other_col = q.split("_")[0] + "_other"
        for row in rows:
            raw = row[q].strip()
            if not raw:
                continue
            answered[q] += 1
            for t in _ticked(q, raw):
                counts[q][t] += 1
                who[q][t].append(row["participant"])
            if row.get(other_col, "").strip():
                other.setdefault(q, []).append((row["participant"],
                                                row[other_col].strip()))
    return NeedsSurveyResult(
        n=len(rows), counts=counts, answered=answered, who=who, other=other,
        open_answers={key: [(r["participant"], r[key].strip()) for r in rows
                            if r[key].strip()] for key in SURVEY_OPEN},
        notes=notes,
    )
