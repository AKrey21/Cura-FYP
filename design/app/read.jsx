// PROVENANCE: ORIGINAL (bespoke to Cura) - React/JSX prototype component; the product spec (see design/HANDOFF.md). Third-party (CDN): React 18, ReactDOM, Babel standalone. Verify claim-checker calls window.claude (LLM) with a fallback. See PROVENANCE.md.
// Cura - Read view (curated feed) + Story detail + Verify (source comparison)

const { useState: useStateR } = React;

// Reusable bookmark toggle - reflects + mutates the shared saved store.
function SaveButton({ id, size = 13, ghost = true, label }) {
  const saved = window.useSaved ? window.useSaved() : { has: () => false };
  const on = saved.has(id);
  return (
    <button
      className={'btn' + (ghost ? ' btn-ghost' : '')}
      title={on ? 'Saved — tap to remove' : 'Save for later'}
      onClick={(e) => { e.stopPropagation(); window.CuraStore.toggleSaved(id); }}
      style={{ padding: label ? '8px 14px' : 8, color: on ? 'var(--accent)' : 'var(--ink)' }}
    >
      <CIcon name={on ? 'bookmark-fill' : 'bookmark'} size={size} color={on ? 'var(--accent)' : 'currentColor'} />
      {label && <span>{on ? 'Saved' : 'Save'}</span>}
    </button>
  );
}

// Live build progress for the curating screen. Polls /api/status (served by
// `cura serve`) and renders a weighted loading bar; in the static prototype /
// export there's no endpoint, so it degrades to the original curating line.
function CuratingStatus() {
  const [prog, setProg] = React.useState(window.CURA_PROGRESS || null);
  React.useEffect(() => {
    let alive = true;
    const tick = () => fetch('/api/status')
      .then(r => (r.ok ? r.json() : null))
      .then(s => {
        if (!alive || !s || (s.status !== 'running' && s.status !== 'done')) return;
        window.CURA_PROGRESS = s;
        setProg(s);
      })
      .catch(() => {});
    tick();
    const id = setInterval(tick, 1200);
    return () => { alive = false; clearInterval(id); };
  }, []);

  const fallback = window.CURA_PENDING
    ? (window.CURA_REQUESTED && window.CURA_REQUESTED.length
        ? 'Cleo is curating your briefing on ' + window.CURA_REQUESTED.join(', ')
          + ' · running the full pipeline on demand'
        : 'Cleo is curating your edition · fetching, summarising & triangulating live sources')
    : 'Cleo is curating today’s edition · scanning 312 sources';
  const label = prog
    ? (prog.label || 'Curating') + (prog.detail ? ' · ' + prog.detail : '')
    : fallback;
  const pct = prog ? Math.round((prog.fraction || 0) * 100) : 0;

  return (
    <div style={{ maxWidth: 460, margin: '40px auto 0' }}>
      <div className="mono" style={{ fontSize: 11, letterSpacing: '0.22em', textTransform: 'uppercase', color: 'var(--ink-muted)', textAlign: 'center', marginBottom: prog ? 16 : 0 }}>
        {label}
      </div>
      {prog && (
        <React.Fragment>
          <div style={{ height: 3, borderRadius: 3, background: 'var(--paper-3)', overflow: 'hidden' }}>
            <div style={{ height: '100%', width: pct + '%', background: 'var(--accent)', borderRadius: 3, transition: 'width .7s cubic-bezier(.4,0,.2,1)' }} />
          </div>
          <div className="mono" style={{ fontSize: 10, letterSpacing: '0.18em', color: 'var(--ink-muted)', textAlign: 'center', marginTop: 10 }}>
            {pct}% · step {Math.min((prog.index || 0) + 1, prog.total || 1)} of {prog.total || 1}
          </div>
        </React.Fragment>
      )}
    </div>
  );
}

function ReadSkeleton() {
  const Box = ({ w, h, mb, r = 4 }) => (
    <div style={{ width: w, height: h, marginBottom: mb, borderRadius: r, background: 'linear-gradient(90deg, var(--paper-2) 25%, var(--paper-3) 50%, var(--paper-2) 75%)', backgroundSize: '400% 100%', animation: 'curaShimmer 1.4s ease infinite' }} />
  );
  return (
    <div className="scroll-area">
      <style>{`@keyframes curaShimmer{0%{background-position:100% 0}100%{background-position:-100% 0}}`}</style>
      <div style={{ maxWidth: 1080, margin: '0 auto', padding: '40px 48px 80px' }}>
        <Box w={180} h={11} mb={18} />
        <Box w={'62%'} h={44} mb={10} />
        <Box w={'40%'} h={44} mb={48} />
        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 32, marginBottom: 36 }}>
          <div>
            <Box w={220} h={14} mb={16} />
            <Box w={'95%'} h={32} mb={8} /><Box w={'80%'} h={32} mb={20} />
            <Box w={'100%'} h={14} mb={8} /><Box w={'90%'} h={14} mb={8} /><Box w={'70%'} h={14} mb={0} />
          </div>
          <Box w={'100%'} h={220} r={6} mb={0} />
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 28 }}>
          {[0, 1, 2].map(i => (
            <div key={i}>
              <Box w={'100%'} h={130} r={2} mb={14} />
              <Box w={'90%'} h={20} mb={8} /><Box w={'100%'} h={13} mb={6} /><Box w={'60%'} h={13} mb={0} />
            </div>
          ))}
        </div>
        <CuratingStatus />
      </div>
    </div>
  );
}

// Newspaper-style section navigation: Front page + one tab per topic that
// has stories today. Sticky, so sections stay one click away mid-scroll.
function SectionBar({ topics, active }) {
  const Tab = ({ label, target, on }) => (
    <button
      onClick={() => { window.location.hash = target; }}
      style={{
        fontFamily: 'JetBrains Mono, monospace', fontSize: 11,
        letterSpacing: '0.18em', textTransform: 'uppercase',
        padding: '16px 2px 12px', border: 'none', background: 'none',
        cursor: 'pointer', whiteSpace: 'nowrap',
        color: on ? 'var(--accent)' : 'var(--ink-muted)',
        boxShadow: on ? 'inset 0 -2px 0 var(--accent)' : 'none',
        fontWeight: on ? 700 : 500,
      }}
    >{label}</button>
  );
  return (
    <nav style={{
      position: 'sticky', top: 0, zIndex: 5,
      background: 'var(--paper)', borderBottom: '1px solid var(--paper-rule)',
      display: 'flex', gap: 22, alignItems: 'center', overflowX: 'auto',
    }}>
      <Tab label="Front page" target="#read" on={!active} />
      {topics.map(t => (
        <Tab key={t} label={t} target={'#read/' + encodeURIComponent(t)} on={active === t} />
      ))}
    </nav>
  );
}

function TopicCard({ story, openStory }) {
  return (
    <article className="story-card" onClick={() => openStory(story.id)}>
      <div style={{
        aspectRatio: '16/10', borderRadius: 2,
        background: 'linear-gradient(135deg, var(--paper-3), var(--paper-2))',
        marginBottom: 12, position: 'relative', overflow: 'hidden',
      }}>
        <StoryImage src={story.image} alt={story.headline} />
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <ConfBar level={story.confidence} label={story.confidenceLabel} />
        <span style={{ fontSize: 11, color: 'var(--ink-muted)' }}>· {story.timestamp}</span>
      </div>
      <h4 className="serif" style={{ fontSize: 19, lineHeight: 1.2, fontWeight: 600, margin: '0 0 6px' }}>
        {story.headline}
      </h4>
      <p style={{ fontSize: 12.5, lineHeight: 1.5, color: 'var(--ink-soft)', margin: '0 0 10px' }}>
        {String(story.dek).length > 130 ? String(story.dek).slice(0, 130) + '…' : story.dek}
      </p>
      <div style={{ fontSize: 11, color: 'var(--ink-muted)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span><strong style={{ color: 'var(--ink)' }}>{story.sources}</strong> source{story.sources === 1 ? '' : 's'} · {story.minutes} min</span>
        <SaveButton id={story.id} />
      </div>
    </article>
  );
}

// A topic's section front: lead story + card grid, fed by the briefing
// stories of that topic plus the analysed pool beyond the spoken briefing.
function TopicSection({ topic, stories, openStory, followed }) {
  if (!stories.length) {
    return (
      <div style={{ padding: '100px 0', textAlign: 'center' }}>
        <div className="serif" style={{ fontSize: 26, fontWeight: 600, marginBottom: 10 }}>
          Nothing in {topic} today.
        </div>
        <div style={{ fontSize: 13, color: 'var(--ink-muted)' }}>
          Cura only sections stories it has analysed — check back after the next edition.
        </div>
      </div>
    );
  }
  const lead = stories[0];
  const rest = stories.slice(1);
  return (
    <div>
      {/* Section masthead */}
      <div style={{
        margin: '32px 0 36px', paddingBottom: 24,
        borderBottom: '1px solid var(--paper-rule)',
        display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 24,
      }}>
        <div>
          <SectionTag>Section front · {stories.length} {stories.length === 1 ? 'story' : 'stories'} today</SectionTag>
          <h1 className="serif" style={{ fontSize: 44, lineHeight: 1.05, fontWeight: 600, letterSpacing: '-0.01em', margin: 0 }}>
            {topic}.
          </h1>
        </div>
        <div style={{ fontSize: 12, color: 'var(--ink-muted)', maxWidth: 280, textAlign: 'right', lineHeight: 1.5 }}>
          {followed
            ? <span>You follow this section — it ranks into your front page too.</span>
            : <span>From today’s scanned coverage. Follow it in Settings to rank it up.</span>}
        </div>
      </div>

      {/* Section lead */}
      <article
        className="story-card"
        onClick={() => openStory(lead.id)}
        style={{
          display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 32,
          paddingBottom: 32, borderBottom: '1px solid var(--paper-rule)', marginBottom: 36,
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
            <span className="src-chip">LEAD · {topic}</span>
            <ConfBar level={lead.confidence} label={lead.confidenceLabel} />
            <span style={{ fontSize: 11, color: 'var(--ink-muted)' }}>{lead.timestamp}</span>
          </div>
          <h2 className="serif" style={{ fontSize: 32, lineHeight: 1.1, fontWeight: 600, letterSpacing: '-0.01em', margin: '0 0 12px' }}>
            {lead.headline}
          </h2>
          <p style={{ fontSize: 16, lineHeight: 1.55, color: 'var(--ink-soft)', margin: '0 0 16px', maxWidth: '52ch' }}>
            {lead.dek}
          </p>
          {lead.tldr && (
            <div style={{ borderLeft: '2px solid var(--accent)', paddingLeft: 14, margin: '0 0 16px' }}>
              <div style={{
                fontFamily: 'JetBrains Mono, monospace', fontSize: 10,
                letterSpacing: '0.22em', textTransform: 'uppercase',
                color: 'var(--ink-muted)', marginBottom: 8,
              }}>TL;DR — cited summary</div>
              <ul style={{ margin: 0, padding: 0, listStyle: 'none' }}>
                {lead.tldr.map((b, i) => (
                  <li key={i} style={{ fontSize: 13.5, lineHeight: 1.5, marginBottom: 6, paddingLeft: 16, position: 'relative' }}>
                    <span style={{ position: 'absolute', left: 0, top: 8, width: 6, height: 1, background: 'var(--ink-muted)' }}/>{b}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <div style={{ display: 'flex', alignItems: 'center', gap: 14, fontSize: 12, color: 'var(--ink-muted)' }}>
            <span><strong style={{ color: 'var(--ink)' }}>{lead.sources}</strong> sources · {lead.minutes} min read</span>
            <span style={{ marginLeft: 'auto' }} />
            <SaveButton id={lead.id} />
          </div>
        </div>
        <div style={{
          aspectRatio: '4/3', borderRadius: 4, position: 'relative', overflow: 'hidden',
          background: 'linear-gradient(135deg,#1A2438 0%,#2A3548 60%,#0E1A2B 100%)',
        }}>
          <StoryImage src={lead.image} alt={lead.headline} />
        </div>
      </article>

      {/* The rest of the section */}
      {rest.length > 0 && (
        <div className="stagger" style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 28 }}>
          {rest.map(s => <TopicCard key={s.id} story={s} openStory={openStory} />)}
        </div>
      )}
    </div>
  );
}

function ReadView({ openStory, openCleo, section }) {
  // Personalisation: Today's edition ranks followed topics first (live mode;
  // stable within groups so the pipeline's coverage ranking is preserved).
  const { signals } = window.useSignals ? window.useSignals()
    : { signals: { topics: {} } };
  const isFollowed = (t) => !!(signals.topics && signals.topics[t]);
  const follows = (s) => isFollowed(s.section) ? 0 : 1;
  const ranked = window.CURA_LIVE
    ? CURA_STORIES.slice().sort((a, b) => follows(a) - follows(b))
    : CURA_STORIES;
  const hero = ranked[0];
  const cluster = ranked.slice(1, 4);
  const list = ranked.slice(4);

  // Section tabs: every topic with at least one story today (briefing +
  // analysed pool), followed topics first, then by coverage.
  const pool = window.allStories ? allStories() : CURA_STORIES;
  const sectionCounts = {};
  pool.forEach(s => { sectionCounts[s.section] = (sectionCounts[s.section] || 0) + 1; });
  const topicTabs = Object.keys(sectionCounts)
    .sort((a, b) => (isFollowed(a) ? 0 : 1) - (isFollowed(b) ? 0 : 1)
                    || sectionCounts[b] - sectionCounts[a]);

  // Tab switches land at the top of the new section, not mid-scroll.
  const scrollRef = React.useRef(null);
  React.useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = 0;
  }, [section]);

  // On-demand briefing (live only): the masthead form + edition state
  const [briefOpen, setBriefOpen] = useStateR(false);
  const [briefQ, setBriefQ] = useStateR('');
  const onDemandTopics = (window.CURA_LIVE && window.CURA_LIVE.topics) || [];

  // First-visit curating state (once per session) - reference for the real fetch.
  const [loaded, setLoaded] = useStateR(window.__curaReadLoadedOnce === true);
  React.useEffect(() => {
    if (loaded) return;
    const t = setTimeout(() => { window.__curaReadLoadedOnce = true; setLoaded(true); }, 900);
    return () => clearTimeout(t);
  }, [loaded]);
  if (!loaded) return <ReadSkeleton />;

  return (
    <div className="scroll-area" ref={scrollRef}>
      <div style={{ maxWidth: 1080, margin: '0 auto', padding: '0 48px 80px' }}>

        <SectionBar topics={topicTabs} active={section} />

        {section ? (
          <TopicSection
            topic={section}
            stories={pool.filter(s => s.section === section)}
            openStory={openStory}
            followed={isFollowed(section)}
          />
        ) : (
        <React.Fragment>

        {/* Greeting + masthead */}
        <div data-tour="masthead" style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 32, margin: '32px 0 56px', paddingBottom: 28, borderBottom: '1px solid var(--paper-rule)' }}>
          <div style={{ maxWidth: 640 }}>
            <SectionTag>
              {editionMeta().dateline} · {onDemandTopics.length
                ? 'on-demand edition: ' + onDemandTopics.join(', ')
                : 'today’s edition'}
            </SectionTag>
            <h1 className="serif" style={{ fontSize: 44, lineHeight: 1.05, fontWeight: 600, letterSpacing: '-0.01em', margin: 0, whiteSpace: 'nowrap' }}>
              Slow news, examined.
            </h1>
            <h1 className="serif" style={{ fontSize: 44, lineHeight: 1.05, fontWeight: 600, letterSpacing: '-0.01em', margin: '4px 0 0', color: 'var(--ink-muted)', whiteSpace: 'nowrap' }}>
              {editionMeta().count} stories · ~{editionMeta().minutes} minute{editionMeta().minutes === 1 ? '' : 's'}.
            </h1>
            {onDemandTopics.length > 0 && (
              <button
                className="btn btn-ghost"
                onClick={() => window.curaRequestBriefing([])}
                style={{ marginTop: 10, padding: '6px 10px', fontSize: 12 }}
              >← Back to the daily edition</button>
            )}
          </div>
          <div style={{
            display: 'flex', gap: 8, alignItems: 'center', flexShrink: 0,
          }}>
            {window.curaRequestBriefing && (
              <button className="btn" onClick={() => setBriefOpen(o => !o)}>
                <CIcon name="verify" size={14}/> New edition…
              </button>
            )}
            <button className="btn" onClick={openCleo}>
              <CIcon name="sparkle" size={14}/> Brief me
            </button>
            <button className="btn">
              <CIcon name="listen" size={14}/> Play audio
            </button>
          </div>
        </div>

        {/* On-demand briefing: re-runs the whole pipeline for these topics */}
        {briefOpen && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (briefQ.trim()) window.curaRequestBriefing(briefQ.split(','));
            }}
            style={{
              display: 'flex', gap: 12, alignItems: 'center',
              margin: '-32px 0 44px', padding: '14px 18px',
              background: 'var(--paper-2)', border: '1px solid var(--paper-rule)',
              borderRadius: 6,
            }}
          >
            <span style={{
              fontFamily: 'JetBrains Mono, monospace', fontSize: 10,
              letterSpacing: '0.22em', textTransform: 'uppercase',
              color: 'var(--ink-muted)', whiteSpace: 'nowrap',
            }}>Brief me on</span>
            <input
              autoFocus
              value={briefQ}
              onChange={(e) => setBriefQ(e.target.value)}
              placeholder="e.g. chip war, climate policy — comma-separate topics"
              style={{
                flex: 1, fontSize: 14, padding: '8px 12px',
                border: '1px solid var(--paper-rule)', borderRadius: 4,
                background: 'var(--paper)', color: 'var(--ink)', outline: 'none',
              }}
            />
            <button className="btn" type="submit">Curate edition</button>
            <span style={{ fontSize: 11, color: 'var(--ink-muted)', whiteSpace: 'nowrap' }}>
              re-runs the full pipeline · ~1–2 min
            </span>
          </form>
        )}

        {/* Hero story */}
        <article
          data-tour="lead-story"
          className="story-card"
          onClick={() => openStory(hero.id)}
          style={{
            display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 32,
            paddingBottom: 36, borderBottom: '1px solid var(--paper-rule)',
            marginBottom: 36,
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
              <span className="src-chip">LEAD · {hero.section}</span>
              <ConfBar level={hero.confidence} label={hero.confidenceLabel} />
              <span style={{ fontSize: 11, color: 'var(--ink-muted)' }}>{hero.timestamp}</span>
            </div>
            <h2 className="serif" style={{
              fontSize: 38, lineHeight: 1.08, fontWeight: 600,
              letterSpacing: '-0.01em', margin: '0 0 14px',
            }}>{hero.headline}</h2>
            <p style={{
              fontSize: 17, lineHeight: 1.55, color: 'var(--ink-soft)',
              margin: '0 0 18px', maxWidth: '52ch',
            }}>{hero.dek}</p>

            {/* TL;DR bullets */}
            <div style={{
              borderLeft: '2px solid var(--accent)', paddingLeft: 14,
              margin: '0 0 18px',
            }}>
              <div style={{
                fontFamily: 'JetBrains Mono, monospace', fontSize: 10,
                letterSpacing: '0.22em', textTransform: 'uppercase',
                color: 'var(--ink-muted)', marginBottom: 8,
              }}>TL;DR — cited summary</div>
              <ul style={{ margin: 0, padding: 0, listStyle: 'none' }}>
                {hero.tldr.map((b, i) => (
                  <li key={i} style={{
                    fontSize: 14, lineHeight: 1.5, marginBottom: 6,
                    paddingLeft: 16, position: 'relative',
                  }}>
                    <span style={{
                      position: 'absolute', left: 0, top: 8, width: 6, height: 1,
                      background: 'var(--ink-muted)',
                    }}/>{b}
                  </li>
                ))}
              </ul>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 14, fontSize: 12, color: 'var(--ink-muted)' }}>
              <span><strong style={{ color: 'var(--ink)' }}>{hero.sources}</strong> sources · {hero.minutes} min read</span>
              <span style={{ width: 1, height: 12, background: 'var(--paper-rule)' }}/>
              <WhyTag reason={whyFor(hero)} />
              <span style={{ marginLeft: 'auto' }} />
              <SaveButton id={hero.id} />
            </div>
          </div>

          {/* Hero visual + bias spread */}
          <div>
            <div style={{
              aspectRatio: '4/3', background: 'linear-gradient(135deg,#1A2438 0%,#2A3548 60%,#0E1A2B 100%)',
              borderRadius: 4, position: 'relative', overflow: 'hidden',
            }}>
              {/* Decorative chart-ish lines */}
              <svg width="100%" height="100%" style={{ position: 'absolute', inset: 0 }} viewBox="0 0 400 300" preserveAspectRatio="none">
                <path d="M0,200 C80,180 140,220 200,150 C260,80 320,140 400,90" stroke="#D9A074" strokeWidth="2" fill="none"/>
                <path d="M0,240 C80,230 140,210 200,180 C260,150 320,170 400,140" stroke="#F4EFE6" strokeWidth="1" fill="none" opacity="0.5"/>
                <text x="20" y="40" fill="#F4EFE6" fontFamily="Fraunces, serif" fontSize="14" opacity="0.7">§ {hero.section}</text>
                <text x="20" y="58" fill="#D9A074" fontFamily="JetBrains Mono, monospace" fontSize="10" letterSpacing="2">{(hero.sources + ' SOURCES — ' + hero.timestamp).toUpperCase()}</text>
              </svg>
              <StoryImage src={hero.image} alt={hero.headline} />
            </div>

            {/* Bias / framing spread */}
            <div data-tour="spread" style={{
              marginTop: 16, padding: '16px 18px',
              background: 'var(--paper-2)', border: '1px solid var(--paper-rule)',
              borderRadius: 4,
            }}>
              <div style={{
                fontFamily: 'JetBrains Mono, monospace', fontSize: 10,
                letterSpacing: '0.22em', textTransform: 'uppercase',
                color: 'var(--ink-muted)', marginBottom: 10,
                display: 'flex', justifyContent: 'space-between',
              }}>
                <span>Coverage spread</span><span>{hero.sources} sources</span>
              </div>
              {/* bias is optional in the Story contract — live pipeline data may omit it */}
              {hero.bias && (
                <React.Fragment>
                  <div style={{ display: 'flex', height: 8, borderRadius: 2, overflow: 'hidden' }}>
                    <div style={{ width: hero.bias.left + '%', background: '#3B5A8C' }} title={'Left ' + hero.bias.left + '%'}/>
                    <div style={{ width: hero.bias.center + '%', background: '#6B7280' }} title={'Center ' + hero.bias.center + '%'}/>
                    <div style={{ width: hero.bias.right + '%', background: '#8E5A2E' }} title={'Right ' + hero.bias.right + '%'}/>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8, fontSize: 11, color: 'var(--ink-muted)' }}>
                    <span>Left {hero.bias.left}%</span>
                    <span>Center {hero.bias.center}%</span>
                    <span>Right {hero.bias.right}%</span>
                  </div>
                </React.Fragment>
              )}
              <button
                className="btn"
                style={{ marginTop: 12, width: '100%', justifyContent: 'center' }}
                onClick={(e) => { e.stopPropagation(); window.location.hash = '#verify'; }}
              >
                <CIcon name="verify" size={13}/> Compare 3 sources side-by-side
              </button>
            </div>
          </div>
        </article>

        {/* Cluster: 3 secondary stories */}
        <div className="stagger" style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 28, marginBottom: 48 }}>
          {cluster.map(s => (
            <article key={s.id} className="story-card" onClick={() => openStory(s.id)}>
              <div style={{
                aspectRatio: '16/10',
                background: 'linear-gradient(135deg, var(--paper-3), var(--paper-2))',
                marginBottom: 14, position: 'relative', overflow: 'hidden',
                borderRadius: 2,
              }}>
                <div style={{
                  position: 'absolute', inset: 0,
                  background: s.section === 'Climate' ? 'linear-gradient(135deg,#1F5E3F22,#1F5E3F44)' :
                             s.section === 'Technology' ? 'linear-gradient(135deg,#3B5A8C22,#3B5A8C44)' :
                             'linear-gradient(135deg,#B8331E22,#B8331E44)',
                }}/>
                <StoryImage src={s.image} alt={s.headline} />
                <div style={{
                  position: 'absolute', top: 12, left: 12,
                  fontFamily: 'JetBrains Mono, monospace', fontSize: 10,
                  letterSpacing: '0.22em', textTransform: 'uppercase',
                  color: 'var(--ink)',
                  background: 'rgba(244,239,230,0.85)', padding: '2px 6px', borderRadius: 2,
                }}>§ {s.section}</div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                <ConfBar level={s.confidence} label={s.confidenceLabel} />
                <span style={{ fontSize: 11, color: 'var(--ink-muted)' }}>· {s.timestamp}</span>
              </div>
              <h3 className="serif" style={{
                fontSize: 22, lineHeight: 1.15, fontWeight: 600,
                letterSpacing: '-0.005em', margin: '0 0 10px',
              }}>{s.headline}</h3>
              <p style={{ fontSize: 13, lineHeight: 1.5, color: 'var(--ink-soft)', margin: '0 0 12px' }}>{s.dek}</p>
              <div style={{ fontSize: 11, color: 'var(--ink-muted)', display: 'flex', justifyContent: 'space-between' }}>
                <span><strong style={{ color: 'var(--ink)' }}>{s.sources}</strong> sources · {s.minutes} min</span>
                <WhyTag reason={whyFor(s)} />
              </div>
            </article>
          ))}
        </div>

        {/* Briefly noted + trends */}
        <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 1fr', gap: 40 }}>
          <div>
            <SectionTag>Briefly noted</SectionTag>
            <div style={{ borderTop: '1px solid var(--paper-rule)' }}>
              {list.map(s => (
                <article
                  key={s.id}
                  className="story-card"
                  onClick={() => openStory(s.id)}
                  style={{
                    padding: '18px 0', borderBottom: '1px solid var(--paper-rule)',
                    display: 'grid', gridTemplateColumns: '70px 1fr auto', gap: 20,
                    alignItems: 'baseline',
                  }}
                >
                  <div style={{
                    fontFamily: 'JetBrains Mono, monospace', fontSize: 10,
                    letterSpacing: '0.22em', textTransform: 'uppercase',
                    color: 'var(--ink-muted)',
                  }}>§ {s.section}</div>
                  <div>
                    <h4 className="serif" style={{ fontSize: 19, lineHeight: 1.2, fontWeight: 600, margin: '0 0 6px' }}>
                      {s.headline}
                    </h4>
                    <div style={{ fontSize: 12, color: 'var(--ink-muted)', display: 'flex', gap: 12, alignItems: 'center' }}>
                      <ConfBar level={s.confidence} label={s.confidenceLabel} />
                      <span>{s.sources} sources · {s.minutes} min</span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <SaveButton id={s.id} />
                    <CIcon name="arrow-right" size={16} color="var(--ink-muted)" />
                  </div>
                </article>
              ))}
            </div>
          </div>

          <aside>
            <SectionTag>Trending across your sources</SectionTag>
            <div style={{ background: 'var(--paper-2)', padding: 20, borderRadius: 4 }}>
              {CURA_TRENDS.map(t => (
                <div key={t.rank} style={{
                  display: 'flex', alignItems: 'baseline', gap: 14,
                  padding: '12px 0', borderBottom: '1px solid var(--paper-rule)',
                }}>
                  <span className="serif" style={{ fontSize: 22, fontWeight: 600, color: 'var(--ink-muted)', width: 24 }}>{t.rank}</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 14, fontWeight: 600 }}>{t.label}</div>
                    <div style={{ fontSize: 11, color: 'var(--ink-muted)', marginTop: 2 }}>{t.section}</div>
                  </div>
                  <div className="mono" style={{ fontSize: 11, color: 'var(--green)', fontWeight: 600 }}>{t.delta}</div>
                </div>
              ))}
            </div>
            <div style={{ marginTop: 20, fontSize: 11, color: 'var(--ink-muted)', lineHeight: 1.5 }}>
              {window.CURA_LIVE
                ? <span>Trends are mention counts across <strong>{editionMeta().scanned || 'today’s'} scanned articles</strong> — independent confirmations, not engagement.</span>
                : <span>Trends are computed across <strong>312 vetted sources</strong>, weighted by independent confirmations — not engagement.</span>}
            </div>
          </aside>
        </div>

        {/* Section teasers: one row per followed topic — the full sections
            live behind the tabs above. */}
        {topicTabs.filter(isFollowed).length > 0 && (
          <div style={{ marginTop: 64 }}>
            <div style={{ paddingBottom: 16, marginBottom: 28, borderBottom: '1px solid var(--paper-rule)' }}>
              <SectionTag>Your sections</SectionTag>
              <h2 className="serif" style={{ fontSize: 28, lineHeight: 1.05, fontWeight: 600, letterSpacing: '-0.01em', margin: 0 }}>
                In today’s paper.
              </h2>
            </div>
            <div className="stagger" style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 24 }}>
              {topicTabs.filter(isFollowed).map(topic => {
                const top = pool.find(s => s.section === topic);
                if (!top) return null;
                return (
                  <article
                    key={topic} className="story-card"
                    onClick={() => { window.location.hash = '#read/' + encodeURIComponent(topic); }}
                    style={{ background: 'var(--paper-2)', border: '1px solid var(--paper-rule)', borderRadius: 4, padding: '16px 18px' }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 10 }}>
                      <span className="mono" style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', color: 'var(--accent)' }}>
                        § {topic}
                      </span>
                      <span style={{ fontSize: 11, color: 'var(--ink-muted)' }}>
                        {sectionCounts[topic]} {sectionCounts[topic] === 1 ? 'story' : 'stories'} →
                      </span>
                    </div>
                    <h4 className="serif" style={{ fontSize: 17, lineHeight: 1.25, fontWeight: 600, margin: 0 }}>
                      {top.headline}
                    </h4>
                  </article>
                );
              })}
            </div>
          </div>
        )}

        </React.Fragment>
        )}
      </div>
    </div>
  );
}

function StoryDetailView({ storyId, goBack, openCleo }) {
  const story = allStories().find(s => s.id === storyId) || CURA_STORIES[0];
  return (
    <div className="scroll-area">
      <div style={{ maxWidth: 760, margin: '0 auto', padding: '32px 24px 100px' }}>
        <button className="btn-ghost btn" onClick={goBack} style={{ marginBottom: 24 }}>
          ← Back to today
        </button>

        <SectionTag>§ {story.section} · {story.timestamp}</SectionTag>
        <h1 className="serif" style={{ fontSize: 46, lineHeight: 1.05, fontWeight: 600, letterSpacing: '-0.01em', margin: '0 0 18px' }}>
          {story.headline}
        </h1>
        <p style={{ fontSize: 19, lineHeight: 1.5, color: 'var(--ink-soft)', margin: '0 0 24px', fontFamily: 'Fraunces, serif' }}>
          {story.dek}
        </p>

        {/* Confidence + sources strip */}
        <div data-tour="story-meta" style={{
          display: 'flex', alignItems: 'center', gap: 20,
          padding: '14px 0', margin: '0 0 32px',
          borderTop: '1px solid var(--paper-rule)', borderBottom: '1px solid var(--paper-rule)',
        }}>
          <ConfBar level={story.confidence} label={story.confidenceLabel} />
          <span style={{ fontSize: 12, color: 'var(--ink-muted)' }}>{story.sources} independent sources</span>
          <span style={{ fontSize: 12, color: 'var(--ink-muted)' }}>{story.minutes} min read</span>
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
            <button className="btn" onClick={openCleo}><CIcon name="sparkle" size={13}/> Ask Cleo</button>
            <SaveButton id={story.id} ghost={false} label />
          </div>
        </div>

        {/* Lead image from the source feeds */}
        {story.image && /^https?:/.test(story.image) && (
          <div style={{
            aspectRatio: '16/9', position: 'relative', overflow: 'hidden',
            borderRadius: 4, marginBottom: 28, background: 'var(--paper-3)',
          }}>
            <StoryImage src={story.image} alt={story.headline} />
          </div>
        )}

        {/* TL;DR */}
        {story.tldr && (
          <div style={{ background: 'var(--paper-2)', padding: '20px 22px', borderRadius: 4, marginBottom: 28 }}>
            <div style={{
              fontFamily: 'JetBrains Mono, monospace', fontSize: 10,
              letterSpacing: '0.22em', textTransform: 'uppercase',
              color: 'var(--ink-muted)', marginBottom: 10,
            }}>TL;DR · cited from primary sources</div>
            <ul style={{ margin: 0, padding: '0 0 0 18px' }}>
              {story.tldr.map((b, i) => (
                <li key={i} style={{ fontSize: 15, lineHeight: 1.55, marginBottom: 8 }}>{b}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Body — live pipeline paragraphs when present; the canned sample
            copy belongs only to the s-fed demo story */}
        {story.body ? (
          <div className="serif drop-cap" style={{ fontSize: 18, lineHeight: 1.65, color: 'var(--ink)' }}>
            {story.body.map((para, i) => <p key={i}>{para}</p>)}
          </div>
        ) : story.id === 's-fed' ? (
          <div className="serif drop-cap" style={{ fontSize: 18, lineHeight: 1.65, color: 'var(--ink)' }}>
            <p>Federal Reserve Chair Jerome Powell used his keynote at the Kansas City Fed’s annual Jackson Hole symposium to deliver what markets quickly read as the clearest signal yet of an imminent shift in policy. <span style={{ background: 'rgba(184,51,30,0.12)', padding: '0 2px' }}>The time has come for policy to adjust</span><sup style={{ color: 'var(--accent)', fontSize: 11 }}>[1]</sup>, Powell said — a phrase that, in the careful grammar of central banking, lands close to a commitment.</p>
            <p>Within minutes, the two-year Treasury yield fell 14 basis points<sup style={{ color: 'var(--accent)', fontSize: 11 }}>[2]</sup>, the largest single-session drop since March. Equity indexes rallied; the dollar weakened against most major currencies.</p>
            <p>But the Federal Open Market Committee is not unanimous. Three regional Fed presidents — Bowman, Logan, and Schmid — have each in recent weeks publicly questioned whether labor-market softening is yet sufficient to warrant a cut<sup style={{ color: 'var(--accent)', fontSize: 11 }}>[3]</sup>. The September meeting will be the first test of how much that dissent matters.</p>
          </div>
        ) : (
          <p style={{ fontSize: 14, color: 'var(--ink-muted)', fontStyle: 'italic' }}>
            Full text isn’t available for this story yet — the TL;DR above covers what Cura’s sources report.
          </p>
        )}

        {/* Citation footnotes — real articles when the pipeline provides them */}
        {story.citations ? (
          <div style={{ marginTop: 36, padding: '20px 0', borderTop: '1px solid var(--paper-rule)' }}>
            <div className="mono" style={{ fontSize: 10, letterSpacing: '0.22em', color: 'var(--ink-muted)', textTransform: 'uppercase', marginBottom: 14 }}>Sources</div>
            <ol style={{ margin: 0, padding: '0 0 0 20px', fontSize: 13, lineHeight: 1.7, color: 'var(--ink-soft)' }}>
              {story.citations.map((c, i) => (
                <li key={i}>
                  {c.title}. <strong>{c.source}</strong>{' '}
                  {c.url && (
                    <a href={c.url} target="_blank" rel="noreferrer" style={{ color: 'var(--accent)' }}>
                      read original ↗
                    </a>
                  )}
                </li>
              ))}
            </ol>
          </div>
        ) : story.id === 's-fed' ? (
          <div style={{ marginTop: 36, padding: '20px 0', borderTop: '1px solid var(--paper-rule)' }}>
            <div className="mono" style={{ fontSize: 10, letterSpacing: '0.22em', color: 'var(--ink-muted)', textTransform: 'uppercase', marginBottom: 14 }}>Citations</div>
            <ol style={{ margin: 0, padding: '0 0 0 20px', fontSize: 13, lineHeight: 1.7, color: 'var(--ink-soft)' }}>
              <li>Powell, J. (Aug 23). Remarks at Jackson Hole. Federal Reserve <span style={{ color: 'var(--accent)' }}>federalreserve.gov</span></li>
              <li>U.S. Treasury yield curve, 14:32 ET. Bloomberg Terminal data via Cura’s Bloomberg license.</li>
              <li>Reuters survey of FOMC public remarks, Aug 14–23. Reuters.</li>
            </ol>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function ClaimChecker() {
  const [claim, setClaim] = useStateR('');
  const [checking, setChecking] = useStateR(false);
  const [result, setResult] = useStateR(null);

  const examples = [
    'The Fed has officially cut interest rates.',
    'TSMC’s Arizona plant opens in 2025.',
    'Insurers are pulling out of Florida.',
    'Powell promised three rate cuts this year.',
  ];

  const kb = () => (window.allStories ? allStories() : (window.CURA_STORIES || [])).map(s =>
    `• [${s.section}] ${s.headline}. ${s.dek}${s.tldr ? ' ' + s.tldr.join(' ') : ''} (confidence ${s.confidence}/5)`
  ).join('\n');

  // deterministic fallback if the API is unavailable
  const fallback = (c) => {
    const t = c.toLowerCase();
    if (/officially cut|has cut|already cut/.test(t))
      return { verdict: 'CONTRADICTED', confidence: 4, summary: 'No cut has happened. Powell only signalled a likely cut at the September meeting — the FOMC has not yet voted.', evidence: [{ source: 'Reuters', note: '“The time has come for policy to adjust” — a signal, not an action.' }, { source: 'WSJ', note: 'Three FOMC presidents still favour holding.' }] };
    if (/2025/.test(t) && /tsmc|arizona|fab|plant/.test(t))
      return { verdict: 'CONTRADICTED', confidence: 5, summary: 'The Arizona fab has been pushed to 2027, not 2025 — the second delay in 18 months.', evidence: [{ source: 'Cura · 11 sources', note: 'Labor shortages and grid constraints cited.' }] };
    if (/insurer|florida|pulling out|exit/.test(t))
      return { verdict: 'SUPPORTED', confidence: 4, summary: 'Three of the largest U.S. carriers will stop renewing policies in flood-prone Florida counties from January.', evidence: [{ source: 'Cura · 9 sources', note: 'Coastal cities are accelerating seawall plans in response.' }] };
    if (/three (rate )?cuts|promised/.test(t))
      return { verdict: 'UNVERIFIED', confidence: 2, summary: 'No source quotes Powell promising a specific number of cuts. He signalled one likely adjustment; pace remains contested.', evidence: [{ source: 'Reuters survey', note: 'FOMC members publicly disagree on pace.' }] };
    return { verdict: 'UNVERIFIED', confidence: 1, summary: `I can’t ground this claim in today’s ${(window.CURA_STORIES || []).length} stories. Try a claim about one of today’s headlines.`, evidence: [] };
  };

  const check = async () => {
    const c = claim.trim();
    if (!c || checking) return;
    setChecking(true); setResult(null);
    let res = null;
    try {
      if (window.claude && typeof window.claude.complete === 'function') {
        const prompt =
          'You are Cleo’s fact-check engine for the news app Cura. Assess the reader’s CLAIM strictly against TODAY’S SOURCES. ' +
          'Reply with ONLY a JSON object, no prose, of the form: ' +
          '{"verdict":"SUPPORTED|MIXED|UNVERIFIED|CONTRADICTED","confidence":1-5,"summary":"one or two plain sentences","evidence":[{"source":"name","note":"what it says"}]}. ' +
          'If the sources don’t cover it, use UNVERIFIED. Never invent sources or facts.\n\n' +
          'TODAY’S SOURCES:\n' + kb() + '\n\nCLAIM: "' + c + '"\n\nJSON:';
        const raw = await window.claude.complete(prompt);
        const m = raw && raw.match(/\{[\s\S]*\}/);
        if (m) { const p = JSON.parse(m[0]); if (p && p.verdict) res = p; }
      }
    } catch (e) { /* fall through */ }
    if (!res) { await new Promise(r => setTimeout(r, 500)); res = fallback(c); }
    setResult(res); setChecking(false);
  };

  const V = {
    SUPPORTED:    { color: 'var(--green)', label: 'Supported by sources' },
    MIXED:        { color: '#C8854A', label: 'Mixed / partially true' },
    UNVERIFIED:   { color: 'var(--ink-muted)', label: 'Unverified' },
    CONTRADICTED: { color: 'var(--accent)', label: 'Contradicted by sources' },
  };
  const v = result ? (V[result.verdict] || V.UNVERIFIED) : null;

  return (
    <div style={{ background: 'var(--ink)', color: 'var(--paper)', borderRadius: 6, padding: '28px 32px', marginBottom: 36 }}>
      <div className="mono" style={{ fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', color: 'var(--accent-soft)', marginBottom: 12 }}>
        Check a claim · grounded fact-check
      </div>
      <h2 className="serif" style={{ fontSize: 30, lineHeight: 1.1, fontWeight: 600, margin: '0 0 6px' }}>
        Heard something? Have Cleo check it.
      </h2>
      <p style={{ fontSize: 14, color: 'rgba(244,239,230,0.7)', margin: '0 0 20px', maxWidth: '54ch' }}>
        Paste a headline or claim. Cleo weighs it against today’s vetted sources — and tells you plainly when she can’t.
      </p>

      <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
        <input
          value={claim}
          onChange={e => setClaim(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && check()}
          placeholder="e.g. The Fed cut rates this week"
          style={{
            flex: 1, background: 'rgba(244,239,230,0.06)', border: '1px solid rgba(244,239,230,0.2)',
            borderRadius: 6, padding: '12px 16px', color: 'var(--paper)', fontSize: 15, fontFamily: 'inherit', outline: 'none',
          }}
        />
        <button onClick={check} disabled={checking} style={{
          background: 'var(--paper)', color: 'var(--ink)', border: 'none', borderRadius: 6,
          padding: '0 22px', fontSize: 14, fontWeight: 600, cursor: checking ? 'default' : 'pointer',
          display: 'flex', alignItems: 'center', gap: 8, fontFamily: 'inherit',
        }}>
          <CIcon name="verify" size={15} /> {checking ? 'Checking…' : 'Check'}
        </button>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: result || checking ? 24 : 0 }}>
        {examples.map((ex, i) => (
          <button key={i} onClick={() => setClaim(ex)} style={{
            fontSize: 12, padding: '6px 10px', borderRadius: 14, cursor: 'pointer', fontFamily: 'inherit',
            background: 'transparent', border: '1px solid rgba(244,239,230,0.2)', color: 'rgba(244,239,230,0.75)',
          }}>{ex}</button>
        ))}
      </div>

      {checking && (
        <div className="mono" style={{ fontSize: 11, letterSpacing: '0.18em', textTransform: 'uppercase', color: 'var(--accent-soft)' }}>
          Cleo is weighing the sources…
        </div>
      )}

      {result && v && (
        <div style={{ background: 'var(--paper)', color: 'var(--ink)', borderRadius: 6, padding: '22px 24px', borderLeft: `4px solid ${v.color}` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
            <span style={{
              fontFamily: 'JetBrains Mono, monospace', fontSize: 11, letterSpacing: '0.18em', textTransform: 'uppercase',
              fontWeight: 600, color: v.color,
            }}>{v.label}</span>
            <span style={{ width: 1, height: 14, background: 'var(--paper-rule)' }} />
            <ConfBar level={result.confidence} label={`${result.confidence}/5 confidence`} />
          </div>
          <p className="serif" style={{ fontSize: 18, lineHeight: 1.5, margin: '0 0 16px' }}>{result.summary}</p>
          {result.evidence && result.evidence.length > 0 && (
            <div style={{ borderTop: '1px solid var(--paper-rule)', paddingTop: 14 }}>
              <div className="mono" style={{ fontSize: 9, letterSpacing: '0.22em', textTransform: 'uppercase', color: 'var(--ink-muted)', marginBottom: 10 }}>What the sources say</div>
              {result.evidence.map((ev, i) => (
                <div key={i} style={{ display: 'flex', gap: 12, marginBottom: 8, fontSize: 13, lineHeight: 1.5 }}>
                  <span className="mono" style={{ fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--accent)', minWidth: 110, flexShrink: 0 }}>{ev.source}</span>
                  <span style={{ color: 'var(--ink-soft)' }}>{ev.note}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function VerifyView({ goBack }) {
  // Live edition: compare the most contested story, framed per-source by the
  // stance classifier. Prototype: the canned Fed comparison.
  const live = window.CURA_LIVE && window.CURA_LIVE.compare;
  const cols = live ? live.sources : COMPARE_SOURCES;
  const subject = live ? live.headline : 'Fed signals first rate cut of the year';
  const subjectConf = live ? live.confidence : 4;
  const subjectConfLabel = live ? live.confidenceLabel : 'Well-sourced';
  const agree = live ? live.agree : [
    'Powell’s exact phrase: “The time has come for policy to adjust.”',
    '2-yr Treasury yield fell 14 bps.',
    'FOMC meets Sept 17–18.',
  ];
  const differ = live ? live.differ : [
    'Reuters leads with the signal; WSJ leads with dissent.',
    'Bloomberg foregrounds market reaction.',
    'Only WSJ names dissenters by name in the lead.',
  ];
  return (
    <div className="scroll-area">
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '32px 36px 80px' }}>
        <button className="btn btn-ghost" onClick={goBack} style={{ marginBottom: 20 }}>← Back</button>

        <SectionTag>Verify · grounded fact-check</SectionTag>
        <h1 className="serif" style={{ fontSize: 36, lineHeight: 1.1, fontWeight: 600, margin: '0 0 24px', letterSpacing: '-0.01em' }}>
          Two ways to check the record.
        </h1>

        {/* 1. Active claim checker */}
        <ClaimChecker />

        {/* 2. Source comparison */}
        <SectionTag>The same story, {cols.length} framings</SectionTag>
        <p style={{ fontSize: 16, color: 'var(--ink-soft)', margin: '0 0 24px', maxWidth: '60ch' }}>
          {live
            ? 'Cura compared how each source frames today’s most contested story. Read the leads side-by-side.'
            : 'Cura ran the same primary fact set through three independent outlets. Read the leads side-by-side.'}
        </p>

        {/* The story being compared */}
        <div style={{
          padding: '14px 18px', background: 'var(--paper-2)', borderRadius: 4,
          marginBottom: 28, display: 'flex', alignItems: 'center', gap: 16,
        }}>
          <div className="mono" style={{ fontSize: 10, letterSpacing: '0.22em', color: 'var(--ink-muted)' }}>SUBJECT</div>
          <div style={{ flex: 1, fontFamily: 'Fraunces, serif', fontSize: 17, fontWeight: 600 }}>
            {subject}
          </div>
          <ConfBar level={subjectConf} label={subjectConfLabel} />
        </div>

        <div data-tour="verify-compare" style={{ display: 'grid', gridTemplateColumns: `repeat(${cols.length},1fr)`, gap: 16 }}>
          {cols.map(src => (
            <div key={src.name} className="compare-col">
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 14 }}>
                <span className="serif" style={{ fontSize: 22, fontWeight: 600 }}>{src.name}</span>
                <span style={{
                  fontFamily: 'JetBrains Mono, monospace', fontSize: 9,
                  letterSpacing: '0.22em', textTransform: 'uppercase',
                  color: src.leanColor, border: `1px solid ${src.leanColor}55`,
                  padding: '2px 6px', borderRadius: 2,
                }}>{src.lean}</span>
              </div>
              <h3 className="serif" style={{ fontSize: 18, lineHeight: 1.25, fontWeight: 600, margin: '0 0 12px' }}>
                {src.headline}
              </h3>
              <p style={{ fontSize: 13, lineHeight: 1.55, color: 'var(--ink-soft)', margin: '0 0 14px' }}>{src.framing}</p>
              <blockquote style={{
                margin: 0, padding: '10px 14px', background: 'var(--paper-2)',
                borderLeft: '2px solid var(--accent)', fontFamily: 'Fraunces, serif',
                fontSize: 14, lineHeight: 1.5, fontStyle: 'italic',
              }}>{src.quote}</blockquote>

              <div style={{ marginTop: 16 }}>
                <div className="mono" style={{ fontSize: 9, letterSpacing: '0.22em', color: 'var(--ink-muted)', textTransform: 'uppercase', marginBottom: 8 }}>Cura’s read</div>
                <ul style={{ margin: 0, padding: '0 0 0 16px', fontSize: 12, lineHeight: 1.55, color: 'var(--ink-soft)' }}>
                  {src.notes.map((n, i) => <li key={i}>{n}</li>)}
                </ul>
              </div>
            </div>
          ))}
        </div>

        {/* What's the same / different */}
        <div style={{
          marginTop: 28, padding: 24, background: 'var(--ink)', color: 'var(--paper)',
          borderRadius: 4, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 32,
        }}>
          <div>
            <div className="mono" style={{ fontSize: 10, letterSpacing: '0.22em', color: 'rgba(244,239,230,0.6)', textTransform: 'uppercase', marginBottom: 10 }}>What the sources agree on</div>
            <ul style={{ margin: 0, padding: '0 0 0 16px', fontSize: 14, lineHeight: 1.6 }}>
              {agree.map((line, i) => <li key={i}>{line}</li>)}
            </ul>
          </div>
          <div>
            <div className="mono" style={{ fontSize: 10, letterSpacing: '0.22em', color: 'rgba(244,239,230,0.6)', textTransform: 'uppercase', marginBottom: 10 }}>Where they differ</div>
            <ul style={{ margin: 0, padding: '0 0 0 16px', fontSize: 14, lineHeight: 1.6 }}>
              {differ.map((line, i) => <li key={i}>{line}</li>)}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { ReadView, StoryDetailView, VerifyView });
