// PROVENANCE: ORIGINAL (bespoke to Cura) - React/JSX prototype component; an
// in-app guided product tour for the demo video. Third-party (CDN): React 18,
// ReactDOM, Babel standalone. See PROVENANCE.md.
// Cura - Guided tour: a click-through walkthrough that spotlights each feature
// and auto-navigates between views, synced to the demo video script
// (report/VIDEO-SCRIPT.md, Scene 5). Self-mounts; inert until started.
//
// Start it any of these ways:
//   • press "t"  (when not typing in a field)
//   • load the app with  ?tour=1
//   • Tweaks panel → "▶ Guided tour"
//   • console: window.curaStartTour()
// Drive it: Next button, or → / Space / Enter ; Back or ← ; Esc to exit.
// The spotlight is click-through, so you can still operate the app underneath.

// Steps mirror the demo video's Scene 5 (report/VIDEO-SCRIPT.md): the in-app
// walk Read -> story -> Listen -> Experience -> Verify. Press Next in time with
// your narration; `say` is the verbatim script line (hidden until you click
// "script", so the recording stays clean). Scenes 1-4 (terminal) and 6 (PDF)
// are not app-driven, so the tour deliberately starts at Read and ends at
// Verify - trigger it as Scene 5 begins, and it is done when Scene 5 is.
const TOUR = [
  {
    view: 'read', target: '[data-tour="lead-story"]',
    title: 'The edition, as a product',
    body: 'The same pipeline output, now a briefing — read it, hear it, or see ' +
          'it. Each story carries its independent source count and confidence.',
    say: 'Now, I’ve had Cura running in the background since before this ' +
         'recording — so it’s already pulled today’s coverage and built the ' +
         'edition. Here’s what that same pipeline produces for a reader. Each ' +
         'story shows how many independent sources it has, and a confidence rating.',
  },
  {
    view: 'read', target: '[data-tour="spread"]',
    title: 'Coverage spread + contested',
    body: 'The left–centre–right spread and the contested marker come straight ' +
          'from the triangulation stage. (Then click the contested story.)',
    say: 'And this bar is the coverage spread — how much of the reporting leans ' +
         'left, centre, or right. See this story’s flagged contested? That means ' +
         'the pipeline found its sources don’t agree.',
  },
  {
    view: 'story', target: '[data-tour="story-meta"]',
    title: 'Inside the contested story',
    body: 'Independent sources, confidence, a cited summary, and footnotes to ' +
          'the original articles travel with every story.',
  },
  {
    view: 'listen', target: '[data-tour="listen-player"]',
    title: 'Listen — the narrated briefing',
    body: 'Press play. The transcript follows the audio, and you can tap any ' +
          'line to jump there.',
    say: 'The same briefing, narrated. The transcript follows the audio, and you ' +
         'can tap any line to jump there.',
  },
  {
    view: 'experience', target: '[data-tour="newspaper"]',
    title: 'Experience — the one-page newspaper',
    body: 'The whole day’s edition as a single broadsheet sheet, contested ' +
          'stories marked in place.',
    say: 'And the third format — the day’s edition laid out as a one-page newspaper.',
  },
  {
    view: 'verify', target: '[data-tour="verify-compare"]',
    title: 'Verify — triangulation made visible',
    body: 'The same story’s leads from each outlet, side by side, with each ' +
          'source’s lean.',
    say: 'This is triangulation made visible: the same story’s opening lines from ' +
         'Reuters, the Journal, and Bloomberg, side by side, with each outlet’s ' +
         'lean — so you can see the disagreement Cura measured.',
  },
];

const TOUR_Z = 9000;

function resolveHash(view) {
  if (!view) return null;
  if (view === 'story') {
    const all = window.allStories ? window.allStories() : (window.CURA_STORIES || []);
    const s = all.find(x => x.contested) || all[0];
    return s ? '#story/' + s.id : null;
  }
  return '#' + view;
}

function GuidedTour() {
  const [active, setActive] = React.useState(false);
  const [i, setI] = React.useState(0);
  const [rect, setRect] = React.useState(null);
  const [pos, setPos] = React.useState(null);
  const [showSay, setShowSay] = React.useState(false);
  const cardRef = React.useRef(null);
  const step = TOUR[i] || {};
  const lastStep = i === TOUR.length - 1;

  const start = React.useCallback((n) => { setI(n || 0); setRect(null); setActive(true); }, []);
  const end = React.useCallback(() => setActive(false), []);
  const next = React.useCallback(() => setI(n => (n < TOUR.length - 1 ? n + 1 : (setActive(false), n))), []);
  const prev = React.useCallback(() => setI(n => Math.max(0, n - 1)), []);

  // Launch triggers: custom event, ?tour= URL param, console helper.
  React.useEffect(() => {
    window.curaStartTour = start;
    const onStart = (e) => start((e.detail && e.detail.step) || 0);
    window.addEventListener('cura-start-tour', onStart);
    const params = new URLSearchParams(window.location.search);
    let t;
    if (params.get('tour') === '1' || params.get('tour') === 'clean') {
      t = setTimeout(() => start(0), 800);  // let the first edition settle
    }
    return () => { window.removeEventListener('cura-start-tour', onStart); if (t) clearTimeout(t); };
  }, [start]);

  // Keyboard: "t" starts; arrows / space / enter drive; Esc exits.
  React.useEffect(() => {
    const onKey = (e) => {
      const el = document.activeElement;
      const typing = el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable);
      if (!active) {
        if (!typing && (e.key === 't' || e.key === 'T')) { e.preventDefault(); start(0); }
        return;
      }
      if (e.key === 'Escape') { e.preventDefault(); end(); }
      else if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'Enter') { e.preventDefault(); next(); }
      else if (e.key === 'ArrowLeft') { e.preventDefault(); prev(); }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [active, start, end, next, prev]);

  // On each step: navigate to its view, then track the target's position
  // through the view-rise animation and the scroll-into-view.
  React.useEffect(() => {
    if (!active) return undefined;
    const hash = resolveHash(step.view);
    if (hash && window.location.hash !== hash) window.location.hash = hash;

    const measure = () => {
      const el = step.target ? document.querySelector(step.target) : null;
      setRect(el ? el.getBoundingClientRect() : null);
      return el;
    };
    let scrolled = false;
    const passes = [70, 300, 600, 1000].map(ms => setTimeout(() => {
      const el = measure();
      if (el && !scrolled) {
        scrolled = true;
        try { el.scrollIntoView({ block: 'center', behavior: 'smooth' }); } catch (e) { el.scrollIntoView(); }
      }
    }, ms));
    const onMove = () => measure();
    window.addEventListener('resize', onMove);
    window.addEventListener('scroll', onMove, true);  // capture: catches .scroll-area
    return () => {
      passes.forEach(clearTimeout);
      window.removeEventListener('resize', onMove);
      window.removeEventListener('scroll', onMove, true);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, i]);

  // Place the card beside the spotlight, never on top of it. Try below, above,
  // then the sides; when the target fills the viewport (e.g. the whole hero
  // story) there is no clear spot, so pin to the calm bottom-right corner
  // rather than dropping the card onto the headline. Centred with no target.
  React.useLayoutEffect(() => {
    if (!active) return;
    const card = cardRef.current;
    if (!card) return;
    const cw = card.offsetWidth, ch = card.offsetHeight;
    const vw = window.innerWidth, vh = window.innerHeight, M = 16, GAP = 14;
    if (!rect) { setPos({ top: Math.round((vh - ch) / 2), left: Math.round((vw - cw) / 2) }); return; }
    const clampLeft = (l) => Math.max(M, Math.min(l, vw - cw - M));
    const clampTop = (t) => Math.max(M, Math.min(t, vh - ch - M));
    const below = rect.bottom + GAP, above = rect.top - GAP - ch;
    const right = rect.right + GAP, leftOf = rect.left - GAP - cw;
    let p;
    if (below + ch <= vh - M)      p = { top: below, left: clampLeft(rect.left) };
    else if (above >= M)           p = { top: above, left: clampLeft(rect.left) };
    else if (right + cw <= vw - M) p = { top: clampTop(rect.top), left: right };
    else if (leftOf >= M)          p = { top: clampTop(rect.top), left: leftOf };
    else                           p = { top: vh - ch - M, left: vw - cw - M };
    setPos({ top: Math.round(p.top), left: Math.round(p.left) });
  }, [rect, i, active, showSay]);

  if (!active) return null;

  const PAD = 8;
  const primaryBtn = { background: 'var(--ink)', color: 'var(--paper)', border: 'none', borderRadius: 6, padding: '8px 16px', fontSize: 13, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit' };
  const secondaryBtn = { background: 'transparent', color: 'var(--ink)', border: '1px solid var(--paper-rule)', borderRadius: 6, padding: '8px 14px', fontSize: 13, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit' };

  return (
    <React.Fragment>
      {/* Dim + spotlight. pointer-events:none so the app stays operable. */}
      {rect ? (
        <div style={{
          position: 'fixed', pointerEvents: 'none', zIndex: TOUR_Z,
          top: rect.top - PAD, left: rect.left - PAD,
          width: rect.width + PAD * 2, height: rect.height + PAD * 2,
          borderRadius: 10, boxShadow: '0 0 0 9999px rgba(14,26,43,0.55)',
          outline: '2px solid var(--accent)', outlineOffset: 0,
          transition: 'all .3s cubic-bezier(.22,.7,.25,1)',
        }} />
      ) : (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(14,26,43,0.55)', pointerEvents: 'none', zIndex: TOUR_Z }} />
      )}

      {/* The coach card */}
      <div ref={cardRef} style={{
        position: 'fixed', zIndex: TOUR_Z + 2,
        top: pos ? pos.top : -9999, left: pos ? pos.left : -9999,
        width: 340, maxWidth: '92vw',
        background: 'var(--paper)', color: 'var(--ink)',
        border: '1px solid var(--rule)', borderRadius: 10,
        boxShadow: '0 24px 60px rgba(14,26,43,0.35)', padding: '18px 20px',
        fontFamily: 'Inter, system-ui, sans-serif',
        opacity: pos ? 1 : 0, transition: 'top .3s cubic-bezier(.22,.7,.25,1), left .3s cubic-bezier(.22,.7,.25,1), opacity .2s',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
          <span className="mono" style={{ fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', color: 'var(--accent)' }}>
            Guided tour · {i + 1}/{TOUR.length}
          </span>
          <button onClick={end} aria-label="End tour" style={{ background: 'none', border: 'none', color: 'var(--ink-muted)', fontSize: 15, cursor: 'pointer', lineHeight: 1, padding: 4 }}>✕</button>
        </div>

        <div className="serif" style={{ fontSize: 20, fontWeight: 600, lineHeight: 1.15, margin: '0 0 6px' }}>{step.title}</div>
        <div style={{ fontSize: 13.5, lineHeight: 1.55, color: 'var(--ink-soft)' }}>{step.body}</div>

        {step.say && showSay && (
          <div style={{ marginTop: 12, padding: '10px 12px', background: 'var(--paper-2)', borderLeft: '2px solid var(--accent)', borderRadius: 4, fontSize: 13, fontStyle: 'italic', lineHeight: 1.5, color: 'var(--ink)' }}>
            🎙 “{step.say}”
          </div>
        )}

        <div style={{ height: 3, background: 'var(--paper-3)', borderRadius: 3, overflow: 'hidden', margin: '14px 0' }}>
          <div style={{ height: '100%', width: (((i + 1) / TOUR.length) * 100) + '%', background: 'var(--accent)', transition: 'width .4s ease' }} />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {step.say ? (
            <button onClick={() => setShowSay(s => !s)} style={{ background: 'none', border: 'none', color: 'var(--ink-muted)', fontSize: 10, letterSpacing: '0.16em', textTransform: 'uppercase', cursor: 'pointer', padding: 0, marginRight: 'auto' }}>
              {showSay ? 'hide script' : '🎙 script'}
            </button>
          ) : <span style={{ marginRight: 'auto' }} />}
          <button onClick={prev} disabled={i === 0} style={{ ...secondaryBtn, opacity: i === 0 ? 0.4 : 1, pointerEvents: i === 0 ? 'none' : 'auto' }}>Back</button>
          <button onClick={next} style={primaryBtn}>{lastStep ? 'Done' : 'Next'}</button>
        </div>
      </div>
    </React.Fragment>
  );
}

(function mountTour() {
  const id = 'cura-tour-root';
  let host = document.getElementById(id);
  if (!host) { host = document.createElement('div'); host.id = id; document.body.appendChild(host); }
  ReactDOM.createRoot(host).render(<GuidedTour />);
})();
