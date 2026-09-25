// PROVENANCE: ORIGINAL (bespoke to Cura) - React/JSX prototype component; the product spec (see design/HANDOFF.md). Third-party (CDN): React 18, ReactDOM, Babel standalone. See PROVENANCE.md.
// Cura - Saved view, Settings (personalization), and the Search command palette.

const { useState: useStateScr, useEffect: useEffectScr, useRef: useRefScr } = React;

/* ─── SAVED ───────────────────────────────────────────── */
function SavedView({ openStory }) {
  const saved = window.useSaved();
  const stories = saved.ids.map(id => (window.allStories ? allStories() : (window.CURA_STORIES || [])).find(s => s.id === id)).filter(Boolean);

  return (
    <div className="scroll-area">
      <div style={{ maxWidth: 820, margin: '0 auto', padding: '40px 48px 80px' }}>
        <SectionTag>Saved · {stories.length} {stories.length === 1 ? 'story' : 'stories'}</SectionTag>
        <h1 className="serif" style={{ fontSize: 40, lineHeight: 1.05, fontWeight: 600, letterSpacing: '-0.01em', margin: '0 0 32px' }}>
          Your reading list.
        </h1>

        {stories.length === 0 ? (
          <div style={{ padding: '60px 0', borderTop: '1px solid var(--paper-rule)', textAlign: 'center', color: 'var(--ink-muted)' }}>
            <div style={{ display: 'inline-flex', width: 48, height: 48, borderRadius: 24, background: 'var(--paper-2)', alignItems: 'center', justifyContent: 'center', marginBottom: 16 }}>
              <CIcon name="bookmark" size={20} color="var(--ink-muted)" />
            </div>
            <h2 className="serif" style={{ fontSize: 24, color: 'var(--ink)', margin: '0 0 8px' }}>Nothing saved yet.</h2>
            <p style={{ fontSize: 14, lineHeight: 1.5, maxWidth: '40ch', margin: '0 auto' }}>
              Tap the bookmark on any story while you read and it’ll wait for you here — across briefings, the newspaper, and the feed.
            </p>
          </div>
        ) : (
          <div style={{ borderTop: '1px solid var(--paper-rule)' }}>
            {stories.map(s => (
              <article key={s.id} style={{
                padding: '20px 0', borderBottom: '1px solid var(--paper-rule)',
                display: 'grid', gridTemplateColumns: '76px 1fr auto', gap: 20, alignItems: 'baseline',
              }}>
                <div className="mono" style={{ fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', color: 'var(--ink-muted)' }}>§ {s.section}</div>
                <div className="story-card" onClick={() => openStory(s.id)}>
                  <h3 className="serif" style={{ fontSize: 21, lineHeight: 1.18, fontWeight: 600, margin: '0 0 6px' }}>{s.headline}</h3>
                  <div style={{ fontSize: 12, color: 'var(--ink-muted)', display: 'flex', gap: 12, alignItems: 'center' }}>
                    <ConfBar level={s.confidence} label={s.confidenceLabel} />
                    <span>{s.sources} sources · {s.minutes} min</span>
                  </div>
                </div>
                <button className="btn btn-ghost" title="Remove from saved" onClick={() => window.CuraStore.toggleSaved(s.id)} style={{ padding: 8 }}>
                  <CIcon name="bookmark-fill" size={16} color="var(--accent)" />
                </button>
              </article>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── SETTINGS / PERSONALIZATION ──────────────────────── */
function Toggle({ on, onClick }) {
  return (
    <button onClick={onClick} aria-pressed={on} style={{
      width: 42, height: 24, borderRadius: 12, border: 'none', cursor: 'pointer', position: 'relative',
      background: on ? 'var(--green)' : 'var(--paper-3)', transition: 'background 0.15s', flexShrink: 0,
    }}>
      <span style={{ position: 'absolute', top: 2, left: on ? 20 : 2, width: 20, height: 20, borderRadius: '50%', background: 'var(--paper)', transition: 'left 0.15s', boxShadow: '0 1px 3px rgba(0,0,0,0.2)' }} />
    </button>
  );
}

function Chip({ on, children, onClick }) {
  return (
    <button onClick={onClick} style={{
      fontSize: 13, padding: '7px 14px', borderRadius: 18, cursor: 'pointer', fontFamily: 'inherit',
      border: '1px solid ' + (on ? 'var(--ink)' : 'var(--paper-rule)'),
      background: on ? 'var(--ink)' : 'transparent', color: on ? 'var(--paper)' : 'var(--ink-soft)',
      transition: 'all 0.12s',
    }}>{children}</button>
  );
}

function SettingsView() {
  const { signals, set } = window.useSignals();
  const Row = ({ label, hint, children }) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: 20, padding: '16px 0', borderBottom: '1px solid var(--paper-rule)' }}>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 15, fontWeight: 500, color: 'var(--ink)' }}>{label}</div>
        {hint && <div style={{ fontSize: 12, color: 'var(--ink-muted)', marginTop: 3, lineHeight: 1.4 }}>{hint}</div>}
      </div>
      {children}
    </div>
  );

  return (
    <div className="scroll-area">
      <div style={{ maxWidth: 720, margin: '0 auto', padding: '40px 48px 80px' }}>
        <SectionTag>Settings · personalization</SectionTag>
        <h1 className="serif" style={{ fontSize: 40, lineHeight: 1.05, fontWeight: 600, letterSpacing: '-0.01em', margin: '0 0 8px' }}>
          Tune your signals.
        </h1>
        <p style={{ fontSize: 15, color: 'var(--ink-soft)', margin: '0 0 36px', maxWidth: '56ch' }}>
          Cura ranks by independent confirmation, not engagement. These are the inputs Cleo weighs when she builds your edition — change them and tomorrow’s set shifts.
        </p>

        {/* Topics */}
        <div className="mono" style={{ fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', color: 'var(--ink-muted)', marginBottom: 12 }}>Topics you follow</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
          {Object.keys(signals.topics).map(t => (
            <Chip key={t} on={signals.topics[t]} onClick={() => set({ topics: Object.assign({}, signals.topics, { [t]: !signals.topics[t] }) })}>{t}</Chip>
          ))}
        </div>
        {/* Personalisation loop: these topics can drive the pipeline now,
            not just re-rank the front page client-side */}
        {window.curaRequestBriefing && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 32 }}>
            <button
              className="btn"
              onClick={() => {
                const kws = signals.keywords || [];
                const followed = Object.keys(signals.topics).filter(t => signals.topics[t]);
                window.curaRequestBriefing(kws.length ? kws : followed);
                window.location.hash = '#read';
              }}
            >Re-curate my edition from these topics</button>
            <span style={{ fontSize: 11, color: 'var(--ink-muted)' }}>
              re-runs the full pipeline on demand · ~1–2 min
            </span>
          </div>
        )}

        {/* The reader's own words, from onboarding — editable here */}
        <div className="mono" style={{ fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', color: 'var(--ink-muted)', marginBottom: 12 }}>Your brief to Cleo</div>
        <textarea
          defaultValue={signals.interests || ''}
          onBlur={(e) => set({ interests: e.target.value.trim() })}
          rows={2}
          placeholder="In your own words, what should Cura cover for you?"
          style={{
            width: '100%', boxSizing: 'border-box', resize: 'vertical',
            fontFamily: 'inherit', fontSize: 13.5, lineHeight: 1.5,
            padding: '10px 12px', borderRadius: 4,
            border: '1px solid var(--paper-rule)', background: 'var(--paper-2)',
            color: 'var(--ink)', outline: 'none', marginBottom: 8,
          }}
        />
        {(signals.keywords || []).length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
            {signals.keywords.map(k => <span key={k} className="src-chip">{k}</span>)}
          </div>
        )}
        <div style={{ fontSize: 11, color: 'var(--ink-muted)', marginBottom: 32 }}>
          Parsed once during the welcome — <a href="#welcome" style={{ color: 'var(--accent)' }}>redo the welcome</a> to re-parse with Cleo.
        </div>

        {/* Sources */}
        <div className="mono" style={{ fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', color: 'var(--ink-muted)', marginBottom: 12 }}>Trusted sources</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 32 }}>
          {Object.keys(signals.sources).map(t => (
            <Chip key={t} on={signals.sources[t]} onClick={() => set({ sources: Object.assign({}, signals.sources, { [t]: !signals.sources[t] }) })}>{t}</Chip>
          ))}
        </div>

        {/* Cadence */}
        <div className="mono" style={{ fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', color: 'var(--ink-muted)', marginBottom: 12 }}>Edition cadence</div>
        <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
          {[['realtime', 'As it breaks'], ['daily', 'Once daily'], ['weekly', 'Weekly digest']].map(([v, l]) => (
            <Chip key={v} on={signals.cadence === v} onClick={() => set({ cadence: v })}>{l}</Chip>
          ))}
        </div>
        <div style={{ fontSize: 12, color: 'var(--ink-muted)', marginBottom: 32, lineHeight: 1.5 }}>
          “Slow news” works best at <strong>once daily</strong> — one considered edition rather than an endless stream.
        </div>

        {/* Behaviour toggles */}
        <div className="mono" style={{ fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', color: 'var(--ink-muted)', marginBottom: 4 }}>Behaviour</div>
        <Row label="Default format" hint="Where Cura opens each morning.">
          <div style={{ display: 'flex', gap: 6 }}>
            {[['read', 'Read'], ['listen', 'Listen'], ['experience', 'Today']].map(([v, l]) => (
              <Chip key={v} on={signals.defaultFormat === v} onClick={() => set({ defaultFormat: v })}>{l}</Chip>
            ))}
          </div>
        </Row>
        <Row label="Autoplay the daily brief" hint="Start Cleo’s narration when you open Listen.">
          <Toggle on={signals.autoplayBrief} onClick={() => set({ autoplayBrief: !signals.autoplayBrief })} />
        </Row>
        <Row label="Show confidence ratings" hint="Display source-count confidence bars on every story.">
          <Toggle on={signals.showConfidence} onClick={() => set({ showConfidence: !signals.showConfidence })} />
        </Row>
      </div>
    </div>
  );
}

/* ─── SEARCH COMMAND PALETTE ──────────────────────────── */
function SearchPalette({ open, onClose, openStory, goView }) {
  const [q, setQ] = useStateScr('');
  const inputRef = useRefScr(null);
  useEffectScr(() => { if (open && inputRef.current) inputRef.current.focus(); if (!open) setQ(''); }, [open]);
  useEffectScr(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    if (open) window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;
  const stories = window.allStories ? allStories() : (window.CURA_STORIES || []);
  const ql = q.trim().toLowerCase();
  const results = ql
    ? stories.filter(s => (s.headline + ' ' + s.section + ' ' + (s.dek || '')).toLowerCase().includes(ql)).slice(0, 7)
    : [];
  const topics = ['Economy', 'Technology', 'Climate', 'World', 'Politics', 'Health'];

  const go = (s) => { onClose(); openStory(s.id); };

  return (
    <div onClick={onClose} style={{ position: 'absolute', inset: 0, background: 'rgba(14,26,43,0.35)', zIndex: 70, display: 'flex', alignItems: 'flex-start', justifyContent: 'center', paddingTop: 90 }}>
      <div onClick={e => e.stopPropagation()} style={{ width: 600, maxWidth: '90%', background: 'var(--paper)', borderRadius: 10, boxShadow: '0 24px 70px rgba(14,26,43,0.35)', overflow: 'hidden', border: '1px solid var(--paper-rule)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '16px 18px', borderBottom: '1px solid var(--paper-rule)' }}>
          <CIcon name="search" size={18} color="var(--ink-muted)" />
          <input ref={inputRef} value={q} onChange={e => setQ(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && results[0]) go(results[0]); }}
            placeholder="Search stories, topics, sources…"
            style={{ flex: 1, border: 'none', outline: 'none', background: 'transparent', fontSize: 17, fontFamily: 'inherit', color: 'var(--ink)' }} />
          <span className="mono" style={{ fontSize: 11, color: 'var(--ink-muted)', border: '1px solid var(--paper-rule)', borderRadius: 4, padding: '2px 6px' }}>ESC</span>
        </div>

        <div style={{ maxHeight: 380, overflowY: 'auto' }}>
          {!ql && (
            <div style={{ padding: '16px 18px' }}>
              <div className="mono" style={{ fontSize: 9, letterSpacing: '0.22em', textTransform: 'uppercase', color: 'var(--ink-muted)', marginBottom: 10 }}>Jump to a topic</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {topics.map(t => {
                  const first = stories.find(s => s.section === t);
                  return <button key={t} onClick={() => first && go(first)} style={{ fontSize: 13, padding: '7px 12px', borderRadius: 16, border: '1px solid var(--paper-rule)', background: 'var(--paper-2)', color: 'var(--ink-soft)', cursor: 'pointer', fontFamily: 'inherit' }}>{t}</button>;
                })}
              </div>
            </div>
          )}
          {ql && results.length === 0 && (
            <div style={{ padding: '28px 18px', textAlign: 'center', color: 'var(--ink-muted)', fontSize: 14 }}>
              No stories match “{q}”. Cleo only searches today’s vetted edition.
            </div>
          )}
          {results.map(s => (
            <div key={s.id} onClick={() => go(s)} style={{ padding: '14px 18px', borderTop: '1px solid var(--paper-rule)', cursor: 'pointer', display: 'flex', gap: 14, alignItems: 'baseline' }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--paper-2)'} onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
              <span className="mono" style={{ fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', color: 'var(--accent)', minWidth: 84 }}>§ {s.section}</span>
              <div style={{ flex: 1 }}>
                <div className="serif" style={{ fontSize: 16, fontWeight: 600, lineHeight: 1.2, marginBottom: 2 }}>{s.headline}</div>
                <div style={{ fontSize: 12, color: 'var(--ink-muted)' }}>{s.sources} sources · {s.minutes} min</div>
              </div>
              <CIcon name="arrow-right" size={15} color="var(--ink-muted)" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ─── ONBOARDING - the welcome gate (#welcome) ────────── */
// First visit: personalization comes before the product. Pick sections,
// and/or brief Cleo in your own words - parsed into followed topics +
// queryable keywords with one click-gated model call (keyword matching
// when no model is available). Re-openable any time via #welcome.
function OnboardingGate({ onClose }) {
  const ALL_TOPICS = Object.keys(window.CuraStore.defaultSignals.topics);
  const current = window.CuraStore.getSignals();
  const [picked, setPicked] = useStateScr(() => {
    const init = {};
    ALL_TOPICS.forEach(t => { init[t] = !!current.topics[t]; });
    return init;
  });
  const [text, setText] = useStateScr(current.interests || '');
  const [busy, setBusy] = useStateScr(false);
  const [recurate, setRecurate] = useStateScr(false);
  const aiLive = !!window.claude;
  const canRecurate = !!window.curaRequestBriefing && !!window.CURA_LIVE;

  const fallbackParse = (brief) => ({
    topics: ALL_TOPICS.filter(t => brief.toLowerCase().includes(t.toLowerCase())),
    keywords: brief.split(/,|;|\band\b/i).map(s => s.trim())
      .filter(s => s.length > 2 && s.length <= 40).slice(0, 5),
  });

  const aiParse = async (brief) => {
    const prompt = 'You are configuring a news app. The available sections are: '
      + ALL_TOPICS.join(', ') + '. The reader wrote this brief about what they '
      + 'want covered:\n\n"' + brief + '"\n\nReply with ONLY a JSON object, no '
      + 'prose: {"topics": [matching sections from the list only], '
      + '"keywords": [2-6 short search phrases capturing their specific interests]}';
    const raw = await window.claude.complete(prompt);
    const parsed = JSON.parse(raw.replace(/```json|```/g, '').trim());
    return {
      topics: (parsed.topics || []).filter(t => ALL_TOPICS.indexOf(t) >= 0),
      keywords: (parsed.keywords || []).map(String).slice(0, 6),
    };
  };

  const start = async () => {
    setBusy(true);
    const topics = Object.assign({}, picked);
    let keywords = [];
    const brief = text.trim();
    if (brief) {
      let parsed;
      try { parsed = aiLive ? await aiParse(brief) : fallbackParse(brief); }
      catch (e) { parsed = fallbackParse(brief); }
      parsed.topics.forEach(t => { topics[t] = true; });
      keywords = parsed.keywords;
    }
    window.CuraStore.setSignal({ topics, interests: brief, keywords });
    try { localStorage.setItem('cura.onboarded', '1'); } catch (e) {}
    if (recurate && canRecurate) {
      const followed = ALL_TOPICS.filter(t => topics[t]);
      window.curaRequestBriefing(keywords.length ? keywords : followed);
    }
    onClose();
  };

  const skip = () => {
    try { localStorage.setItem('cura.onboarded', '1'); } catch (e) {}
    onClose();
  };

  const monoLabel = (s) => (
    <div className="mono" style={{
      fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase',
      color: 'var(--ink-muted)', margin: '20px 0 10px',
    }}>{s}</div>
  );

  return (
    <div style={{
      position: 'absolute', inset: 0, zIndex: 90,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'rgba(14,26,43,0.35)', backdropFilter: 'blur(10px)',
      WebkitBackdropFilter: 'blur(10px)',
    }}>
      <div style={{
        width: 600, maxHeight: '88%', overflowY: 'auto',
        background: 'var(--paper)', border: '1px solid var(--paper-rule)',
        borderRadius: 6, boxShadow: '0 36px 90px rgba(14,26,43,0.45)',
        padding: '34px 40px 28px',
      }}>
        <div className="mono" style={{
          fontSize: 10, letterSpacing: '0.26em', textTransform: 'uppercase',
          color: 'var(--accent)', marginBottom: 10,
        }}>Welcome to Cura</div>
        <h1 className="serif" style={{ fontSize: 34, lineHeight: 1.05, fontWeight: 600, letterSpacing: '-0.01em', margin: '0 0 8px' }}>
          First, make it yours.
        </h1>
        <p style={{ fontSize: 13.5, lineHeight: 1.55, color: 'var(--ink-soft)', margin: 0 }}>
          Cura ranks by independent confirmation, not engagement — but <em>what</em> it
          ranks for you starts here. Pick sections, or just tell Cleo what you care about.
        </p>

        {monoLabel('Sections you follow')}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {ALL_TOPICS.map(t => (
            <Chip key={t} on={picked[t]}
              onClick={() => setPicked(Object.assign({}, picked, { [t]: !picked[t] }))}>
              {t}
            </Chip>
          ))}
        </div>

        {monoLabel('Or in your own words')}
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={3}
          placeholder={'e.g. "I care about AI and chip policy, F1, and Southeast Asian markets — keep celebrity news out of my way."'}
          style={{
            width: '100%', boxSizing: 'border-box', resize: 'vertical',
            fontFamily: 'inherit', fontSize: 13.5, lineHeight: 1.5,
            padding: '10px 12px', borderRadius: 4,
            border: '1px solid var(--paper-rule)', background: 'var(--paper-2)',
            color: 'var(--ink)', outline: 'none',
          }}
        />
        <div style={{ fontSize: 11, color: 'var(--ink-muted)', marginTop: 6 }}>
          {aiLive
            ? 'Cleo reads this once when you start — 1 model call — and turns it into sections + interests it can search for.'
            : 'Parsed locally (no model configured) — section names and comma-separated interests are picked up.'}
        </div>

        {canRecurate && (
          <label style={{ display: 'flex', gap: 10, alignItems: 'flex-start', marginTop: 16, fontSize: 12.5, color: 'var(--ink-soft)', cursor: 'pointer' }}>
            <input type="checkbox" checked={recurate} onChange={(e) => setRecurate(e.target.checked)} style={{ marginTop: 2 }} />
            <span>
              <strong>Re-curate tonight’s edition from this brief</strong> — re-runs the whole
              pipeline for your interests (~1–2 min). Otherwise your picks shape ranking
              and sections immediately, and tomorrow’s edition fully.
            </span>
          </label>
        )}

        <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginTop: 24, paddingTop: 16, borderTop: '1px solid var(--paper-rule)' }}>
          <button className="btn btn-ghost" onClick={skip} disabled={busy} style={{ color: 'var(--ink-muted)' }}>
            Skip for now
          </button>
          <span style={{ flex: 1 }} />
          <button className="btn" onClick={start} disabled={busy} style={{
            background: 'var(--ink)', color: 'var(--paper)', padding: '10px 22px', fontSize: 14,
          }}>
            {busy ? 'Cleo is reading your brief…' : 'Start reading'}
          </button>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { SavedView, SettingsView, SearchPalette, OnboardingGate });
