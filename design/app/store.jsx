// PROVENANCE: ORIGINAL (bespoke to Cura) - React/JSX prototype component; the product spec (see design/HANDOFF.md). Third-party (CDN): React 18, ReactDOM, Babel standalone. See PROVENANCE.md.
// Cura - shared client store (Saved bookmarks + personalization signals)
// Lightweight global + React hooks, persisted to localStorage and broadcast via
// CustomEvents so any view re-renders when state changes.

const CuraStore = {
  _read(key, fallback) {
    try { const v = JSON.parse(localStorage.getItem(key)); return v == null ? fallback : v; }
    catch (e) { return fallback; }
  },
  _write(key, val, evt) {
    try { localStorage.setItem(key, JSON.stringify(val)); } catch (e) {}
    window.dispatchEvent(new CustomEvent(evt, { detail: val }));
  },

  // ── Saved stories ──
  getSaved() { return this._read('cura.saved', []); },
  toggleSaved(id) {
    const s = this.getSaved().slice();
    const i = s.indexOf(id);
    if (i >= 0) s.splice(i, 1); else s.unshift(id);
    this._write('cura.saved', s, 'cura-saved');
    return s;
  },
  isSaved(id) { return this.getSaved().includes(id); },

  // ── Personalization signals ──
  defaultSignals: {
    topics: { Economy: true, Technology: true, Climate: true, World: true, Politics: true, Health: false, Arts: true, Sports: false, Science: false },
    sources: { Reuters: true, BBC: true, 'CNA': true, 'Straits Times': true, Bloomberg: true, WSJ: true, Reddit: false, X: false },
    cadence: 'daily',          // realtime | daily | weekly
    defaultFormat: 'read',     // read | listen | experience
    autoplayBrief: false,
    showConfidence: true,
    interests: '',             // the reader's own words, from onboarding
    keywords: [],              // queryable interests parsed from `interests`
  },
  getSignals() {
    const defaults = Object.assign({}, this.defaultSignals);
    // Live edition: the source chips reflect what the pipeline actually tracks
    if (window.CURA_LIVE && window.CURA_LIVE.sources) {
      const sources = {};
      window.CURA_LIVE.sources.forEach((name) => { sources[name] = true; });
      defaults.sources = sources;
    }
    return Object.assign({}, defaults, this._read('cura.signals', {}));
  },
  setSignal(patch) {
    const next = Object.assign({}, this.getSignals(), patch);
    this._write('cura.signals', next, 'cura-signals');
    return next;
  },
};
window.CuraStore = CuraStore;

window.useSaved = function () {
  const [ids, setIds] = React.useState(CuraStore.getSaved());
  React.useEffect(() => {
    const h = (e) => setIds(e.detail);
    window.addEventListener('cura-saved', h);
    return () => window.removeEventListener('cura-saved', h);
  }, []);
  return { ids, toggle: (id) => CuraStore.toggleSaved(id), has: (id) => ids.includes(id) };
};

window.useSignals = function () {
  const [sig, setSig] = React.useState(CuraStore.getSignals());
  React.useEffect(() => {
    const h = (e) => setSig(e.detail);
    window.addEventListener('cura-signals', h);
    return () => window.removeEventListener('cura-signals', h);
  }, []);
  return { signals: sig, set: (patch) => CuraStore.setSignal(patch) };
};
