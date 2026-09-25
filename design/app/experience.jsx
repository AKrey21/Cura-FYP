// PROVENANCE: ORIGINAL (bespoke to Cura) - React/JSX prototype component; the product spec (see design/HANDOFF.md). Third-party (CDN): React 18, ReactDOM, Babel standalone. See PROVENANCE.md.
// Cura - Experience view: "The Cura Daily" as a single broadsheet sheet.
// Not a book: one tall page of dense, column-flowed newsprint on a desk -
// the way a real paper reads. Stories pour into CSS columns that pack
// themselves (empty space is impossible by construction); sections run into
// each other under ruled headers; photos are halftone and used sparingly.
// Stories aren't links - reading is the interaction. The whole edition
// prints (allStories()), closing with the Nightcap (typeset for this
// reader from local signals) and the Index. Cleo's edited edition stays
// click-gated behind the press gate (?lock=1 forces it for demos).

const { useState: useStateE, useEffect: useEffectE, useRef: useRefE } = React;

const SECTION_ORDER = ['World', 'Politics', 'Economy', 'Technology', 'Science',
                       'Health', 'Climate', 'Sports', 'Arts', 'Top Stories'];

/* A faint paper-grain texture (SVG turbulence, no asset). */
const GRAIN =
  "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/%3E%3CfeColorMatrix values='0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.05 0'/%3E%3C/filter%3E%3Crect width='160' height='160' filter='url(%23n)'/%3E%3C/svg%3E\")";

function clampText(text, n) {
  text = String(text || '');
  if (text.length <= n) return text;
  const cut = text.slice(0, n);
  return cut.slice(0, Math.max(cut.lastIndexOf(' '), 1)) + ' …';
}

/* Synthesized paper rustle (Web Audio, no asset) - only on user-gesture
   replays; browsers block audio before the first interaction. */
function rustle() {
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    const ctx = window.__curaPaperCtx || (window.__curaPaperCtx = new Ctx());
    if (ctx.state === 'suspended') ctx.resume();
    const dur = 1.1;
    const buf = ctx.createBuffer(1, Math.floor(ctx.sampleRate * dur), ctx.sampleRate);
    const d = buf.getChannelData(0);
    for (let i = 0; i < d.length; i++) {
      const t = i / d.length;
      d[i] = (Math.random() * 2 - 1) * Math.pow(1 - t, 1.4) * (0.3 + 0.7 * Math.abs(Math.sin(t * 14)));
    }
    const src = ctx.createBufferSource(); src.buffer = buf;
    const bp = ctx.createBiquadFilter(); bp.type = 'bandpass';
    bp.frequency.value = 2300; bp.Q.value = 0.6;
    const gain = ctx.createGain(); gain.gain.value = 0.08;
    src.connect(bp); bp.connect(gain); gain.connect(ctx.destination);
    src.start();
  } catch (e) { /* garnish */ }
}

/* Newsprint photo: grayscale + halftone dots + ink caption. */
function PrintPhoto({ story, ratio = '16/9', caption = true, captionText }) {
  const credit = story.citations && story.citations.length
    ? 'via ' + story.citations[0].source : 'wire';
  return (
    <figure style={{ margin: '0 0 8px' }}>
      <div className="xp-halftone" style={{
        aspectRatio: ratio, position: 'relative', overflow: 'hidden',
        background: 'linear-gradient(135deg, var(--paper-3), var(--paper-2))',
        border: '1px solid var(--ink)',
      }}>
        <StoryImage src={story.image} alt={story.headline} />
      </div>
      {caption && (
        <figcaption style={{ marginTop: 4 }}>
          {captionText && (
            <span className="serif" style={{ fontSize: 11, fontStyle: 'italic', color: 'var(--ink-soft)', marginRight: 8 }}>
              {captionText}
            </span>
          )}
          <span style={{
            fontFamily: 'JetBrains Mono, monospace', fontSize: 8.5,
            letterSpacing: '0.14em', textTransform: 'uppercase',
            color: 'var(--ink-muted)',
          }}>Photograph · {credit}</span>
        </figcaption>
      )}
    </figure>
  );
}

function ExperienceView() {
  const pool = window.allStories ? allStories() : CURA_STORIES;

  // Cleo's editorial: click-gated (never auto-calls the API). Cached
  // server-side per edition, and inlined on reload once generated.
  const cleoAvailable = !!(window.CURA_LIVE && window.claude);
  const [editorial, setEditorial] = useStateE(
    (window.CURA_LIVE && window.CURA_LIVE.editorial) || null);
  const [edState, setEdState] = useStateE(editorial ? 'on' : 'idle');
  const [showEdited, setShowEdited] = useStateE(!!editorial);
  const ed = (showEdited && editorial) ? editorial : null;
  const headlineOf = (s) => (ed && ed.headlines && ed.headlines[s.id]) || s.headline;

  // The press gate (?lock=1 forces it on for demos, ?lock=0 skips it)
  const lockParam = new URLSearchParams(window.location.search).get('lock');
  const [locked, setLocked] = useStateE(
    lockParam === '1' ? true : lockParam === '0' ? false
      : (cleoAvailable && !editorial && !window.__curaXpWire));
  const generateAndUnlock = () => {
    setEdState('loading');
    const sig = window.CuraStore ? window.CuraStore.getSignals() : { topics: {} };
    const readerTopics = Object.keys(sig.topics || {}).filter(t => sig.topics[t]);
    fetch('/api/editorial', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topics: readerTopics }),  // personalises the nightcap
    })
      .then(r => { if (!r.ok) throw new Error('editorial ' + r.status); return r.json(); })
      .then(data => { setEditorial(data); setShowEdited(true); setEdState('on'); setLocked(false); })
      .catch(() => setEdState('error'));
  };
  const readWire = () => { window.__curaXpWire = true; setLocked(false); };

  // The reader, for the Nightcap
  const { signals } = window.useSignals ? window.useSignals() : { signals: { topics: {} } };
  const savedStore = window.useSaved ? window.useSaved() : { ids: [] };
  const followed = Object.keys(signals.topics || {}).filter(t => signals.topics[t]);

  // The lead is an editorial CALL, not a rank: when Cleo has edited the
  // paper, her pick leads; on the wire, coverage rank does.
  const lead = (ed && ed.lead && pool.find(s => s.id === ed.lead)) || pool[0];

  // Sections - classic order on the wire, the editor's order when edited
  const bySection = {};
  pool.filter(s => s.id !== lead.id).forEach(s => {
    (bySection[s.section] = bySection[s.section] || []).push(s);
  });
  let sections = SECTION_ORDER.filter(s => bySection[s])
    .concat(Object.keys(bySection).filter(s => SECTION_ORDER.indexOf(s) < 0));
  if (ed && ed.sectionOrder && ed.sectionOrder.length) {
    const order = ed.sectionOrder.filter(s => bySection[s]);
    sections = order.concat(sections.filter(s => order.indexOf(s) < 0));
  }
  const contested = pool.find(s => s.contested);

  // The judgment layer: prominence per story (the editor's call when
  // edited; first-of-section gets the photo on the wire), plus the
  // editor's-marks toggle - red-pencil reasoning printed on the page.
  const promOf = (s, i) => (ed && ed.prominence && ed.prominence[s.id])
    ? ed.prominence[s.id] : (i === 0 ? 'major' : 'standard');
  const [marks, setMarks] = useStateE(false);
  const markFor = (s, prom) => {
    if (s.contested) return 'keep the split visible — ' + s.sources + ' sources disagree';
    if (prom === 'brief') return 'held to a brief' + (s.sources <= 2 ? ': thin sourcing' : '');
    if (prom === 'major') return 'promoted: ' + s.sources + ' sources, ' + String(s.confidenceLabel || '').toLowerCase();
    return null;
  };

  const mono = (extra) => Object.assign({
    fontFamily: 'JetBrains Mono, monospace', fontSize: 10,
    letterSpacing: '0.22em', textTransform: 'uppercase', color: 'var(--ink-muted)',
  }, extra);

  /* ---------- the unroll: tonight's paper arrives rolled ----------------
     A masked reveal with a shrinking cylinder riding the reveal edge —
     clip-path + transforms only, driven by rAF (no per-frame React
     renders), so it stays smooth with the full sheet rendered. */
  const reduceMotion = window.matchMedia
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const [unroll, setUnroll] = useStateE(
    () => !reduceMotion && !locked && !window.__curaUnrolled);
  const sheetRef = useRefE(null);
  const rollRef = useRefE(null);
  const curlRef = useRefE(null);
  // Unlocking the press gate starts the unroll (first time this session)
  useEffectE(() => {
    if (!locked && !reduceMotion && !window.__curaUnrolled) setUnroll(true);
  }, [locked]);
  useEffectE(() => {
    if (!unroll || locked) return;
    window.__curaUnrolled = true;
    const sheet = sheetRef.current;
    if (!sheet) { setUnroll(false); return; }
    const H = sheet.offsetHeight;
    const DUR = Math.min(3200, 1400 + H * 0.45); // longer sheets unroll longer
    const D0 = 96, D1 = 10;                      // roll diameter, fat -> spent
    let raf;
    const t0 = performance.now();
    const step = (now) => {
      const k = Math.min(1, (now - t0) / DUR);
      const e = k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2; // easeInOutCubic
      const edge = e * H;
      const d = D0 - (D0 - D1) * e;
      sheet.style.clipPath = 'inset(0 0 ' + Math.max(0, 100 - e * 100) + '% 0)';
      const roll = rollRef.current, curl = curlRef.current;
      if (roll) {
        roll.style.transform = 'translateY(' + (edge - d / 2) + 'px)';
        roll.style.height = d + 'px';
      }
      if (curl) curl.style.transform = 'translateY(' + (edge - 46) + 'px)';
      if (k < 1) { raf = requestAnimationFrame(step); return; }
      sheet.style.clipPath = 'none';
      setUnroll(false);
    };
    raf = requestAnimationFrame(step);
    return () => { cancelAnimationFrame(raf); if (sheet) sheet.style.clipPath = 'none'; };
  }, [unroll, locked]);
  const replayUnroll = () => {
    if (unroll || reduceMotion) return;
    rustle();
    window.__curaUnrolled = false;
    setUnroll(true);
  };

  /* ---------- newsprint building blocks ---------- */

  const sectionRule = (name) => (
    <div style={{ breakInside: 'avoid', columnSpan: 'all', margin: '26px 0 14px' }}>
      <div style={{ borderTop: '2px solid var(--ink)', borderBottom: '1px solid var(--ink)', padding: '4px 0', display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <span className="serif" style={{ fontSize: 19, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase' }}>{name}</span>
        <span style={mono({ fontSize: 8 })}>{(bySection[name] || []).length} {(bySection[name] || []).length === 1 ? 'STORY' : 'STORIES'} · THE CURA DAILY</span>
      </div>
    </div>
  );

  const storyBlock = (s, prom) => {
    const big = prom === 'major';
    const brief = prom === 'brief';
    const paras = brief ? [] : (s.body || s.tldr || [s.dek]).slice(0, big ? 2 : 1);
    const kicker = big && ed && ed.kickers && ed.kickers[s.id];
    const mark = marks && markFor(s, prom);
    return (
      <article key={s.id} style={{ breakInside: 'avoid', margin: '0 0 ' + (brief ? 10 : 16) + 'px' }}>
        {kicker && (
          <div className="mono" style={{
            fontFamily: 'JetBrains Mono, monospace', fontSize: 8.5,
            letterSpacing: '0.22em', textTransform: 'uppercase',
            color: 'var(--accent)', marginBottom: 3,
          }}>{kicker}</div>
        )}
        {big && s.image && (
          <PrintPhoto story={s} ratio="16/9"
            captionText={ed && ed.captions && ed.captions[s.id]} />
        )}
        <h3 className="serif" style={{
          fontSize: big ? 23 : brief ? 14 : 16.5, lineHeight: 1.12, fontWeight: 600,
          letterSpacing: '-0.005em', margin: '0 0 5px',
        }}>{headlineOf(s)}</h3>
        {!brief && (
          <div className="serif" style={{ fontSize: 12.5, fontStyle: 'italic', lineHeight: 1.35, color: 'var(--ink-soft)', margin: '0 0 6px' }}>
            {clampText(s.dek, big ? 160 : 110)}
          </div>
        )}
        {paras.map((para, i) => (
          <p key={i} className="serif" style={{
            fontSize: 11.5, lineHeight: 1.5, textAlign: 'justify', margin: '0 0 6px',
          }}>{clampText(para, big ? 460 : 300)}</p>
        ))}
        {!brief && ed && ed.quotes && ed.quotes[s.id] && (
          <blockquote className="serif" style={{
            margin: '6px 0', padding: '5px 9px', borderLeft: '3px solid var(--ink)',
            background: 'var(--paper-2)', fontSize: 12.5, lineHeight: 1.35, fontStyle: 'italic', fontWeight: 500,
          }}>“{ed.quotes[s.id]}”</blockquote>
        )}
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 9, color: 'var(--ink-muted)' }}>
          <ConfBar level={s.confidence} label={s.confidenceLabel} />
          <span className="mono" style={{ fontSize: 8.5 }}>{s.sources} SRC</span>
          {s.contested && <span className="mono" style={{ fontSize: 8.5, color: 'var(--accent)', fontWeight: 600 }}>CONTESTED</span>}
        </div>
        {mark && <div className="xp-mark">✎ {mark}</div>}
      </article>
    );
  };

  /* ---------- the Nightcap (typeset for this reader; no model call) ----- */
  const sectionCounts = {};
  pool.forEach(s => { sectionCounts[s.section] = (sectionCounts[s.section] || 0) + 1; });
  const yours = followed.filter(t => sectionCounts[t]);
  const clippings = pool.filter(s => savedStore.ids && savedStore.ids.indexOf(s.id) >= 0).slice(0, 4);
  const watch = (window.CURA_TRENDS || []).slice(0, 3);
  const contestedCount = pool.filter(s => s.contested).length;

  return (
    <div className="scroll-area" style={{
      background: 'radial-gradient(1100px 700px at 50% 18%, #4A4034 0%, #2E2820 52%, #1B1712 100%)',
      position: 'relative',
    }}>
      <style>{`
        .xp-grain { position:absolute; inset:0; pointer-events:none; background-image:${GRAIN}; opacity:.55; }
        .xp-halftone img { filter: grayscale(1) contrast(1.12) brightness(1.04) sepia(.14); }
        .xp-halftone::after {
          content:''; position:absolute; inset:0; pointer-events:none;
          background-image: radial-gradient(circle, rgba(20,18,14,.65) 0.9px, transparent 1.1px);
          background-size: 3px 3px; mix-blend-mode: overlay;
        }
        .bs-cols { columns: 4; column-gap: 20px; column-rule: 1px solid var(--paper-rule); }
        .bs-cols-3 { columns: 3; column-gap: 22px; column-rule: 1px solid var(--paper-rule); }
        .xp-mark {
          display: inline-block; font-family: Fraunces, serif; font-style: italic;
          font-size: 11.5px; color: var(--accent); transform: rotate(-1.2deg);
          border-bottom: 1px dashed var(--accent); margin-top: 4px; padding-bottom: 1px;
        }
      `}</style>

      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        padding: '30px 24px 60px',
        filter: locked ? 'blur(16px) brightness(0.7) saturate(0.85)' : 'none',
        transition: 'filter .8s ease',
        pointerEvents: locked ? 'none' : 'auto',
      }}>
        {/* desk caption */}
        <div style={{
          fontFamily: 'JetBrains Mono, monospace', fontSize: 9, letterSpacing: '0.26em',
          textTransform: 'uppercase', color: 'rgba(244,239,230,0.5)', marginBottom: 16,
          display: 'flex', gap: 18, alignItems: 'center',
        }}>
          <span>The Cura Daily · the whole edition, one sheet</span>
          {!reduceMotion && (
            <button onClick={replayUnroll} title="Unroll tonight's paper again" style={{
              background: 'none', border: '1px solid rgba(244,239,230,0.25)', borderRadius: 3,
              color: 'rgba(244,239,230,0.6)', fontFamily: 'inherit', fontSize: 8.5,
              letterSpacing: '0.2em', padding: '3px 8px', cursor: 'pointer',
            }}>⟲ UNROLL</button>
          )}
          <button onClick={() => setMarks(m => !m)}
            title="Show the editor's reasoning on the page" style={{
              background: marks ? 'rgba(184,51,30,0.85)' : 'none',
              border: '1px solid ' + (marks ? 'rgba(184,51,30,0.9)' : 'rgba(244,239,230,0.25)'),
              borderRadius: 3, color: marks ? '#F4EFE6' : 'rgba(244,239,230,0.6)',
              fontFamily: 'inherit', fontSize: 8.5,
              letterSpacing: '0.2em', padding: '3px 8px', cursor: 'pointer',
            }}>✎ EDITOR’S MARKS</button>
          {editorial && (
            <span style={{ display: 'flex', gap: 4 }}>
              {[['wire', 'WIRE'], ['edited', 'EDITED BY CLEO']].map(([key, label]) => (
                <button key={key} onClick={() => setShowEdited(key === 'edited')} style={{
                  background: (key === 'edited') === showEdited ? 'rgba(244,239,230,0.9)' : 'none',
                  border: '1px solid rgba(244,239,230,0.3)', borderRadius: 3,
                  color: (key === 'edited') === showEdited ? '#1B1712' : 'rgba(244,239,230,0.6)',
                  fontFamily: 'inherit', fontSize: 8.5, letterSpacing: '0.18em',
                  padding: '3px 8px', cursor: 'pointer',
                }}>{label}</button>
              ))}
            </span>
          )}
        </div>

        {/* THE SHEET (wrapped so the unroll props ride above the clip) */}
        <div data-tour="newspaper" style={{ width: 'min(1100px, 96%)', position: 'relative' }}>
        <div ref={sheetRef} style={{
          background: 'var(--paper)', position: 'relative',
          boxShadow: '0 34px 60px rgba(0,0,0,0.55), 0 4px 14px rgba(0,0,0,0.4)',
          padding: '38px 44px 34px',
          clipPath: unroll ? 'inset(0 0 100% 0)' : 'none',
          willChange: unroll ? 'clip-path' : 'auto',
        }}>
          <div className="xp-grain" />

          {/* Masthead */}
          <div style={{ borderBottom: '3px double var(--ink)', paddingBottom: 12, textAlign: 'center' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={mono({ fontSize: 8.5 })}>VOL. I · EVENING EDITION</span>
              <span style={mono({ fontSize: 8.5 })}>{editionMeta().dateline.toUpperCase()}</span>
              <span style={mono({ fontSize: 8.5 })}>{pool.length} STORIES · {sections.length} SECTIONS</span>
            </div>
            <div className="serif" style={{ fontSize: 84, fontWeight: 600, lineHeight: 1, letterSpacing: '-0.01em', margin: '6px 0 2px' }}>
              The Cura Daily
            </div>
            <div style={mono({ fontSize: 8.5 })}>
              “SLOW NEWS, EXAMINED” · CONFIDENCE-RATED · SOURCE-CITED{ed ? ' · EDITED BY CLEO' : ''}
            </div>
          </div>

          {/* Editor's note (when edited) */}
          {ed && ed.note && (
            <div style={{ borderBottom: '1px solid var(--ink)', padding: '10px 0', display: 'flex', gap: 14, alignItems: 'baseline' }}>
              <span style={mono({ fontSize: 8, whiteSpace: 'nowrap' })}>FROM THE EDITOR</span>
              <span className="serif" style={{ fontSize: 13, fontStyle: 'italic', lineHeight: 1.45 }}>{ed.note}</span>
            </div>
          )}

          {/* FRONT: lead story + right rail */}
          <div style={{ display: 'grid', gridTemplateColumns: '2.1fr 1fr', gap: 24, padding: '18px 0 20px', borderBottom: '1px solid var(--ink)' }}>
            <article>
              <div style={mono({ fontSize: 9, color: 'var(--accent)', marginBottom: 6 })}>THE LEAD · {lead.section.toUpperCase()}</div>
              <h1 className="serif" style={{ fontSize: 40, lineHeight: 1.04, fontWeight: 600, letterSpacing: '-0.015em', margin: '0 0 8px' }}>
                {headlineOf(lead)}
              </h1>
              {ed && ed.headlines && ed.headlines[lead.id] && (
                <div style={mono({ fontSize: 8, margin: '0 0 6px' })}>WIRE: {lead.headline}</div>
              )}
              <div className="serif" style={{ fontSize: 16, fontStyle: 'italic', lineHeight: 1.35, color: 'var(--ink-soft)', margin: '0 0 12px' }}>
                {lead.dek}
              </div>
              {ed && ed.leadWhy && (
                <div style={{ fontSize: 11.5, fontStyle: 'italic', color: 'var(--accent)', margin: '0 0 10px' }}>Why it leads: {ed.leadWhy}</div>
              )}
              {marks && (
                <div className="xp-mark" style={{ marginBottom: 8 }}>
                  ✎ {ed && ed.lead === lead.id
                    ? 'the editor moved this to the front'
                    : 'leads by coverage: ' + lead.sources + ' independent sources'}
                  {lead.contested ? ' · contested — keep the split visible' : ''}
                </div>
              )}
              <PrintPhoto story={lead} ratio="16/7"
                captionText={ed && ed.captions && ed.captions[lead.id]} />
              <div className="serif drop-cap" style={{ columns: 2, columnGap: 22, columnRule: '1px solid var(--paper-rule)', fontSize: 12.5, lineHeight: 1.55, textAlign: 'justify' }}>
                {(lead.body || lead.tldr || [lead.dek]).slice(0, 3).map((para, i) => (
                  <p key={i} style={{ margin: '0 0 8px' }}>{para}</p>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 10, alignItems: 'center', fontSize: 10, color: 'var(--ink-muted)', marginTop: 4 }}>
                <ConfBar level={lead.confidence} label={lead.confidenceLabel} />
                <span>{lead.sources} independent sources · curated by Cleo</span>
              </div>
            </article>

            <aside style={{ borderLeft: '1px solid var(--ink)', paddingLeft: 18 }}>
              <div style={mono({ fontSize: 8.5, marginBottom: 8 })}>In this edition</div>
              {sections.map(name => (
                <div key={name} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', padding: '4px 0', borderBottom: '1px dotted var(--paper-rule)' }}>
                  <span className="serif" style={{ fontSize: 13.5, fontWeight: 600 }}>{name}</span>
                  <span style={mono({ fontSize: 8 })}>{bySection[name].length}</span>
                </div>
              ))}
              {contested && (
                <div style={{ marginTop: 14, padding: '10px 12px', background: 'var(--paper-2)', border: '1px solid var(--paper-rule)' }}>
                  <div style={mono({ fontSize: 8, marginBottom: 6 })}>MOST CONTESTED TODAY</div>
                  <div className="serif" style={{ fontSize: 14.5, fontWeight: 600, fontStyle: 'italic', lineHeight: 1.25, marginBottom: 5 }}>
                    “{clampText(headlineOf(contested), 90)}”
                  </div>
                  <div style={{ fontSize: 10, color: 'var(--ink-muted)' }}>{contested.sources} sources disagree on framing</div>
                </div>
              )}
              <div style={{ marginTop: 14 }}>
                <div style={mono({ fontSize: 8.5, marginBottom: 6 })}>Trending</div>
                {(window.CURA_TRENDS || []).slice(0, 4).map(t => (
                  <div key={t.rank} style={{ display: 'flex', gap: 8, alignItems: 'baseline', padding: '3px 0' }}>
                    <span className="serif" style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-muted)' }}>{t.rank}.</span>
                    <span className="serif" style={{ fontSize: 13, fontWeight: 600 }}>{t.label}</span>
                    <span className="mono" style={{ fontSize: 8, color: 'var(--green)', marginLeft: 'auto' }}>{t.delta}</span>
                  </div>
                ))}
              </div>
            </aside>
          </div>

          {/* the fold */}
          <div style={{
            height: 14, margin: '0 -44px',
            background: 'linear-gradient(180deg, rgba(14,26,43,0.10), transparent 55%, rgba(255,255,255,0.25))',
          }} />

          {/* BODY: sections flow as packed newsprint columns — no empty space,
              the next story always fills the gap */}
          {sections.map(name => (
            <div key={name}>
              {sectionRule(name)}
              <div className="bs-cols">
                {bySection[name].map((s, i) => storyBlock(s, promOf(s, i)))}
              </div>
            </div>
          ))}

          {/* From the publisher — an inline ad box, like a real paper */}
          <div style={{ margin: '28px 0 0', border: '2px solid var(--ink)', padding: '18px 20px', textAlign: 'center' }}>
            <div className="serif" style={{ fontSize: 15, color: 'var(--ink-muted)' }}>❦</div>
            <span className="serif" style={{ fontSize: 30, fontWeight: 600, marginRight: 14 }}>Hear it.</span>
            <span className="serif" style={{ fontSize: 14, fontStyle: 'italic', color: 'var(--ink-soft)', marginRight: 14 }}>
              Tonight’s edition, read aloud in about {editionMeta().minutes} minutes.
            </span>
            <button className="btn" onClick={() => { window.location.hash = '#listen'; }}>
              <CIcon name="listen" size={13} /> Open Listen
            </button>
            <div style={mono({ fontSize: 7.5, marginTop: 8 })}>— AN ANNOUNCEMENT FROM THE CURA DAILY —</div>
          </div>

          {/* THE NIGHTCAP — typeset for this reader */}
          <div style={{ margin: '26px 0 0', borderTop: '2px solid var(--ink)', paddingTop: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 10 }}>
              <span className="serif" style={{ fontSize: 19, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase' }}>The Nightcap</span>
              <span style={mono({ fontSize: 8 })}>
                {ed && ed.nightcap
                  ? 'WRITTEN BY CLEO FOR THIS READER · GROUNDED IN TONIGHT’S SOURCES'
                  : 'A COLUMN TYPESET FOR THIS READER ALONE · NO MODEL CALL'}
              </span>
            </div>
            <div className="bs-cols-3">
              <p className="serif" style={{ fontSize: 12.5, lineHeight: 1.55, margin: '0 0 8px', breakInside: 'avoid' }}>
                Tonight’s paper carried <strong>{pool.length} stories</strong> across{' '}
                <strong>{sections.length} sections</strong>
                {yours.length
                  ? <span> — including {yours.map((t, i) => (
                      <span key={t}><strong>{sectionCounts[t]} in {t}</strong>{i < yours.length - 1 ? ', ' : ''}</span>
                    ))}, which you follow.</span>
                  : <span>. Follow topics in Settings and this column starts keeping score for you.</span>}
                {contestedCount > 0 && (
                  <span> {contestedCount} {contestedCount === 1 ? 'story was' : 'stories were'} flagged
                  contested — where sources disagreed, you saw it marked.</span>
                )}
              </p>
              <div style={{ breakInside: 'avoid', margin: '0 0 10px' }}>
                <div style={mono({ fontSize: 8, marginBottom: 5 })}>YOUR CLIPPINGS</div>
                {clippings.length ? clippings.map((s, i) => (
                  <div key={s.id} style={{
                    border: '1px dashed var(--ink-muted)', padding: '6px 9px', marginBottom: 6,
                    transform: 'rotate(' + (i % 2 ? 0.7 : -0.7) + 'deg)', background: 'var(--paper-2)',
                  }}>
                    <div style={mono({ fontSize: 7, color: 'var(--accent)', marginBottom: 2 })}>§ {s.section}</div>
                    <div className="serif" style={{ fontSize: 11.5, fontWeight: 600, lineHeight: 1.25 }}>{clampText(headlineOf(s), 70)}</div>
                  </div>
                )) : (
                  <p className="serif" style={{ fontSize: 11.5, fontStyle: 'italic', color: 'var(--ink-muted)', margin: 0 }}>
                    Nothing pressed tonight — bookmark stories in Read and they’ll be clipped here tomorrow.
                  </p>
                )}
              </div>
              <div style={{ breakInside: 'avoid', margin: '0 0 10px' }}>
                <div style={mono({ fontSize: 8, marginBottom: 5 })}>WATCH TOMORROW</div>
                {watch.map(t => (
                  <div key={t.rank} style={{ display: 'flex', gap: 8, alignItems: 'baseline', padding: '3px 0', borderBottom: '1px dotted var(--paper-rule)' }}>
                    <span className="mono" style={{ fontSize: 8, color: 'var(--green)' }}>{t.delta}</span>
                    <span className="serif" style={{ fontSize: 12.5, fontWeight: 600 }}>{t.label}</span>
                  </div>
                ))}
              </div>
              <div style={{ breakInside: 'avoid' }}>
                <p className="serif" style={{ fontSize: 12.5, lineHeight: 1.55, fontStyle: 'italic', margin: 0 }}>
                  {ed && ed.nightcap
                    ? ed.nightcap
                    : yours.length
                      ? 'I’ll keep reading ' + yours.join(', ') + ' overnight, and tomorrow’s paper will lead with whatever the sources can’t agree on. Sleep well —'
                      : 'I’ll keep reading overnight. Tell me what you follow, and tomorrow’s paper will be yours. —'}
                </p>
                <div className="serif" style={{ fontSize: 19, fontStyle: 'italic', fontWeight: 600, marginTop: 4 }}>Cleo</div>
              </div>
            </div>
          </div>

          {/* COLOPHON / THE INDEX */}
          <div style={{ margin: '22px 0 0', borderTop: '3px double var(--ink)', paddingTop: 10 }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 8 }}>
              {((window.CURA_LIVE && window.CURA_LIVE.sources) || ['Reuters', 'BBC', 'CNA', 'Straits Times']).slice(0, 28).map(name => (
                <span key={name} className="src-chip" style={{ fontSize: 8 }}>{name}</span>
              ))}
            </div>
            <p className="serif" style={{ fontSize: 11.5, lineHeight: 1.5, color: 'var(--ink-soft)', margin: '0 0 10px' }}>
              Assembled by Cura: stories clustered across {editionMeta().scanned || 'today’s'} scanned
              articles, summarised, stance-checked per source, and triangulated for disagreement.
              Confidence counts independent outlets — never engagement.
              {ed ? ' Tonight’s headlines and editor’s note were written by Cleo, grounded in the cited sources.' : ''}
            </p>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={mono({ fontSize: 8.5 })}>END OF EDITION</span>
              <span style={mono({ fontSize: 8.5 })}>{editionMeta().scanned ? editionMeta().scanned + ' SCANNED · ' : ''}{pool.length} PRINTED</span>
              <span style={mono({ fontSize: 8.5 })}>TOMORROW AT 06:00</span>
            </div>
          </div>
        </div>

        {/* the roll riding the reveal edge */}
        {unroll && !locked && (
          <React.Fragment>
            <div ref={curlRef} style={{
              position: 'absolute', left: 0, right: 0, top: 0, height: 46,
              pointerEvents: 'none',
              background: 'linear-gradient(180deg, transparent, rgba(14,26,43,0.20))',
            }} />
            <div ref={rollRef} style={{
              position: 'absolute', left: '-1.5%', right: '-1.5%', top: 0, height: 96,
              borderRadius: 999, pointerEvents: 'none',
              background: 'linear-gradient(180deg, #E8E1CF 0%, #F4EFE0 24%, #CCC2AB 68%, #6E6450 100%)',
              boxShadow: '0 12px 26px rgba(0,0,0,0.55)',
            }}>
              {[['left', -3], ['right', -3]].map(([side, off]) => (
                <div key={side} style={{
                  position: 'absolute', top: 0, bottom: 0, [side]: off,
                  aspectRatio: '1 / 1', borderRadius: '50%',
                  background: 'repeating-radial-gradient(circle at 50% 50%, #F0EADA 0 2px, #C9BFA8 2px 4px, #ABA088 4px 5px)',
                  border: '1px solid #877D66',
                }} />
              ))}
            </div>
          </React.Fragment>
        )}
        </div>
      </div>

      {/* THE PRESS GATE — tonight's paper waits for its editor */}
      {locked && (
        <div style={{
          position: 'absolute', inset: 0, zIndex: 60,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'radial-gradient(800px 500px at 50% 45%, rgba(20,16,12,0.25), rgba(20,16,12,0.6))',
        }}>
          <div style={{
            width: 430, background: 'var(--paper)', border: '1px solid var(--paper-rule)',
            boxShadow: '0 36px 80px rgba(0,0,0,0.55)', padding: '34px 38px 28px',
            textAlign: 'center', position: 'relative', overflow: 'hidden',
          }}>
            <div className="xp-grain" />
            <div style={{ borderBottom: '3px double var(--ink)', paddingBottom: 12, marginBottom: 18 }}>
              <div style={mono({ fontSize: 8, marginBottom: 6 })}>
                {editionMeta().dateline.toUpperCase()} · EVENING EDITION
              </div>
              <div className="serif" style={{ fontSize: 34, fontWeight: 600, lineHeight: 1 }}>The Cura Daily</div>
            </div>

            <svg width="34" height="40" viewBox="0 0 34 40" style={{ margin: '0 auto 14px', display: 'block' }}>
              <rect x="3" y="17" width="28" height="20" rx="2.5" fill="none" stroke="var(--ink)" strokeWidth="2.5" />
              <path d="M9 17 v-5 a8 8 0 0 1 16 0 v5" fill="none" stroke="var(--ink)" strokeWidth="2.5" />
              <circle cx="17" cy="26" r="2.6" fill="var(--ink)" />
              <path d="M17 28 v4" stroke="var(--ink)" strokeWidth="2.5" />
            </svg>

            <p className="serif" style={{ fontSize: 16, lineHeight: 1.45, fontStyle: 'italic', color: 'var(--ink-soft)', margin: '0 0 6px' }}>
              Tonight’s paper is typeset — it’s waiting for its editor.
            </p>
            <p style={{ fontSize: 12, lineHeight: 1.55, color: 'var(--ink-muted)', margin: '0 0 20px' }}>
              Cleo rewrites the wire headlines in print voice, signs an editor’s note,
              and pulls tonight’s quotes — grounded only in the cited sources.
            </p>

            {edState === 'loading' ? (
              <div className="serif" style={{ fontSize: 14, fontStyle: 'italic', color: 'var(--ink-soft)', padding: '10px 0' }}>
                Cleo is editing tonight’s edition…
              </div>
            ) : (
              <button className="btn" onClick={generateAndUnlock} style={{
                background: 'var(--ink)', color: 'var(--paper)', width: '100%',
                justifyContent: 'center', padding: '12px 0', fontSize: 14,
              }}>
                <CIcon name="sparkle" size={15} /> Generate with AI · 1 model call
              </button>
            )}
            {edState === 'error' && (
              <div style={{ fontSize: 11, color: 'var(--accent)', marginTop: 8 }}>
                The editor was unreachable — try again.
              </div>
            )}

            <div style={mono({ fontSize: 7.5, margin: '14px 0 10px' })}>
              {pool.length} STORIES · {sections.length} SECTIONS · HALFTONE PRESS
            </div>
            <button onClick={readWire} style={{
              background: 'none', border: 'none', cursor: 'pointer',
              fontFamily: 'JetBrains Mono, monospace', fontSize: 9.5, letterSpacing: '0.18em',
              textTransform: 'uppercase', color: 'var(--ink-muted)', textDecoration: 'underline',
            }}>
              or read the wire edition — no model call →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

window.ExperienceView = ExperienceView;
