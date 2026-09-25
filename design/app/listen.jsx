// PROVENANCE: ORIGINAL (bespoke to Cura) - React/JSX prototype component; the product spec (see design/HANDOFF.md). Third-party (CDN): React 18, ReactDOM, Babel standalone. Narration via the browser Web Speech API (speechSynthesis). See PROVENANCE.md.
// Cura - Listen view (audio briefings) - LIVE
// Real narration via the Web Speech API (SpeechSynthesis), a waveform that
// animates with playback, and a transcript that highlights the spoken line
// and lets you tap any line to jump there.

const { useState: useStateL, useEffect: useEffectL, useRef: useRefL, useCallback: useCallbackL } = React;

/* ---------- helpers ---------- */
function fmtTime(s) {
  s = Math.max(0, Math.round(s));
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return m + ':' + String(sec).padStart(2, '0');
}

// Estimate a believable duration per segment from its word count.
function buildTimeline(segments, rate) {
  const starts = [];
  let acc = 0;
  const durs = segments.map(seg => {
    const words = seg.text.trim().split(/\s+/).length;
    const d = Math.max(2.2, words / (2.7 * rate)); // ~2.7 words/sec at 1x
    starts.push(acc);
    acc += d;
    return d;
  });
  return { starts, durs, total: acc };
}

/* ---------- narration controller ---------- */
function useNarration(segments) {
  // Server-rendered neural narration (cura serve --neural-tts): one WAV per
  // segment, same indices as the transcript, so sync/seek work unchanged.
  // Absent or mismatched -> the Web Speech baseline.
  const audioUrls = (window.CURA_AUDIO && Array.isArray(window.CURA_AUDIO)
    && window.CURA_AUDIO.length === segments.length) ? window.CURA_AUDIO : null;
  const engine = audioUrls ? 'neural' : 'webspeech';
  const supported = !!audioUrls
    || (typeof window !== 'undefined' && 'speechSynthesis' in window);
  const [current, setCurrent] = useStateL(0);
  const [playing, setPlaying] = useStateL(false);
  const [rate, setRate] = useStateL(1);
  const [ended, setEnded] = useStateL(false);

  const currentRef = useRefL(0);
  const playingRef = useRefL(false);
  const rateRef = useRefL(1);
  const genRef = useRefL(0);
  const voiceRef = useRefL(null);
  const audioRef = useRefL(null);

  useEffectL(() => { currentRef.current = current; }, [current]);
  useEffectL(() => { playingRef.current = playing; }, [playing]);
  useEffectL(() => { rateRef.current = rate; }, [rate]);

  // Pick a pleasant English voice once voices are available.
  useEffectL(() => {
    if (!supported) return;
    const pick = () => {
      const vs = window.speechSynthesis.getVoices();
      if (!vs.length) return;
      voiceRef.current =
        vs.find(v => /^en(-|_)?(US|GB)/i.test(v.lang) && /(samantha|female|google us english|aria|jenny|libby|sonia)/i.test(v.name)) ||
        vs.find(v => /^en(-|_)?US/i.test(v.lang)) ||
        vs.find(v => /^en/i.test(v.lang)) ||
        vs[0];
    };
    pick();
    window.speechSynthesis.onvoiceschanged = pick;
    return () => { try { window.speechSynthesis.onvoiceschanged = null; } catch (e) {} };
  }, [supported]);

  const stopSpeech = useCallbackL(() => {
    genRef.current++;
    if (audioRef.current) {
      try { audioRef.current.pause(); } catch (e) {}
      audioRef.current = null;
    }
    if ('speechSynthesis' in window) { try { window.speechSynthesis.cancel(); } catch (e) {} }
  }, []);

  const speakFrom = useCallbackL((startIdx) => {
    if (!supported) return;
    const gen = ++genRef.current;
    if (audioRef.current) { try { audioRef.current.pause(); } catch (e) {} audioRef.current = null; }
    if ('speechSynthesis' in window) { try { window.speechSynthesis.cancel(); } catch (e) {} }
    let i = startIdx;
    const finished = () => {
      setPlaying(false); playingRef.current = false; setEnded(true);
    };
    const advance = () => {
      if (gen !== genRef.current || !playingRef.current) return;
      i += 1; speakNext();
    };
    const speakNext = () => {
      if (gen !== genRef.current || !playingRef.current) return;
      if (i >= segments.length) { finished(); return; }
      setCurrent(i); currentRef.current = i;
      if (audioUrls) {
        const a = new Audio(audioUrls[i]);
        a.playbackRate = rateRef.current;
        audioRef.current = a;
        a.onended = advance;
        a.onerror = advance;
        a.play().catch(advance);
        return;
      }
      const u = new SpeechSynthesisUtterance(segments[i].text);
      if (voiceRef.current) u.voice = voiceRef.current;
      u.rate = rateRef.current; u.pitch = 1; u.volume = 1;
      u.onend = advance;
      u.onerror = advance;
      try { window.speechSynthesis.speak(u); } catch (e) {}
    };
    // tiny delay lets a preceding cancel() settle (Chrome quirk)
    setTimeout(speakNext, 60);
  }, [segments, supported, audioUrls]);

  const play = useCallbackL(() => {
    setEnded(false);
    setPlaying(true); playingRef.current = true;
    if (supported) speakFrom(currentRef.current);
  }, [speakFrom, supported]);

  const pause = useCallbackL(() => {
    setPlaying(false); playingRef.current = false;
    stopSpeech();
  }, [stopSpeech]);

  const toggle = useCallbackL(() => { (playingRef.current ? pause : play)(); }, [play, pause]);

  const seek = useCallbackL((idx) => {
    const clamped = Math.max(0, Math.min(segments.length - 1, idx));
    setEnded(false);
    setCurrent(clamped); currentRef.current = clamped;
    if (playingRef.current) speakFrom(clamped);
  }, [segments, speakFrom]);

  const changeRate = useCallbackL((r) => {
    setRate(r); rateRef.current = r;
    if (audioRef.current) {
      audioRef.current.playbackRate = r; // audio adjusts live, no restart
    } else if (playingRef.current) {
      speakFrom(currentRef.current);     // re-speak current at new rate
    }
  }, [speakFrom]);

  useEffectL(() => () => { stopSpeech(); }, [stopSpeech]);

  return { current, playing, rate, ended, supported, engine, play, pause, toggle, seek, changeRate };
}

/* ---------- live waveform ---------- */
function LiveWaveform({ bars = 72, progress = 0, playing, onScrub }) {
  const [tick, setTick] = useStateL(0);
  const raf = useRefL(null);
  useEffectL(() => {
    if (!playing) return;
    let t0 = performance.now();
    const loop = (t) => { setTick((t - t0) / 1000); raf.current = requestAnimationFrame(loop); };
    raf.current = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf.current);
  }, [playing]);

  const items = Array.from({ length: bars }).map((_, i) => {
    // a stable profile + a live shimmer near nothing-special positions
    const base = 10 + Math.abs(Math.sin(i * 0.45) * 16 + Math.cos(i * 0.17) * 10);
    const live = playing ? Math.abs(Math.sin(tick * 6 + i * 0.6)) * 14 : 0;
    const h = Math.min(46, base + live);
    const played = i / bars <= progress;
    return { h, played };
  });

  return (
    <div
      className="waveform"
      style={{ cursor: 'pointer' }}
      onClick={(e) => {
        if (!onScrub) return;
        const r = e.currentTarget.getBoundingClientRect();
        onScrub(Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)));
      }}
    >
      {items.map((b, i) => (
        <i key={i} className={b.played ? 'played' : ''} style={{
          height: b.h,
          background: b.played ? 'var(--accent)' : 'rgba(244,239,230,0.25)',
        }} />
      ))}
    </div>
  );
}

/* ---------- the view ---------- */
function ListenView({ openCleo }) {
  const segments = window.CURA_BRIEFING;
  const nar = useNarration(segments);
  const live = !!window.CURA_LIVE;
  const stories = window.CURA_STORIES || [];

  // Live edition: the episode card reflects today's actual briefing;
  // prototype keeps the canned episode.
  const canned = window.CURA_EPISODES.find(e => e.id === 'e-brief') || window.CURA_EPISODES[0];
  let current = canned;
  if (live && stories.length) {
    const confidence = Math.round(
      stories.reduce((a, s) => a + s.confidence, 0) / stories.length);
    const labelCounts = {};
    stories.forEach(s => { labelCounts[s.confidenceLabel] = (labelCounts[s.confidenceLabel] || 0) + 1; });
    const confidenceLabel = Object.keys(labelCounts)
      .sort((a, b) => labelCounts[b] - labelCounts[a])[0];
    current = {
      id: 'e-live-brief', type: 'BRIEF', confidence, confidenceLabel,
      title: 'Your Daily Brief — ' + editionMeta().dateline.replace(' · ', ', '),
    };
  }

  const [layout, setLayout] = useStateL(
    (window.__curaTweaks && window.__curaTweaks.listenLayout) || 'immersive'
  );
  useEffectL(() => {
    const onTw = (e) => { if (e.detail && e.detail.listenLayout) setLayout(e.detail.listenLayout); };
    window.addEventListener('cura-tweak', onTw);
    return () => window.removeEventListener('cura-tweak', onTw);
  }, []);

  // Timeline + elapsed clock (decoupled from speech engine timing, but believable)
  const { starts, total } = buildTimeline(segments, nar.rate);
  const [elapsed, setElapsed] = useStateL(0);
  useEffectL(() => { setElapsed(starts[nar.current] || 0); }, [nar.current]); // eslint-disable-line
  useEffectL(() => {
    if (!nar.playing) return;
    const id = setInterval(() => {
      setElapsed(e => {
        const cap = (nar.current + 1 < starts.length) ? starts[nar.current + 1] : total;
        return Math.min(cap, e + 0.1 * nar.rate);
      });
    }, 100);
    return () => clearInterval(id);
  }, [nar.playing, nar.current, nar.rate]); // eslint-disable-line
  const progress = total ? Math.min(1, elapsed / total) : 0;

  // Auto-scroll the active transcript line into view inside its own container.
  const txRef = useRefL(null);
  const lineRefs = useRefL({});
  useEffectL(() => {
    const c = txRef.current, el = lineRefs.current[nar.current];
    if (!c || !el) return;
    const target = el.offsetTop - c.clientHeight / 2 + el.clientHeight / 2;
    c.scrollTo({ top: Math.max(0, target), behavior: 'smooth' });
  }, [nar.current]);

  const rates = [0.75, 1, 1.25, 1.5];

  /* shared: now-playing player block */
  const player = (compact) => (
    <div data-tour="listen-player" style={{
      background: 'var(--ink)', color: 'var(--paper)',
      borderRadius: 6, padding: compact ? '22px 24px' : '32px 36px',
      display: 'grid',
      gridTemplateColumns: compact ? '1fr' : '180px 1fr',
      gap: compact ? 18 : 32, alignItems: 'center',
    }}>
      {!compact && (
        <div style={{
          aspectRatio: '1/1',
          background: 'linear-gradient(135deg, var(--accent) 0%, #2A3548 100%)',
          borderRadius: 4, position: 'relative', overflow: 'hidden',
        }}>
          <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(circle at 30% 30%, rgba(244,239,230,0.2), transparent 60%)' }} />
          <div style={{ position: 'absolute', bottom: 14, left: 14, right: 14, fontFamily: 'Fraunces, serif', fontSize: 22, fontWeight: 600, lineHeight: 1.1, color: 'var(--paper)' }}>Daily<br />Brief</div>
          <div className="mono" style={{ position: 'absolute', top: 14, left: 14, fontSize: 9, letterSpacing: '0.22em', color: 'rgba(244,239,230,0.7)' }}>
            {live ? 'CURA · ' + editionMeta().date.toUpperCase() : 'CURA · EP. 089'}
          </div>
          {nar.playing && (
            <div style={{ position: 'absolute', bottom: 14, right: 14, display: 'flex', gap: 3, alignItems: 'flex-end', height: 18 }}>
              {[0, 1, 2].map(i => (
                <span key={i} style={{
                  width: 3, background: 'var(--paper)', borderRadius: 2,
                  animation: `eq 0.9s ${i * 0.15}s infinite ease-in-out`,
                }} />
              ))}
            </div>
          )}
        </div>
      )}

      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8, flexWrap: 'wrap' }}>
          <span className="mono" style={{ fontSize: 10, letterSpacing: '0.22em', color: 'var(--accent-soft)' }}>
            {nar.playing ? 'NOW PLAYING' : nar.ended ? 'FINISHED' : 'READY'} · {current.type}
          </span>
          <ConfBar level={current.confidence} label={current.confidenceLabel || 'Well-sourced'} max={5} />
        </div>
        <h2 className="serif" style={{ fontSize: compact ? 22 : 28, lineHeight: 1.15, fontWeight: 600, margin: '0 0 4px' }}>
          {current.title}
        </h2>
        <div style={{ fontSize: 12, color: 'rgba(244,239,230,0.65)', marginBottom: 18 }}>
          {nar.engine === 'neural' ? 'Cleo · neural voice (Coqui)'
            : nar.supported ? 'Narrated live by Cleo' : 'Cleo — calibrated voice'} · {fmtTime(total)}
        </div>

        <LiveWaveform progress={progress} playing={nar.playing}
          onScrub={(f) => {
            // map fraction to nearest segment by start time
            let idx = 0;
            for (let i = 0; i < starts.length; i++) if (starts[i] <= f * total) idx = i;
            nar.seek(idx);
          }} />
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'rgba(244,239,230,0.6)', margin: '8px 0 18px' }}>
          <span className="mono">{fmtTime(elapsed)}</span>
          <span className="mono">{fmtTime(total)}</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
          <button className="btn" style={{ background: 'transparent', borderColor: 'rgba(244,239,230,0.2)', color: 'var(--paper)' }}
            onClick={() => nar.seek(nar.current - 1)} title="Previous line">
            <CIcon name="skip-back" size={14} />
          </button>
          <button
            onClick={nar.toggle}
            className={nar.playing ? 'cura-pulse' : ''}
            style={{
              width: 56, height: 56, borderRadius: '50%',
              background: 'var(--paper)', color: 'var(--ink)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              border: 'none', cursor: 'pointer', flexShrink: 0,
            }}>
            <CIcon name={nar.playing ? 'pause' : 'play'} size={20} />
          </button>
          <button className="btn" style={{ background: 'transparent', borderColor: 'rgba(244,239,230,0.2)', color: 'var(--paper)' }}
            onClick={() => nar.seek(nar.current + 1)} title="Next line">
            <CIcon name="skip-fwd" size={14} />
          </button>

          {/* Speed control */}
          <div style={{ display: 'flex', gap: 4, marginLeft: 4 }}>
            {rates.map(r => (
              <button key={r} onClick={() => nar.changeRate(r)} className="mono" style={{
                fontSize: 11, padding: '6px 8px', borderRadius: 4, cursor: 'pointer',
                border: '1px solid rgba(244,239,230,0.2)',
                background: nar.rate === r ? 'var(--paper)' : 'transparent',
                color: nar.rate === r ? 'var(--ink)' : 'rgba(244,239,230,0.7)',
                fontFamily: 'JetBrains Mono, monospace',
              }}>{r}×</button>
            ))}
          </div>

          <div style={{ flex: 1 }} />
          <button className="btn" style={{ background: 'transparent', borderColor: 'rgba(244,239,230,0.2)', color: 'var(--paper)' }} onClick={openCleo}>
            <CIcon name="sparkle" size={13} /> Ask about this
          </button>
        </div>

        {!nar.supported && (
          <div style={{ marginTop: 14, fontSize: 11, color: 'var(--accent-soft)', lineHeight: 1.5 }}>
            Live narration needs a browser with speech support. The transcript follows along in demo mode.
          </div>
        )}
      </div>
    </div>
  );

  /* transcript block */
  const transcript = (
    <div>
      <SectionTag>Transcript · follows the audio</SectionTag>
      <div ref={txRef} style={{
        maxHeight: layout === 'transcript' ? 520 : 420,
        overflowY: 'auto', paddingRight: 12,
        maskImage: 'linear-gradient(to bottom, transparent, #000 6%, #000 94%, transparent)',
        WebkitMaskImage: 'linear-gradient(to bottom, transparent, #000 6%, #000 94%, transparent)',
      }}>
        <div style={{ padding: '14px 0' }}>
          {segments.map((seg, i) => {
            const active = i === nar.current;
            const past = i < nar.current;
            return (
              <div key={i}>
                {seg.chapter && (
                  <div className="mono" style={{
                    fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase',
                    color: 'var(--ink-muted)', margin: i === 0 ? '0 0 14px' : '22px 0 12px',
                    display: 'flex', alignItems: 'center', gap: 10,
                  }}>
                    <span style={{ width: 16, height: 1, background: 'var(--paper-rule)' }} />
                    {seg.chapter}
                  </div>
                )}
                <p
                  ref={el => { lineRefs.current[i] = el; }}
                  onClick={() => nar.seek(i)}
                  className="serif"
                  style={{
                    margin: '0 0 12px', cursor: 'pointer',
                    fontSize: active ? 21 : 17,
                    lineHeight: 1.5,
                    fontWeight: active ? 600 : 400,
                    color: active ? 'var(--ink)' : past ? 'var(--ink-muted)' : 'var(--ink-soft)',
                    borderLeft: active ? '2px solid var(--accent)' : '2px solid transparent',
                    paddingLeft: 14, transition: 'all 0.2s ease',
                  }}
                >
                  {seg.text}
                </p>
              </div>
            );
          })}
        </div>
      </div>
      <div style={{ marginTop: 14, fontSize: 11, color: 'var(--ink-muted)', lineHeight: 1.5 }}>
        Tap any line to jump there. Every segment is bound to its source citations.
      </div>
    </div>
  );

  /* queue block - live: this briefing's chapters (tap to jump the narration
     to that story); prototype: the canned episode queue */
  const chapterMarks = segments
    .map((seg, i) => ({ chapter: seg.chapter, i }))
    .filter(seg => seg.chapter);
  // drop the intro and sign-off chapters; what remains are the stories
  const storyChapters = chapterMarks.length > 2 ? chapterMarks.slice(1, -1) : chapterMarks;

  const queue = live ? (
    <div>
      <SectionTag>In this briefing · tap to jump</SectionTag>
      {storyChapters.map((c, k) => {
        const pos = chapterMarks.findIndex(m => m.i === c.i);
        const end = pos + 1 < chapterMarks.length ? starts[chapterMarks[pos + 1].i] : total;
        const story = stories.find(s => s.headline === c.chapter);
        const isCurrent = nar.current >= c.i
          && (pos + 1 >= chapterMarks.length || nar.current < chapterMarks[pos + 1].i);
        return (
          <div key={c.i} className="story-card"
            onClick={() => { nar.seek(c.i); if (!nar.playing) nar.play(); }}
            style={{
              padding: '16px 0', borderBottom: '1px solid var(--paper-rule)',
              display: 'grid', gridTemplateColumns: '46px 1fr', gap: 14,
            }}>
            <div style={{
              width: 46, height: 46, borderRadius: 4,
              background: isCurrent ? 'var(--accent)' : 'var(--ink)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: 'var(--paper)',
            }}>
              <CIcon name="play" size={14} />
            </div>
            <div>
              <div className="mono" style={{ fontSize: 9, letterSpacing: '0.22em', color: 'var(--ink-muted)', marginBottom: 4, textTransform: 'uppercase' }}>
                {(story ? '§ ' + story.section : 'STORY ' + (k + 1))}
                {' · '}{fmtTime(Math.max(0, end - starts[c.i]))}
                {story && story.contested ? ' · contested' : ''}
              </div>
              <div className="serif" style={{ fontSize: 17, lineHeight: 1.2, fontWeight: 600, marginBottom: 4 }}>{c.chapter}</div>
              {story && story.dek && (
                <div style={{ fontSize: 12, lineHeight: 1.45, color: 'var(--ink-soft)' }}>{story.dek}</div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  ) : (
    <div>
      <SectionTag>Up next · your queue</SectionTag>
      {window.CURA_EPISODES.filter(e => e.id !== current.id).map(e => (
        <div key={e.id} className="story-card" style={{
          padding: '16px 0', borderBottom: '1px solid var(--paper-rule)',
          display: 'grid', gridTemplateColumns: '46px 1fr', gap: 14,
        }}>
          <div style={{
            width: 46, height: 46, borderRadius: 4,
            background: e.type === 'DEEP DIVE' ? 'var(--ink)' : e.type === 'EXPLAINER' ? 'var(--paper-3)' : 'var(--accent)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: e.type === 'EXPLAINER' ? 'var(--ink)' : 'var(--paper)',
          }}>
            <CIcon name="play" size={14} />
          </div>
          <div>
            <div className="mono" style={{ fontSize: 9, letterSpacing: '0.22em', color: 'var(--ink-muted)', marginBottom: 4 }}>
              {e.type} · {e.duration}
            </div>
            <div className="serif" style={{ fontSize: 17, lineHeight: 1.2, fontWeight: 600, marginBottom: 4 }}>{e.title}</div>
            {e.desc && <div style={{ fontSize: 12, lineHeight: 1.45, color: 'var(--ink-soft)' }}>{e.desc}</div>}
          </div>
        </div>
      ))}
    </div>
  );

  return (
    <div className="scroll-area">
      <style>{`@keyframes eq{0%,100%{height:5px}50%{height:18px}}`}</style>
      <div style={{ maxWidth: layout === 'transcript' ? 920 : 1080, margin: '0 auto', padding: '40px 48px 80px' }}>

        <SectionTag>{live ? editionMeta().dateline.split(' · ')[0] : 'Tuesday'} · audio briefings</SectionTag>
        <h1 className="serif" style={{ fontSize: 44, lineHeight: 1.05, fontWeight: 600, letterSpacing: '-0.01em', margin: '0 0 12px' }}>
          Listen as it happens.
        </h1>
        <p style={{ fontSize: 17, color: 'var(--ink-soft)', margin: '0 0 36px', maxWidth: '54ch' }}>
          Daily briefings, deep dives, and explainers — narrated by Cleo, grounded in cited sources.
        </p>

        {layout === 'transcript' ? (
          <>
            <div style={{ marginBottom: 32 }}>{player(true)}</div>
            {transcript}
            <div style={{ marginTop: 48 }}>{queue}</div>
          </>
        ) : (
          <>
            <div style={{ marginBottom: 40 }}>{player(false)}</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1.25fr 1fr', gap: 40 }}>
              {transcript}
              {queue}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

window.ListenView = ListenView;
