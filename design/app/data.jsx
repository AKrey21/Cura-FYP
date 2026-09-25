// PROVENANCE: ORIGINAL (bespoke to Cura) - React/JSX prototype component; the product spec (see design/HANDOFF.md). Third-party (CDN): React 18, ReactDOM, Babel standalone. Canned sample story/briefing data; replaced at runtime by the live pipeline (window.CURA_LIVE). See PROVENANCE.md.
// Cura - story + source data

const CURA_STORIES = [
  {
    id: 's-fed',
    section: 'Economy',
    headline: 'Fed signals first rate cut of the year, citing softening labor market',
    dek: 'Powell’s remarks at Jackson Hole moved markets sharply, but Fed officials remain divided on pace.',
    tldr: [
      'Fed Chair Powell hinted at a 25bp cut at the September meeting.',
      'Two-year Treasury yields fell 14 bps, the largest single-day drop since March.',
      'Internal dissent: three regional presidents publicly favor holding rates steady.',
    ],
    sources: 14,
    confidence: 4, // out of 5
    confidenceLabel: 'Well-sourced',
    timestamp: '42 min ago',
    why: 'You follow Economy + previously read Fed coverage',
    feature: true,
    minutes: 6,
    bias: { left: 38, center: 44, right: 18 },
    image: '#1A2438', // placeholder swatch
  },
  {
    id: 's-coastal',
    section: 'Climate',
    headline: 'Coastal cities accelerate seawall plans as insurers exit Florida market',
    dek: 'Three of the largest U.S. carriers won’t renew policies in flood-prone counties starting January.',
    sources: 9,
    confidence: 4,
    confidenceLabel: 'Well-sourced',
    timestamp: '2 hr ago',
    why: 'You bookmarked two stories on insurance withdrawal',
    minutes: 4,
  },
  {
    id: 's-chip',
    section: 'Technology',
    headline: 'TSMC delays Arizona fab opening to 2027, citing labor and grid constraints',
    dek: 'The flagship $40B project faces a second postponement, casting doubt on near-term reshoring goals.',
    sources: 11,
    confidence: 5,
    confidenceLabel: 'Highly verified',
    timestamp: '4 hr ago',
    why: 'Top story across your trusted sources today',
    minutes: 5,
  },
  {
    id: 's-election',
    section: 'Politics',
    headline: 'Gubernatorial debates pivot to housing as median rents hit 14-year high',
    dek: 'Both candidates released county-level affordability plans this week. Analysts find the math fragile.',
    sources: 7,
    confidence: 3,
    confidenceLabel: 'Mixed reporting',
    timestamp: '5 hr ago',
    why: 'You set Politics to “daily digest”',
    minutes: 4,
  },
  {
    id: 's-ukraine',
    section: 'World',
    headline: 'Black Sea grain corridor reopens after weeks of disruption',
    dek: 'Egyptian and Turkish negotiators credit a back-channel agreement; details remain undisclosed.',
    sources: 16,
    confidence: 4,
    confidenceLabel: 'Well-sourced',
    timestamp: '7 hr ago',
    why: 'You follow World affairs',
    minutes: 5,
  },
  {
    id: 's-health',
    section: 'Health',
    headline: 'CDC links rising tick-borne illness to range expansion, not detection bias',
    dek: 'A six-year longitudinal study settles a long-running methodological dispute.',
    sources: 6,
    confidence: 5,
    confidenceLabel: 'Highly verified',
    timestamp: '9 hr ago',
    why: 'New from a source you trust (CDC primary)',
    minutes: 3,
  },
  {
    id: 's-arts',
    section: 'Arts',
    headline: 'A quiet renaissance for repertory cinema, mapped',
    dek: 'Independent theaters report a third consecutive year of growth. The geography is surprising.',
    sources: 5,
    confidence: 4,
    confidenceLabel: 'Well-sourced',
    timestamp: '11 hr ago',
    why: 'Saturday Long Read — you opted in',
    minutes: 12,
  },
  {
    id: 's-sports',
    section: 'Sports',
    headline: 'WNBA viewership eclipses last year’s Finals — and the trend isn’t about one player',
    dek: 'Local-market ratings tell a more durable story than the national narrative.',
    sources: 8,
    confidence: 4,
    confidenceLabel: 'Well-sourced',
    timestamp: '14 hr ago',
    why: 'You follow Sports',
    minutes: 4,
  },
];

// Source comparison data for the verify view (story s-fed)
const COMPARE_SOURCES = [
  {
    name: 'Reuters',
    lean: 'CENTER',
    leanColor: '#6B7280',
    headline: 'Powell signals September rate cut; markets rally',
    framing: 'Cites labor-market data; emphasizes Powell’s exact wording (“time has come”).',
    quote: '“The time has come for policy to adjust,” Powell said in prepared remarks.',
    notes: ['Quote is verbatim', 'Three independent confirmations', 'No editorial framing'],
  },
  {
    name: 'WSJ',
    lean: 'CENTER-RIGHT',
    leanColor: '#8E5A2E',
    headline: 'Powell tilts dovish, but FOMC dissent grows louder',
    framing: 'Leads with internal disagreement among regional Fed presidents.',
    quote: 'Bowman, Logan and Schmid have publicly questioned the urgency of cuts.',
    notes: ['Same facts, different lead', 'Adds dissent context', 'Names three dissenters'],
  },
  {
    name: 'Bloomberg',
    lean: 'CENTER',
    leanColor: '#6B7280',
    headline: 'Two-year yields plunge as Powell opens door to easing',
    framing: 'Markets-first framing; minute-by-minute reaction in bond and equity markets.',
    quote: 'The two-year Treasury yield fell 14 bps, the steepest single-day move since March.',
    notes: ['Quantitative emphasis', 'Adds market data', 'No political framing'],
  },
];

// Listen view - episodes
const CURA_EPISODES = [
  {
    id: 'e-brief',
    type: 'BRIEF',
    title: 'Your Daily Brief — Tuesday, Aug 27',
    duration: '11:42',
    chapters: [
      { t: '0:00', label: 'Open — what changed overnight' },
      { t: '1:14', label: 'Fed: Powell’s Jackson Hole signal' },
      { t: '3:22', label: 'TSMC Arizona delay' },
      { t: '5:48', label: 'Coastal insurance withdrawal' },
      { t: '8:11', label: 'Black Sea grain corridor' },
      { t: '10:05', label: 'Briefly noted — 6 stories' },
    ],
    voice: 'Cleo — calibrated voice',
    confidence: 4,
  },
  {
    id: 'e-deep-fed',
    type: 'DEEP DIVE',
    title: 'How the Fed actually decides',
    duration: '24:18',
    voice: 'Cleo + archival audio',
    confidence: 4,
    desc: 'A grounded walkthrough of the FOMC’s decision process, with primary-source quotes.',
  },
  {
    id: 'e-deep-chip',
    type: 'DEEP DIVE',
    title: 'The Arizona fab, in three voices',
    duration: '18:54',
    voice: 'Cleo + cited interviews',
    confidence: 5,
    desc: 'TSMC executives, AZ labor officials, and federal CHIPS Act administrators — contrasted.',
  },
  {
    id: 'e-explain',
    type: 'EXPLAINER',
    title: 'What is a "real" rate cut, and why now?',
    duration: '6:30',
    voice: 'Cleo — explainer voice',
    confidence: 4,
    desc: 'No jargon. One clear question, answered.',
  },
];

// Listen view - full narrated transcript for the Daily Brief.
// Each segment is one spoken unit (sentence-level keeps Web Speech reliable and
// gives fine-grained transcript highlighting). `chapter` marks a new section.
const CURA_BRIEFING = [
  { chapter: 'Open — what changed overnight', text: 'Good morning. It’s Tuesday, the twenty-seventh of August. I’m Cleo, and this is your daily brief — nine stories, about fifteen minutes.' },
  { text: 'Overnight, the big mover was the Federal Reserve. Everything else is steadier, so let’s start there and work down.' },

  { chapter: 'The Fed — Powell’s Jackson Hole signal', text: 'At Jackson Hole, Fed Chair Jerome Powell said, quote, the time has come for policy to adjust. In central-bank language, that lands very close to a promise.' },
  { text: 'Markets agreed. The two-year Treasury yield fell fourteen basis points — the largest single-session drop since March. Stocks rallied, and the dollar slipped.' },
  { text: 'But the committee is not unanimous. Three regional presidents — Bowman, Logan, and Schmid — have publicly questioned whether the labor market is soft enough to justify cutting yet.' },
  { text: 'So the real test is the September meeting. I’ve rated this story well-sourced — fourteen outlets, and the key quote is verbatim across all of them.' },

  { chapter: 'Technology — the Arizona fab slips', text: 'In technology: TSMC has pushed its flagship Arizona chip plant to twenty twenty-seven. That’s the second delay in eighteen months for the forty-billion-dollar project.' },
  { text: 'The company cites labor shortages and a strained Phoenix-area power grid. This one is highly verified — eleven independent sources.' },

  { chapter: 'Climate — insurers exit Florida', text: 'On climate: three of the largest U.S. insurers will stop renewing policies in flood-prone Florida counties starting in January.' },
  { text: 'At the same time, several coastal cities are accelerating seawall construction. The two trends are linked — as private insurance retreats, public infrastructure is filling the gap.' },

  { chapter: 'World — the grain corridor reopens', text: 'Abroad: the Black Sea grain corridor has reopened after weeks of disruption. Egyptian and Turkish negotiators credit a back-channel agreement, though the details remain undisclosed.' },

  { chapter: 'Briefly noted', text: 'A few more, quickly. Gubernatorial debates have pivoted to housing, with median rents at a fourteen-year high.' },
  { text: 'The CDC has linked rising tick-borne illness to range expansion rather than better detection — settling a long-running scientific dispute.' },
  { text: 'And in culture: independent repertory cinemas report a third straight year of growth, with the geography of that revival genuinely surprising.' },

  { chapter: 'Close', text: 'That’s your brief. If you want to go deeper on any of these, just ask me — I’ll only answer from the sources I cited. Have a good Tuesday.' },
];

// Cleo conversation seed
const CLEO_SEED = [
  {
    role: 'cleo',
    text: 'Good morning. There are 9 stories in today’s edition — about 15 minutes. Want me to brief you, or is there something specific you’re tracking?',
    grounded: false,
  },
];

// Trends sidebar
const CURA_TRENDS = [
  { rank: 1, label: 'Jackson Hole', delta: '+412%', section: 'Economy' },
  { rank: 2, label: 'TSMC Arizona', delta: '+186%', section: 'Tech' },
  { rank: 3, label: 'FL insurance', delta: '+94%', section: 'Climate' },
  { rank: 4, label: 'Grain corridor', delta: '+71%', section: 'World' },
  { rank: 5, label: 'WNBA Finals', delta: '+58%', section: 'Sports' },
];

Object.assign(window, {
  CURA_STORIES, COMPARE_SOURCES, CURA_EPISODES, CURA_BRIEFING, CLEO_SEED, CURA_TRENDS,
});
