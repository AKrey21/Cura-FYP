# Needs survey - September 2026 (retrospective)

**Collected:** September 2026 (the CSV date column records 2026-09-27 for
every row) · **Data:** `cura/eval/datasets/user-study/needs-survey-responses.csv`
(one row per participant) · **Questionnaire and researcher notes:**
`cura/eval/datasets/user-study/needs-survey-2026-09.md` · **Tally:**
`python -m cura eval-needs-survey`

## Purpose and status

A twelve-question needs survey put to the eight July user-study
participants (P01-P08, matched by code) to check the literature-derived
requirements of the design chapter against the intended audience. It was
gathered after the design, and the report says so: it is evidence *for*
the requirements, not design-stage research, and it supplements the July
study (`user-study-protocol.md`) rather than replacing it.

n = 8, so every statistic below is a count, never a percentage.

## Sample, delivery and consent

The same convenience sample as the July study, re-using its participant
codes so answers sit beside the study rows without names. The
questionnaire went out as an online form, the link sent to each
participant individually over WhatsApp on 27 September 2026 together with
their code. Consent for this follow-up was given by completion: the form
opened with an information preamble (purpose, five minutes, anonymous by
code, voluntary, any question skippable, reported only as group counts),
and submitting the form after reading it is the consent record. The July
information sheet does not on its own cover a follow-up questionnaire, so
this preamble, not that sheet, is the consent basis for the survey.

## Results (counts of 8 unless stated)

| Q | question | counts |
|---|---|---|
| 1 | how often they check the news | several times a day 4; about once a day 3; a few times a week 1; less often 0 |
| 2 | where they get it (tick all) | messaging groups 8; social media 7; news apps or websites 6; podcasts or radio 4; TV 2; email newsletters 1; other 1 (Hacker News) |
| 3 | deliberately avoid the news | sometimes 5; often 1; never 2 |
| 4 | why (tick all; the six who avoid) | too negative 4; no time 3; too much of it 2; cannot tell what to trust 1; other 3 (nothing to do with me; US politics crowding Singapore news; nothing left after a 12-hour shift) |
| 5 | how long a daily catch-up should take | under two minutes 2; about five minutes 4; about ten minutes 1; fifteen minutes or more 1 |
| 6 | the one format they would keep | text summary 3; audio 3; single page 2 |
| 7 | when in the day | morning 3; lunch 1; evening 1; no set time 3 |
| 8 | noticed outlets telling a story differently | often 3; sometimes 4; rarely 1; never 0 |
| 9 | what they do then | read more than one outlet 3; go with the outlet I trust 3; ignore it 1; not sure which to believe 1 |
| 10 | what would make them trust a summary (tick all) | which outlets 7; open the original 6; person or AI 4; where outlets disagree 3; how many outlets 2; single-outlet warning 2; other 2 (a Chinese version; news vs sponsored content) |

Data notes (kept as recorded): P05 and P07 never avoid the news and
skipped Q4, so Q4 counts are of the six who answered. Participant codes
per option come from `python -m cura eval-needs-survey`.

## Open answers (Q11-Q12), coded by the researcher

A participant can appear under more than one theme; the codes are listed
so the coding can be checked against the CSV.

- **Local relevance, followed topics first** (six: P02, P03, P04, P05,
  P07, P08). "Too many overseas news" (P05); MOE announcements on top
  (P04); a business section, local and global separated (P07); property,
  interest rates and HDB policy first (P08); which things matter for
  Singapore (P02); US politics leaking into Singapore reading (P03).
- **What changed since my last visit, or since the days I missed**
  (three: P03, P06, P07).
- **AI authorship disclosed up front** (P03 in the open answers; four
  ticked it in Q10: P01, P02, P03, P08).
- **Confirmed vs rumour, news vs marketing** (two: P04, P08); pairs with
  the Q10 single-outlet warning (P04, P06).
- **Short, bounded, no alert spam** (P01, P05, P07, P08): "TikTok
  length", "don't need so long", devalued BREAKING alerts, "short and
  clean".
- **Deduplicate and show the outlet count** (P03).
- **Negative news present but not first** (P06); no "fake-cheerful"
  narration voice (P02).
- **A Chinese or Malay edition** (two: P05, P06).
- **Paywalls** (P02, P07) and **clickbait, opinion-as-news, autoplay
  video** (P01, P03) as the irritants a summary sidesteps.

## Reading against the literature (report §2.2) and the design

Agreed:

- **A bounded catch-up.** Six of eight avoid the news at least sometimes
  (a higher share than the 40% in [2]; n = 8 supports only the
  direction), and six of eight want five minutes or less. Supports the
  five-minute budget and the page that ends.
- **Provenance is the trust currency.** Outlet names (seven) and a link to
  the original (six) lead Q10, the same headline finding as the July
  study's open answers.
- **Disagreement is noticed.** Seven of eight have noticed outlets telling
  a story differently, three of them often. Only three name "seeing where
  outlets disagree" as a trust factor, behind outlet names and links:
  surfacing disagreement is wanted (July T3) but it is not the first thing
  a reader checks.
- **No single format wins.** Text three, audio three, single page two;
  three morning readers and three with no set time. Supports three
  renderings of one edition and on-demand builds.

Did not agree:

- **Why readers avoid the news.** The literature's selective avoiders
  cite overload; here negativity (four of six) led, lack of time (three)
  came second and overload (two) third. The design's answer to overload,
  a bounded page, does not by itself answer negativity or relevance.
- **Local relevance.** Six of eight asked, unprompted, for local or
  followed topics first. Cura ranks followed topics first and builds
  on-demand editions by topic, but has no locality ordering and its feed
  set is global. This is the largest unmet need the survey found.
- **AI disclosure.** Four of eight want to know whether a person or an AI
  wrote it. The Experience view labels Cleo-written text; the summaries
  are extractive, verbatim source sentences, but the interface does not
  say so. Open.
- **What is new since last visit.** Three of eight; not in the design.
  The 72-hour store holds the history; no view shows it. Open.

## Limitations

Retrospective: gathered after the design, so it can confirm or contradict
requirements, not have shaped them. The same acquaintance sample as July,
with the same social-desirability caveat; n = 8 supports counts only.
Self-report of habits, not observed behaviour. Thematic coding of the open
answers is the researcher's judgement, listed above so it can be checked.
Two participants who never avoid the news skipped Q4, so its counts are
of six.
