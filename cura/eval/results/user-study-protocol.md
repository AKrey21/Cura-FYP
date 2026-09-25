# User study - usefulness, trust, and format preference

**Sessions:** 11–14 July 2026 (two per day) · **Transcribed:** 2026-08-02
**Data:** `cura/eval/datasets/user-study/responses.csv` (one row per paper
questionnaire) · **Aggregate:** `python -m cura eval-user-study`

Participants must be human - their trust in a briefing is the measurand; an
LLM proxy would answer the question circularly.

## Design

Within-subjects: every participant used all three formats - text feed,
audio narration, one-page newspaper - in a counterbalanced order (all six
possible orders appear across the eight sessions; two orders occur twice).
The app ran the full stretch stack, recorded per row in the `stack` column:
RoBERTa stance, BART summaries, Coqui narration. Each session used the live
edition of its day; the contested-story probe used whichever story that
day's edition flagged, recorded in the researcher box on the paper form.

## Participants

n = 8 (top of the 5–8 planned range), a convenience sample of coursemates
and family known personally to the researcher; ages estimated 25–40 (not
formally recorded). Consent was verbal at session time - the researcher
explained what the study was for and participants agreed before starting -
and confirmed retrospectively in writing in August 2026 using the study's
information sheet and consent form
(`datasets/user-study/participant-info-consent.html`); signed forms are
stored separately from the questionnaires, which are anonymous (codes
P01–P08).

## Procedure

Sessions were capped at 30 minutes. Participants used the app on their own
devices, tried each format in their assigned order, then completed the
printed questionnaire (`datasets/user-study/questionnaire.html`): six
5-point Likert items (U1–U3 usefulness, T1–T3 trust), a forced ranking of
the three formats, "which would you open tomorrow", and two open questions.
The researcher box recorded order, stack, the contested story shown, and
whether the participant agreed it was contested.

## Results

| item | n | median | IQR | mean | statement |
|---|---|---|---|---|---|
| U1 | 8 | 4.0 | [3, 5] | 4.00 | useful overview of the day's news |
| U2 | 8 | 3.5 | [3, 4] | 3.50 | right amount of detail |
| U3 | 8 | 4.0 | [2, 5] | 3.50 | would use daily |
| T1 | 8 | 4.0 | [3, 4] | 3.50 | trust it to represent stories accurately |
| T2 | 7 | 4.0 | [2, 4] | 3.43 | contested label matched my own sense |
| T3 | 8 | 4.0 | [3, 5] | 3.88 | seeing disagreement raises my trust |

| format | mean rank | 1st-place votes | "open tomorrow" |
|---|---|---|---|
| audio | **1.75** | **4** | **4** |
| text | 1.88 | 3 | 3 |
| paper | 2.25 | 2 | 1 |

Contested-story probe: **6/8 agreed** the flagged story was contested.

Data notes (kept as recorded, not repaired): P02 left T2 blank (excluded
from that item, n=7); P03 tied text and audio at rank 1 ("I genuinely
couldn't pick between reading and listening").

## Reading

- **Usefulness holds:** U1 median 4.0, no rating below 2 on it; the one
  consistent critic (P04, 1s and 2s throughout) objects on principle to
  unverifiable summaries, not to execution.
- **The triangulation feature earns direct user evidence - with a split
  that matches the quantitative eval.** T3 ("seeing disagreement raises my
  trust") is the *strongest* trust item (3.88): disagreement-surfacing is
  wanted. T2 ("the label matched my sense") is the *weakest* (3.43), and
  P07's "both versions read the same" is a verbatim qualitative echo of the
  same-valence framing-clash false negatives found in triangulation round 3
  (`triangulation-protocol.md`). Two independent evaluations locate the
  same missing signal: stance *target*, not valence.
- **Provenance is the trust currency.** Half the sample (P01, P03, P04,
  P06) independently asked for source links, source counts, or checkable
  text as what would raise trust - the report's headline qualitative
  finding, and a concrete design implication (per-line attribution).
- **Format: audio narrowly first** (4 first-place votes, mean rank 1.75)
  over text (3, 1.88); the newspaper trails for daily use (one devotee,
  P07) - consistent with its role as the presentation showpiece rather
  than the daily driver.

## Limitations

n=8 supports medians and counts, not hypothesis tests. The sample is an
acquaintance convenience sample - social-desirability inflation is likely,
and the disclosed mitigations (anonymous forms, a visible critic in P04)
only soften it. Single ≤30-minute exposure - P07 said directly that a week
of use would be needed for a trust view. Own-device sessions mean
heterogeneous browsers/screens (uncontrolled, same caveat family as the
TTS study's environment column). Ages were not formally recorded; the
contested-story titles live on the paper forms but were not transcribed
into the CSV.
