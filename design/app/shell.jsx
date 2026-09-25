// PROVENANCE: ORIGINAL (bespoke to Cura) - React/JSX prototype component; the product spec (see design/HANDOFF.md). Third-party (CDN): React 18, ReactDOM, Babel standalone. See PROVENANCE.md.
// Cura - App shell (sidebar, topbar, layout)

const { useState } = React;

// Edition facts shown across the chrome: live values when served by
// `cura serve` (CURA_LIVE), canned prototype defaults otherwise.
function editionMeta() {
  const live = window.CURA_LIVE;
  const count = (window.CURA_STORIES || []).length || 9;
  if (window.CURA_PENDING) {
    const now = new Date();
    return { count: '…', minutes: '…',
             dateline: now.toLocaleDateString('en-US', { weekday: 'long' })
               + ' · ' + now.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
             date: now.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
             scanned: null };
  }
  if (!live) {
    return { count, minutes: 15, dateline: 'Tuesday · Aug 27',
             date: 'Aug 27', scanned: 312 };
  }
  const now = new Date();
  const date = now.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  const weekday = now.toLocaleDateString('en-US', { weekday: 'long' });
  return {
    count,
    minutes: Math.max(1, Math.round(live.estMinutes || count)),
    dateline: weekday + ' · ' + date,
    date,
    scanned: live.scannedArticles || null,
  };
}
window.editionMeta = editionMeta;

// Article image overlay: absolutely fills the decorative visual beneath it,
// and removes itself when the URL is absent, a canned colour swatch, or
// fails to load - leaving the placeholder graphic showing.
function StoryImage({ src, alt }) {
  if (!src || !/^https?:/.test(src)) return null;
  return (
    <img src={src} alt={alt || ''} loading="lazy"
      style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' }}
      onError={(e) => { e.currentTarget.style.display = 'none'; }} />
  );
}
window.StoryImage = StoryImage;

// Every story in the edition: the briefing set plus the analysed-but-
// unbriefed pool that fills Read's topic sections.
function allStories() {
  return (window.CURA_STORIES || []).concat(window.CURA_MORE || []);
}
window.allStories = allStories;

// "Why am I seeing this": prefer the user's own Settings signals (followed
// topics) over the pipeline's generic reason.
function whyFor(story) {
  if (window.CURA_LIVE && window.CuraStore) {
    const signals = CuraStore.getSignals();
    if (signals.topics && signals.topics[story.section]) {
      return 'You follow ' + story.section;
    }
  }
  return story.why;
}
window.whyFor = whyFor;

function Sidebar({ view, setView }) {
  const navItems = [
    { id: 'read',       label: 'Read',       icon: 'read',       shortcut: '1' },
    { id: 'listen',     label: 'Listen',     icon: 'listen',     shortcut: '2' },
    { id: 'experience', label: 'Experience', icon: 'experience', shortcut: '3' },
  ];
  const utilItems = [
    { id: 'verify',   label: 'Verify',    icon: 'verify' },
    { id: 'saved',    label: 'Saved',     icon: 'bookmark' },
    { id: 'settings', label: 'Settings',  icon: 'settings' },
  ];
  const saved = window.useSaved ? window.useSaved() : { ids: [] };
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-c serif">Cura</span>
        <span className="brand-dot" />
        <span className="brand-meta">v0.1</span>
      </div>

      <div className="nav-section">
        <div className="nav-section-label">Formats</div>
        {navItems.map(it => (
          <div
            key={it.id}
            className={'nav-item ' + (view === it.id ? 'active' : '')}
            onClick={() => setView(it.id)}
          >
            <span className="nav-icon"><CIcon name={it.icon} size={17} /></span>
            <span>{it.label}</span>
            <span className="nav-shortcut">{it.shortcut}</span>
          </div>
        ))}
      </div>

      <div className="nav-section">
        <div className="nav-section-label">Tools</div>
        {utilItems.map(it => (
          <div
            key={it.id}
            className={'nav-item ' + (view === it.id ? 'active' : '')}
            onClick={() => setView(it.id)}
          >
            <span className="nav-icon"><CIcon name={it.icon} size={17} /></span>
            <span>{it.label}</span>
            {it.id === 'saved' && saved.ids.length > 0 && (
              <span className="nav-shortcut" style={{ background: 'var(--accent)', color: 'var(--paper)', borderRadius: 9, padding: '1px 7px', fontWeight: 600 }}>{saved.ids.length}</span>
            )}
          </div>
        ))}
      </div>

      <div style={{ flex: 1 }} />

      {/* Today's edition stat (no account, no per-user budget) */}
      <div style={{ padding: '20px 24px', borderTop: '1px solid var(--paper-rule)' }}>
        <div style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 10, letterSpacing: '0.22em',
          color: 'var(--ink-muted)', textTransform: 'uppercase',
          marginBottom: 10,
        }}>Today’s edition</div>
        <div style={{
          display: 'flex', alignItems: 'baseline', gap: 6,
          fontFamily: 'Fraunces, serif', color: 'var(--ink)',
        }}>
          <span style={{ fontSize: 28, fontWeight: 600 }}>{editionMeta().count}</span>
          <span style={{ fontSize: 13, color: 'var(--ink-muted)' }}>stories · ~{editionMeta().minutes} min</span>
        </div>
        <div style={{
          marginTop: 8, fontSize: 11, color: 'var(--ink-muted)', lineHeight: 1.4,
        }}>{editionMeta().scanned ? editionMeta().scanned + ' articles scanned · ' : ''}{editionMeta().count} selected by Cleo</div>
      </div>
    </aside>
  );
}

function TopBar({ view, openCleo, breadcrumb, openSearch }) {
  const labels = {
    read: 'Read · your daily set',
    listen: 'Listen · audio briefings',
    experience: 'Experience · the daily edition',
    verify: 'Verify · grounded fact-check',
    saved: 'Saved · your reading list',
    settings: 'Settings · personalization',
    story: 'Read · story',
  };
  return (
    <div className="topbar">
      <div className="breadcrumb">{breadcrumb || labels[view] || 'Cura'}</div>
      <div className="topbar-search" onClick={openSearch} role="button">
        <CIcon name="search" size={14} />
        <span style={{ flex: 1 }}>Search stories, sources, topics…</span>
        <span className="mono" style={{ fontSize: 11, color: 'var(--ink-muted)' }}>⌘K</span>
      </div>
      <div className="budget-chip">
        <span className="dot" />
        <span className="mono" style={{ letterSpacing: '0.16em', fontSize: 11, color: 'var(--ink-muted)' }}>EDITION</span>
        <span style={{ fontWeight: 600 }}>{editionMeta().date} · {editionMeta().count} stories</span>
      </div>
      <button className="ask-cleo-btn" onClick={openCleo}>
        <CIcon name="sparkle" size={14} />
        <span>Ask Cleo</span>
      </button>
    </div>
  );
}

// Confidence bar component (shared)
function ConfBar({ level = 4, label, max = 5 }) {
  return (
    <span className="conf-pill">
      <span className="conf-bar">
        {Array.from({ length: max }).map((_, i) => (
          <i key={i} className={i < level ? (level >= 4 ? 'on' : 'warn') : ''} />
        ))}
      </span>
      <span>{label}</span>
    </span>
  );
}

// Generic small "section tag"
function SectionTag({ children }) {
  return <div className="section-tag">{children}</div>;
}

// Why-am-I-seeing-this inline button
function WhyTag({ reason }) {
  const [open, setOpen] = useState(false);
  return (
    <span style={{ position: 'relative', display: 'inline-block' }}>
      <span className="why-tag" onClick={() => setOpen(!open)}>
        <span style={{ fontSize: 13 }}>?</span> why am I seeing this
      </span>
      {open && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, marginTop: 6,
          background: 'var(--ink)', color: 'var(--paper)',
          padding: '12px 14px', borderRadius: 6, width: 280,
          fontSize: 12, lineHeight: 1.5, zIndex: 30,
          boxShadow: '0 12px 30px rgba(14,26,43,0.25)', fontStyle: 'normal',
        }}>
          <div style={{
            fontFamily: 'JetBrains Mono, monospace', fontSize: 9,
            letterSpacing: '0.22em', textTransform: 'uppercase',
            color: 'rgba(244,239,230,0.6)', marginBottom: 6,
          }}>SIGNAL</div>
          {reason}
          <div style={{
            marginTop: 10, paddingTop: 10,
            borderTop: '1px solid rgba(244,239,230,0.15)',
            fontSize: 11, color: 'rgba(244,239,230,0.7)',
          }}>You can adjust signals in Settings → Personalization.</div>
        </div>
      )}
    </span>
  );
}

Object.assign(window, { Sidebar, TopBar, ConfBar, SectionTag, WhyTag });
