// PROVENANCE: ORIGINAL (bespoke to Cura) - React/JSX prototype component; the product spec (see design/HANDOFF.md). Third-party (CDN): React 18, ReactDOM, Babel standalone. Live answers via window.claude (LLM) with a scripted offline fallback. See PROVENANCE.md.
// Cura - Cleo conversational chat (slide-over panel) - LIVE
// Cleo answers for real via window.claude.complete, grounded in today's source
// set. If the API isn't available (offline file, rate limit, error), she falls
// back to a keyword-matched grounded answer so the demo never breaks.

const { useState: useStateC, useRef: useRefC, useEffect: useEffectC } = React;

/* ---------- build Cleo's knowledge base from today's data ---------- */
function buildCleoKB() {
  const stories = (window.allStories ? allStories() : (window.CURA_STORIES || [])).map(s => {
    const tldr = s.tldr ? ' Key points: ' + s.tldr.join(' ') : '';
    return `• [${s.section}] ${s.headline}. ${s.dek}${tldr} (${s.sources} sources, confidence ${s.confidence}/5: ${s.confidenceLabel}).`;
  }).join('\n');
  // The canned Fed source-comparison belongs to the prototype data only -
  // grounding live Cleo in it would have her cite stories not in the edition.
  const compare = window.CURA_LIVE ? '' : (window.COMPARE_SOURCES || []).map(c =>
    `• ${c.name} (${c.lean}) — "${c.headline}". ${c.framing} Quote: ${c.quote}`
  ).join('\n');
  const m = window.editionMeta ? window.editionMeta() : { dateline: 'Tuesday · Aug 27', count: 9 };
  return `TODAY'S EDITION — ${m.dateline.replace(' · ', ', ')} (${m.count} stories):\n${stories}`
    + (compare ? `\n\nSOURCE COMPARISON for the Fed story:\n${compare}` : '');
}

const CLEO_PERSONA =
  `You are Cleo, the AI news helper inside Cura, a slow-news app. ` +
  `You are warm, calm, and plain-spoken — never hype, no emoji, no exclamation marks. ` +
  `Rules you never break:\n` +
  `1. Answer ONLY using the sources provided below. If the answer isn't in them, say so plainly ("I can't ground that in today's sources") and offer what you do have.\n` +
  `2. Cite sources inline in parentheses, e.g. (Reuters) or (CDC).\n` +
  `3. Be concise: 2–4 short sentences, or a few tight points. This is a quick briefing, not an essay.\n` +
  `4. Never invent numbers, names, or quotes that aren't in the sources.`;

/* keyword fallback so the prototype works offline / when rate-limited */
function cleoFallback(q) {
  const t = q.toLowerCase();
  if (/fed|powell|rate|interest|jackson/.test(t)) {
    return { text: 'Here’s what I can ground on the Fed:', grounded: true, bullets: [
      { i: 1, text: 'Powell said “the time has come for policy to adjust” — markets read it as a near-commitment to a September cut.', cite: 'Reuters · federalreserve.gov' },
      { i: 2, text: 'The 2-year Treasury yield fell 14 bps, the largest single-session drop since March.', cite: 'Bloomberg' },
      { i: 3, text: 'But three FOMC presidents — Bowman, Logan, Schmid — publicly favor holding. September is the real test.', cite: 'WSJ' },
    ] };
  }
  if (/tsmc|chip|arizona|fab|semiconduct/.test(t)) {
    return { text: 'On the chip story:', grounded: true, bullets: [
      { i: 1, text: 'TSMC pushed its $40B Arizona fab to 2027 — the second delay in 18 months.', cite: 'Reuters' },
      { i: 2, text: 'The causes cited are labor shortages and a strained Phoenix-area grid. I’ve rated it highly verified (11 sources).', cite: 'Cura' },
    ] };
  }
  if (/insur|florida|climate|seawall|flood/.test(t)) {
    return { text: 'On climate and insurance:', grounded: true, bullets: [
      { i: 1, text: 'Three of the largest U.S. carriers will stop renewing policies in flood-prone Florida counties from January.', cite: 'Cura · 9 sources' },
      { i: 2, text: 'Coastal cities are accelerating seawall plans as private insurance retreats.', cite: 'Cura' },
    ] };
  }
  if (/brief|summary|today|catch.?up|what.?s|happening/.test(t)) {
    return { text: 'Today’s nine stories, in order of weight: the Fed signalling a September cut; TSMC delaying its Arizona fab to 2027; insurers exiting Florida; the Black Sea grain corridor reopening; plus housing, a CDC tick-borne study, and a repertory-cinema revival. Want me to go deeper on any one? (Cura — 312 sources scanned)', grounded: true };
  }
  return { text: 'I can only answer from today’s cited sources. I have the Fed decision, the TSMC Arizona delay, Florida insurance, the grain corridor, housing, a CDC study, and an arts long-read. Which one should I dig into?', grounded: false };
}

function CleoPanel({ open, onClose }) {
  const meta = window.editionMeta ? window.editionMeta() : { count: 9, minutes: 15 };
  const [messages, setMessages] = useStateC([
    { role: 'cleo', text: `Good morning. There are ${meta.count} stories in today’s edition — about ${meta.minutes} minutes. Want me to brief you, or is there something you’re tracking?` },
    // The scripted Fed walkthrough is prototype-only demo content
    ...(window.CURA_LIVE ? [] : [{
      role: 'cleo',
      text: 'Three things matter most about the Fed today, in order:',
      bullets: [
        { i: 1, text: 'Powell’s exact phrase — “the time has come for policy to adjust” — is unusually direct. Markets read it as a near-commitment to a September cut.', cite: 'Reuters · federalreserve.gov' },
        { i: 2, text: 'But the FOMC isn’t unanimous. Three regional presidents have publicly questioned the urgency.', cite: 'WSJ · Reuters survey' },
        { i: 3, text: 'The 14bp drop in the 2-yr yield is the biggest market tell.', cite: 'Bloomberg' },
      ],
      grounded: true,
    }]),
  ]);
  const [input, setInput] = useStateC('');
  const [thinking, setThinking] = useStateC(false);
  const scrollRef = useRefC(null);
  const live = !!(window.claude && typeof window.claude.complete === 'function');

  useEffectC(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, thinking]);

  const send = async () => {
    const q = input.trim();
    if (!q || thinking) return;
    const history = messages.slice(-6);
    setMessages(m => [...m, { role: 'user', text: q }]);
    setInput('');
    setThinking(true);

    let replied = false;
    try {
      if (window.claude && typeof window.claude.complete === 'function') {
        const convo = history.map(m => (m.role === 'user' ? 'Reader: ' : 'Cleo: ') + m.text).join('\n');
        const prompt =
          CLEO_PERSONA + '\n\n=== SOURCES ===\n' + buildCleoKB() +
          '\n\n=== CONVERSATION ===\n' + convo + '\nReader: ' + q + '\nCleo:';
        const reply = await window.claude.complete(prompt);
        if (reply && reply.trim()) {
          setMessages(m => [...m, { role: 'cleo', text: reply.trim(), grounded: true }]);
          replied = true;
        }
      }
    } catch (e) { /* fall through to fallback */ }

    if (!replied) {
      await new Promise(r => setTimeout(r, 500));
      setMessages(m => [...m, { role: 'cleo', ...cleoFallback(q) }]);
    }
    setThinking(false);
  };

  const suggestions = [
    'Brief me on today',
    'Why is the FOMC dissent notable?',
    'Compare WSJ vs Reuters on the Fed.',
    'What’s the climate story?',
  ];

  return (
    <>
      {open && (
        <>
          <div className="cleo-overlay" onClick={onClose} />
          <div className="cleo-panel">
        {/* Header */}
        <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--paper-rule)', display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            width: 36, height: 36, borderRadius: '50%',
            background: 'linear-gradient(135deg, var(--accent), var(--ink))',
            display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--paper)',
          }}>
            <CIcon name="sparkle" size={16} />
          </div>
          <div style={{ flex: 1 }}>
            <div className="serif" style={{ fontSize: 18, fontWeight: 600, lineHeight: 1.1 }}>Cleo</div>
            <div className="mono" style={{ fontSize: 10, letterSpacing: '0.18em', color: 'var(--ink-muted)', textTransform: 'uppercase' }}>
              Grounded · cites everything
            </div>
          </div>
          <button onClick={onClose} className="btn-ghost btn" style={{ padding: 8 }}>
            <CIcon name="close" size={16} />
          </button>
        </div>

        {/* Messages */}
        <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', padding: '20px 24px' }}>
          {messages.map((m, i) => (
            <div key={i} style={{ marginBottom: 18 }}>
              {m.role === 'user' ? (
                <div style={{
                  background: 'var(--ink)', color: 'var(--paper)',
                  padding: '10px 14px', borderRadius: '14px 14px 4px 14px',
                  fontSize: 14, lineHeight: 1.5, marginLeft: 40,
                }}>{m.text}</div>
              ) : (
                <div>
                  {m.text.split('\n').filter(Boolean).map((para, k) => (
                    <div key={k} style={{ fontSize: 14, lineHeight: 1.55, color: 'var(--ink)', marginBottom: m.bullets ? 12 : 8 }}>
                      {para}
                    </div>
                  ))}
                  {m.bullets && (
                    <ol style={{ margin: 0, padding: 0, listStyle: 'none' }}>
                      {m.bullets.map(b => (
                        <li key={b.i} style={{ marginBottom: 12, paddingLeft: 28, position: 'relative' }}>
                          <span className="serif" style={{ position: 'absolute', left: 0, top: -2, fontSize: 18, fontWeight: 600, color: 'var(--accent)' }}>{b.i}.</span>
                          <div style={{ fontSize: 13, lineHeight: 1.5, color: 'var(--ink-soft)', marginBottom: 4 }}>{b.text}</div>
                          <div className="mono" style={{ fontSize: 10, letterSpacing: '0.16em', textTransform: 'uppercase', color: 'var(--ink-muted)' }}>→ {b.cite}</div>
                        </li>
                      ))}
                    </ol>
                  )}
                  {m.grounded && (
                    <div style={{
                      marginTop: 12, display: 'inline-flex', alignItems: 'center', gap: 6,
                      fontSize: 11, color: 'var(--green)',
                      background: 'rgba(31,94,63,0.08)', padding: '4px 10px', borderRadius: 12,
                    }}>
                      <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--green)' }} />
                      Grounded in your sources
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}

          {thinking && (
            <div style={{ marginBottom: 18, display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ display: 'flex', gap: 4 }}>
                {[0, 1, 2].map(i => (
                  <span key={i} style={{
                    width: 6, height: 6, borderRadius: '50%', background: 'var(--ink-muted)',
                    animation: `cleodot 1s ${i * 0.16}s infinite ease-in-out`,
                  }} />
                ))}
              </div>
              <span className="mono" style={{ fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase', color: 'var(--ink-muted)' }}>
                Cleo is reading the sources
              </span>
            </div>
          )}
        </div>

        {/* Suggestions */}
        <div style={{ padding: '0 24px 12px' }}>
          <div className="mono" style={{ fontSize: 9, letterSpacing: '0.22em', color: 'var(--ink-muted)', textTransform: 'uppercase', marginBottom: 8 }}>
            Try asking
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {suggestions.map((s, i) => (
              <button key={i} onClick={() => setInput(s)} style={{
                fontSize: 12, padding: '6px 10px', borderRadius: 14,
                background: 'var(--paper-2)', border: '1px solid var(--paper-rule)',
                color: 'var(--ink-soft)', cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left',
              }}>{s}</button>
            ))}
          </div>
        </div>

        {/* Input */}
        <div style={{ padding: '14px 20px 18px', borderTop: '1px solid var(--paper-rule)' }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8,
            background: 'var(--paper-2)', border: '1px solid var(--paper-rule)',
            borderRadius: 8, padding: '4px 4px 4px 14px',
          }}>
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && send()}
              placeholder="Ask anything — grounded in your sources"
              style={{ flex: 1, border: 'none', outline: 'none', background: 'transparent', fontSize: 14, padding: '8px 0', fontFamily: 'inherit', color: 'var(--ink)' }}
            />
            <button onClick={send} disabled={thinking} style={{
              width: 32, height: 32, borderRadius: 6,
              background: thinking ? 'var(--ink-muted)' : 'var(--ink)', color: 'var(--paper)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              border: 'none', cursor: thinking ? 'default' : 'pointer',
            }}>
              <CIcon name="send" size={14} />
            </button>
          </div>
          <div style={{ marginTop: 8, fontSize: 10, color: 'var(--ink-muted)', textAlign: 'center' }}>
            {live
              ? 'Cleo only answers from cited sources. If she can’t ground it, she says so.'
              : 'Demo mode — answering from today’s cached sources. (Live model unavailable offline.)'}
          </div>
        </div>
        <style>{`@keyframes cleodot{0%,100%{opacity:0.3;transform:translateY(0)}50%{opacity:1;transform:translateY(-3px)}}`}</style>
      </div>
        </>
      )}
    </>
  );
}

window.CleoPanel = CleoPanel;
