// PROVENANCE: ORIGINAL (bespoke to Cura) - React/JSX interface component; data shapes in web/README.md. Third-party (CDN): React 18, ReactDOM, Babel standalone. See PROVENANCE.md.
// Cura - App root: state + router + mount

const { useState: useStateA, useEffect: useEffectA } = React;

if (window.CURA_LIVE) document.title = 'Cura — Today';

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

    </div>
  );
}

// Mount: the app fills the viewport. `cura serve` (and the static export)
// inline the live edition as CURA_LIVE before this module runs.
function CuraStage() {
  return (
    <div style={{ width: '100vw', height: '100vh' }}>
      <CuraApp />
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<CuraStage />);
