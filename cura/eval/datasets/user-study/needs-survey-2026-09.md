# Keeping up with the news — a five-minute survey


**Your participant code:** ________

---

**1. How often do you check the news?**
- [ ] Several times a day
- [ ] About once a day
- [ ] A few times a week
- [ ] Less often than that

**2. Where do you mostly get it?** (tick all that apply)
- [ ] News apps or websites
- [ ] Social media
- [ ] Messaging groups (WhatsApp, Telegram)
- [ ] Podcasts or radio
- [ ] TV
- [ ] Email newsletters
- [ ] Other: ________

**3. Do you ever deliberately avoid the news?**
- [ ] Never
- [ ] Sometimes
- [ ] Often

**4. If you do, why?** (tick all that apply)
- [ ] There is too much of it
- [ ] It is too negative
- [ ] I cannot tell what to trust
- [ ] I do not have the time
- [ ] Other: ________

**5. How long would you want a daily catch-up to take?**
- [ ] Under two minutes
- [ ] About five minutes
- [ ] About ten minutes
- [ ] Fifteen minutes or more

**6. If you could have only one format for that catch-up, which would you pick?**
- [ ] A short text summary I can scroll
- [ ] Audio I can listen to while doing something else
- [ ] A single page I can skim, like a front page

**7. When in the day would you use it?**
- [ ] Morning, before or during the commute
- [ ] Around lunch
- [ ] Evening
- [ ] No set time

**8. Have you noticed different outlets telling the same story differently?**
- [ ] Often
- [ ] Sometimes
- [ ] Rarely
- [ ] Never

**9. When you notice that, what do you usually do?**
- [ ] Read more than one outlet
- [ ] Go with the outlet I trust
- [ ] Ignore it
- [ ] I am not sure which to believe

**10. What would make you trust a summary of a story?** (tick all that apply)
- [ ] Knowing which outlets it came from
- [ ] Knowing how many outlets covered it
- [ ] Being able to open the original article
- [ ] Seeing where the outlets disagree
- [ ] A warning when only one outlet has reported it
- [ ] Knowing whether a person or an AI wrote it
- [ ] Other: ________

**11. What is the most annoying thing about keeping up with the news?**

________________________________________________________________

**12. Anything else about how you would want a daily briefing to work?**

________________________________________________________________

Thank you.

---

## Researcher notes (not shown to participants)

- **Purpose.** Retrospective needs survey, September 2026, to check the
  literature-based requirements of the design chapter against the intended
  audience. The report must label it as gathered after the design; it
  supplements the July user study, it is not pre-design research.
- **Sample.** The eight July participants (P01–P08), matched by code so
  answers can sit beside the study rows without names.
- **Consent.** By completion: the intro above is the information
  preamble, and submitting the form after reading it is the consent
  record. The July information sheet and consent form
  (`participant-info-consent.html`) do not cover a follow-up on their own.
- **Question-to-requirement map.** Q1–Q5: a bounded catch-up, not an
  endless feed. Q6–Q7: the reader's choice of format. Q8–Q9: disagreement
  made visible; framing, not only tone. Q10: provenance the reader can
  check; a warning on thin sourcing. Q11–Q12: open needs.
- **Reporting.** n = 8, so report counts ("six of eight"), never
  percentages. Put the numbers in the requirements table (table rows do
  not count toward the chapter cap) and add one short paragraph saying what
  agreed with the literature and what did not.
- **Delivery.** Online form, one section per question, intro text and
  code field kept; link sent to each participant individually over
  WhatsApp on 27 September 2026 with their code.
- **Responses.** `needs-survey-responses.csv` beside this file, one row per
  participant: option text canonicalised for counting; "other" text, the
  two open answers and the participants' asides (`notes`) verbatim. Tally
  with `python -m cura eval-needs-survey`; results and reading in
  `cura/eval/results/needs-survey-2026-09.md`.
