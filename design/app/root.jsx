// PROVENANCE: ORIGINAL (bespoke to Cura) - React/JSX prototype component; the product spec (see design/HANDOFF.md). Third-party (CDN): React 18, ReactDOM, Babel standalone. See PROVENANCE.md.
// Cura - App root: state + router + tweaks panel

const { useState: useStateA, useEffect: useEffectA } = React;

if (window.CURA_LIVE) document.title = 'Cura — Today';

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "theme": "paper",
  "density": "comfortable",
  "accent": "#B8331E",
  "listenLayout": "immersive"
}/*EDITMODE-END*/;

function CuraApp() {
  const [view, setView] = useStateA('read');
  const [storyId, setStoryId] = useStateA(null);
  const [readSection, setReadSection] = useStateA(null);
  const [cleoOpen, setCleoOpen] = useStateA(false);
  const [searchOpen, setSearchOpen] = useStateA(false);
  // Onboarding: personalization comes first on a fresh visit (#welcome
  // reopens it; ?welcome=0 suppresses it for demos/screenshots)
  const [welcomeOpen, setWelcomeOpen] = useStateA(() => {
    if (new URLSearchParams(window.location.search).get('welcome') === '0') return false;
    try { return !localStorage.getItem('cura.onboarded'); } catch (e) { return false; }
  });
  // First-edition build still running on the server (cura serve): show the
  // curating state everywhere until the poller fires cura-live-ready.
  const [livePending, setLivePending] = useStateA(!!window.CURA_PENDING);
  useEffectA(() => {
    const onReady = () => setLivePending(false);
    const onPending = () => setLivePending(true);  // on-demand re-curation
    window.addEventListener('cura-live-ready', onReady);
    window.addEventListener('cura-live-pending', onPending);
    return () => {
      window.removeEventListener('cura-live-ready', onReady);
      window.removeEventListener('cura-live-pending', onPending);
    };
  }, []);
  const tweaksResult = window.useTweaks ? window.useTweaks(TWEAK_DEFAULTS) : [TWEAK_DEFAULTS, () => {}];
  const tweaks = tweaksResult[0];
  const setTweak = tweaksResult[1];

  // Apply theme + accent to root
  useEffectA(() => {
    const root = document.querySelector('.app-root');
    if (!root) return;
    if (tweaks.theme === 'dark') root.classList.add('theme-dark');
    else root.classList.remove('theme-dark');
    root.style.setProperty('--accent', tweaks.accent || '#B8331E');
  }, [tweaks.theme, tweaks.accent]);

  // Broadcast tweak values so views (e.g. Listen layout) can react live.
  useEffectA(() => {
    window.__curaTweaks = tweaks;
    window.dispatchEvent(new CustomEvent('cura-tweak', { detail: tweaks }));
  }, [tweaks]);

  // Hash routing (so back/forward + deep links work)
  useEffectA(() => {
    const apply = () => {
      const hash = window.location.hash.replace('#', '');
      if (!hash) { setView('read'); setStoryId(null); setReadSection(null); return; }
      if (hash === 'welcome') {
        setWelcomeOpen(true);
        setView('read'); setStoryId(null); setReadSection(null);
        return;
      }
      if (hash.startsWith('story/')) { setView('story'); setStoryId(hash.slice(6)); return; }
      // Read's topic sections are deep-linkable: #read/World, #read/Technology…
      if (hash.startsWith('read/')) {
        setView('read'); setStoryId(null);
        setReadSection(decodeURIComponent(hash.slice(5)) || null);
        return;
      }
      if (['read', 'listen', 'experience', 'verify', 'saved', 'settings'].includes(hash)) {
        setView(hash);
        setStoryId(null);
        if (hash === 'read') setReadSection(null);
      }
    };
    apply();
    window.addEventListener('hashchange', apply);
    return () => window.removeEventListener('hashchange', apply);
  }, []);

  const goView = (v) => { window.location.hash = '#' + v; };
  const openStory = (id) => { window.location.hash = '#story/' + id; };
  const goBack = () => { window.history.back(); };
  const openCleo = () => setCleoOpen(true);
  const closeCleo = () => setCleoOpen(false);

  // ⌘K / Ctrl-K opens search
  useEffectA(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); setSearchOpen(o => !o); }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  let main = null;
  let breadcrumb = null;
  if (livePending) {
    main = <ReadSkeleton />;
  } else if (view === 'read') {
    main = <ReadView openStory={openStory} openCleo={openCleo} section={readSection} />;
  } else if (view === 'listen') {
    main = <ListenView openCleo={openCleo} />;
  } else if (view === 'experience') {
    main = <ExperienceView openStory={openStory} />;
  } else if (view === 'story') {
    const story = (window.allStories ? allStories() : CURA_STORIES).find(s => s.id === storyId);
    breadcrumb = 'Read · ' + (story ? story.section : 'story');
    main = <StoryDetailView storyId={storyId} goBack={goBack} openCleo={openCleo} />;
  } else if (view === 'verify') {
    main = <VerifyView goBack={goBack} />;
  } else if (view === 'saved') {
    main = <SavedView openStory={openStory} />;
  } else if (view === 'settings') {
    main = <SettingsView />;
  }

  // Sidebar's view should reflect the current top-level view (story → read)
  const sidebarView = (view === 'story') ? 'read' : view;

  return (
    <div className="app-root" style={{ position: 'relative' }}>
      <Sidebar view={sidebarView} setView={goView} />
      <div className="main">
        <TopBar view={view} openCleo={openCleo} breadcrumb={breadcrumb} openSearch={() => setSearchOpen(true)} />
        {/* keyed per route so every view settles in rather than popping */}
        <div key={view + '/' + (storyId || '') + '/' + (readSection || '')}
          className="view-rise"
          style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
          {main}
        </div>
      </div>
      <CleoPanel open={cleoOpen} onClose={closeCleo} />
      {window.SearchPalette && (
        <SearchPalette open={searchOpen} onClose={() => setSearchOpen(false)} openStory={openStory} goView={goView} />
      )}
      {window.OnboardingGate && welcomeOpen && (
        <OnboardingGate onClose={() => {
          setWelcomeOpen(false);
          if (window.location.hash === '#welcome') window.location.hash = '#read';
        }} />
      )}

      {/* Tweaks */}
      {window.TweaksPanel && (
        <TweaksPanel title="Tweaks">
          <TweakSection title="Theme">
            <TweakRadio
              label="Surface"
              value={tweaks.theme}
              options={[
                { value: 'paper', label: 'Paper' },
                { value: 'dark', label: 'Dark' },
              ]}
              onChange={v => setTweak('theme', v)}
            />
            <TweakColor
              label="Accent"
              value={tweaks.accent}
              onChange={v => setTweak('accent', v)}
            />
          </TweakSection>
          <TweakSection title="Listen view">
            <TweakRadio
              label="Layout"
              value={tweaks.listenLayout}
              options={[
                { value: 'immersive', label: 'Immersive' },
                { value: 'transcript', label: 'Transcript' },
              ]}
              onChange={v => setTweak('listenLayout', v)}
            />
          </TweakSection>
          <TweakSection title="Demo">
            <TweakButton onClick={() => window.dispatchEvent(new CustomEvent('cura-start-tour'))}>▶ Guided tour</TweakButton>
          </TweakSection>
          <TweakSection title="Navigate">
            <TweakButton onClick={() => goView('read')}>Read view</TweakButton>
            <TweakButton onClick={() => goView('listen')}>Listen view</TweakButton>
            <TweakButton onClick={() => goView('experience')}>Experience view</TweakButton>
            <TweakButton onClick={() => goView('verify')}>Verify (claim checker)</TweakButton>
            <TweakButton onClick={() => goView('saved')}>Saved</TweakButton>
            <TweakButton onClick={() => goView('settings')}>Settings</TweakButton>
            <TweakButton onClick={() => setSearchOpen(true)}>Open search (⌘K)</TweakButton>
            <TweakButton onClick={openCleo}>Open Cleo</TweakButton>
          </TweakSection>
        </TweaksPanel>
      )}
    </div>
  );
}

// Mount: full-viewport app when served live (`cura serve` injects
// CURA_LIVE); otherwise the design-prototype browser-frame mockup.
function CuraStage() {
  const [w, setW] = useStateA(window.innerWidth);
  const [h, setH] = useStateA(window.innerHeight);
  useEffectA(() => {
    const onR = () => { setW(window.innerWidth); setH(window.innerHeight); };
    window.addEventListener('resize', onR);
    return () => window.removeEventListener('resize', onR);
  }, []);

  if (window.CURA_LIVE || window.CURA_PENDING) {
    return (
      <div style={{ width: '100vw', height: '100vh' }}>
        <CuraApp />
      </div>
    );
  }

  // Fit a 1440x880 frame into the viewport with padding
  const designW = 1440, designH = 880;
  const scale = Math.min((w - 48) / designW, (h - 48) / designH, 1);

  return (
    <div className="stage">
      <div style={{
        width: designW, height: designH,
        transform: `scale(${scale})`,
        transformOrigin: 'center center',
      }}>
        <ChromeWindow
          tabs={[
            { title: 'Cura — Today, Aug 27' },
            { title: 'Reuters' },
            { title: 'WSJ' },
          ]}
          activeIndex={0}
          url="cura.app/today"
          width={designW}
          height={designH}
        >
          <CuraApp />
        </ChromeWindow>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<CuraStage />);
