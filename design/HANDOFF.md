# Cura - Build Handoff

**Cura: AI-powered multi-format news intelligence.** Read / Listen / Experience the day's news, fact-check claims, and ask Cleo - Cura's grounded AI news helper.

This repo is a **high-fidelity, interactive prototype** that defines the product's UI, interactions, states, and data contracts. It is the spec. The surface:

- `Cura - Desktop.html` - desktop web app (Chrome-framed, 1440×880 canvas)

Open it directly in a browser. No build step - React + Babel are loaded from CDN and transpile the `.jsx` in-browser.

---

## What is REAL vs SIMULATED in the prototype

| Feature | Status in prototype | For production |
|---|---|---|
| **Listen narration** | **Real** - Web Speech API (`speechSynthesis`) reads the briefing aloud; waveform + transcript sync to it | Keep, or swap to a server TTS (e.g. for consistent voice) feeding the same transcript-segment model |
| **Cleo answers** | **Real** - calls an LLM, grounded in the loaded story set, with a scripted fallback when offline | Wire to your own model endpoint; keep the grounding prompt + citation contract |
| **Verify claim-check** | **Real** - LLM verdict (Supported/Mixed/Unverified/Contradicted) over the story set, with fallback | Same as Cleo |
| **Search, Saved, Settings** | **Real** - client-side filter, `localStorage` persistence | Move Saved/Settings to user account; Search to server index |
| **Story feed, episodes, source comparison** | **Simulated** - canned data in `app/data.jsx` | Replace with the live ingestion + NLP pipeline (below) |
| **Charts/thumbnails** | Inline SVG placeholders | Replace with real generated visuals |

> The prototype intentionally does **not** implement the RSS ingestion or NLP engine. It defines the **shape** of the data those systems must produce. Build the engine to satisfy the contracts below and the UI works unchanged.

---

## Backend to implement (from the proposal)

1. **Multi-source ingestion** - RSS/Atom from traditional outlets (CNN, BBC, CNA, Straits Times) + social (Reddit, X), normalised + deduplicated (URL + title).
2. **NLP pipeline** producing, per story: sentiment (VADER-style), topic (9 categories), named entities, keyphrases (TF-IDF), extractive summary → the `tldr` array.
3. **Confidence score** - derived from independent-source count (drives `confidence` 1–5 + `confidenceLabel`).
4. **Coverage/bias spread** - left/center/right distribution across sources (drives `bias`).
5. **Audio briefing** - assemble the day's stories into the ordered, chaptered transcript (`CURA_BRIEFING` shape) → narrate via TTS.
6. **Cleo grounding** - answer only from the day's story set; cite sources; refuse when ungrounded (prompt in `app/cleo.jsx`).
7. **Verify** - same grounding, returns a structured verdict (`app/read.jsx → ClaimChecker`).

---

## Data contracts

Defined in **`app/data.jsx`**. Match these shapes exactly.

### Story
```js
{
  id: 's-fed',                 // stable unique id
  section: 'Economy',          // one of the 9 topic categories
  headline: 'Fed signals first rate cut…',
  dek: 'Powell's remarks moved markets…',
  tldr: ['…', '…', '…'],       // extractive cited summary (optional)
  sources: 14,                 // independent source count
  confidence: 4,               // 1–5, from source count
  confidenceLabel: 'Well-sourced',
  timestamp: '42 min ago',
  why: 'You follow Economy + read Fed coverage',  // personalization reason
  minutes: 6,                  // est. read time
  bias: { left: 38, center: 44, right: 18 },      // coverage spread %, optional —
                               // live: outlet-lean distribution (AllSides-style
                               // map in cura/briefing/assemble.py), >=2 outlets
  feature: true,               // hero treatment (optional)
  body: ['…', '…'],            // article-page paragraphs (optional; live pipeline)
  citations: [{ source: 'Reuters', title: '…', url: 'https://…' }],  // optional
  image: 'https://…'           // lead image URL from the source feeds (optional)
}
```

The live edition payload (`window.CURA_LIVE`, from `cura serve`) additionally
carries: `estMinutes`, `scannedArticles`, `sources` (tracked outlet names),
`topics` (the topics this edition was built for - empty for the daily
edition), `builtAt` (epoch seconds), `audio` (one WAV URL per briefing
segment when serving `--neural-tts`),
`trends` (live `CURA_TRENDS` rows), `moreStories` (full Story objects for the
analysed clusters beyond the spoken briefing, selected round-robin across
topics so one heavy topic can't crowd the rest - they fill Read's section
tabs and are merged into search/saved/Cleo grounding), and `compare` -
`editorial` (when unlocked - Cleo's judgment layer: `note`, `lead` (story id),
`leadWhy`, `prominence` {id: major|standard|brief}, `kickers` {id},
`captions` {id}, `sectionOrder` [..], `headlines` {id}, `nightcap`,
`quotes` {id}), and the Verify view's source-comparison for the most
contested story:
```js
compare: { storyId, headline, confidence, confidenceLabel,
           sources: [{ name, lean, leanColor, headline, framing, quote, notes }],
           agree: ['…'], differ: ['…'] }
```

### Briefing segment (`CURA_BRIEFING`)
```js
{ chapter: 'The Fed — Powell's signal',  // optional: starts a new section
  text: 'One spoken sentence.' }          // keep sentence-level for TTS reliability
```

### Source comparison (`COMPARE_SOURCES`)
```js
{ name:'Reuters', lean:'CENTER', leanColor:'#6B7280',
  headline:'…', framing:'…', quote:'…', notes:['…','…'] }
```

### Episode (`CURA_EPISODES`), Trends (`CURA_TRENDS`) - see `app/data.jsx`.

### Client state (`app/store.jsx`, `localStorage`)
- `cura.saved` - array of story ids
- `cura.signals` - personalization: `{ topics{}, sources{}, cadence, defaultFormat, autoplayBrief, showConfidence, interests, keywords[] }` (`interests` = the reader's own words from onboarding; `keywords` = queryable phrases parsed from it)
- `cura.onboarded` - set once the welcome gate has been completed or skipped

---

## Views & behaviors

- **Read** - sticky section bar (Front page + one tab per topic with stories, followed topics first; deep-linkable as `#read/<Topic>`). Front page: hero + cluster + briefly-noted + trends + per-followed-topic teasers. Section tabs: section lead + card grid from `stories` + `moreStories`. Confidence bars, "why am I seeing this", coverage spread → Verify. Bookmark toggles Saved. **Loading state**: curating skeleton on first visit (`ReadSkeleton`). **On-demand (live)**: masthead "New edition…" form calls `window.curaRequestBriefing(topics)` → `POST /api/brief` re-runs the whole pipeline; the skeleton shows the requested topics while polling, the masthead tags on-demand editions and offers "back to the daily edition". Settings has a "re-curate from these topics" button using the same call.
- **Listen** - live narration; tap transcript line or scrub waveform to seek; speed 0.75–1.5×. Engine: server-rendered neural audio when the live payload carries `audio` (one WAV URL per `CURA_BRIEFING` segment, from `cura serve --neural-tts`), else Web Speech. Layout tweak: Immersive / Transcript. **Unsupported state**: shows a notice, transcript still navigable.
- **Experience** - "The Cura Daily" as a single broadsheet sheet on a lit desk: big masthead, lead story (drop-cap double-column text + halftone photo), a right rail (In this edition / most contested / trending), the fold, then the WHOLE edition (`allStories()`) flowing continuously as packed CSS-column newsprint under ruled section headers (classic newspaper order; column flow makes empty space impossible). Stories are NOT links - reading is the interaction. Photos are halftone and lead-only. The sheet ends with the publisher's inline ad box, **The Nightcap** (a three-column personal column typeset from local signals: followed-topic tally, saved-story clippings, tomorrow's watchlist, Cleo's signed note; no model call), and the colophon Index. The press gate blurs the sheet behind a "Generate with AI · 1 model call" lock when Cleo can edit but hasn't (`?lock=1` forces it, `?lock=0` skips it; "read the wire edition" bypasses); the Wire/Edited toggle lives in the desk caption.
- **Verify** - (1) **claim checker** (type a claim → grounded verdict + evidence), (2) three-source comparison.
- **Cleo** - desktop slide-over. Grounded chat, cited, "thinking" state, **live vs demo** indicator.
- **Saved** - reading list from bookmarks; empty state.
- **Settings** - personalization signals (topics, sources, cadence, format, toggles).
- **Search (⌘K)** - command palette filtering today's edition.

---

## Design system

Tokens live in each HTML `<style>` `:root`. Fonts: **Fraunces** (serif headlines), **Inter** (body), **JetBrains Mono** (labels).

```
--paper #F4EFE6  --paper-2 #EBE3D4  --paper-3 #E2D7C2
--ink #0E1A2B  --ink-soft #2A3548  --ink-muted #6B7280
--accent #B8331E  --accent-soft #D9A074  --green #1F5E3F
```
Dark mode tokens included (`.app-root.theme-dark`).

## File map
```
Cura - Desktop.html  # shell: fonts, CSS tokens, script load order
app/data.jsx        # ← data contracts (replace with live pipeline output)
app/store.jsx       # saved + signals (localStorage)
app/icons.jsx       # inline SVG icon set
app/shell.jsx       # sidebar + topbar (desktop)
app/read.jsx        # Read, Story detail, Verify + ClaimChecker, SaveButton, ReadSkeleton
app/listen.jsx      # Listen + Web Speech narration engine (useNarration)
app/experience.jsx  # newspaper edition
app/cleo.jsx        # Cleo chat + LLM grounding prompt + fallback
app/screens.jsx     # Saved, Settings, Search palette
app/root.jsx        # router, ⌘K, tweaks panel, mounts
app/tour.jsx        # guided product tour (press t)
components/          # chrome.jsx (browser frame), tweaks-panel.jsx
```

- **Onboarding (#welcome)** - first visit blurs the app behind a welcome gate: pick section chips and/or brief Cleo in your own words; the free text is parsed (one click-gated model call via `window.claude`, keyword matching as the offline fallback) into followed `topics` + queryable `keywords`, with an optional "re-curate tonight's edition from this brief" that drives `/api/brief`. Editable later in Settings ("Your brief to Cleo"); re-openable via `#welcome`.

## Known gaps (intentional - for production)
- Story bodies are sample copy; only `s-fed` has full article text.
