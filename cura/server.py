# PROVENANCE: ORIGINAL - local web server, background EditionCache, live-data
# injection into the prototype, and the Cleo/editorial endpoints. Third-party:
# http.server (stdlib); the anthropic SDK for the optional Cleo proxy. See PROVENANCE.md.
"""Cura web server - one command to run the whole product locally.

    python -m cura serve                       # live ingestion, opens browser
    python -m cura serve --topics technology   # personalised
    python -m cura serve --input examples/sample_articles.json   # offline demo

Serves the high-fidelity prototype from design/ and injects the live
pipeline output into it:

- `window.CURA_LIVE` is inlined into the page (stories + briefing transcript
  from a real pipeline run) and merged over the canned data after
  app/data.jsx loads, so the UI renders today's edition unchanged.
- `window.claude.complete` (used by Cleo chat and the Verify claim-checker)
  is wired to POST /api/cleo, which proxies to the Anthropic API when
  ANTHROPIC_API_KEY is set. Without a key the prototype's offline "demo
  mode" fallback takes over gracefully.

Endpoints: GET / (app), GET /api/edition (UI-contract JSON),
GET /api/audio/<n>.wav (neural narration), POST /api/brief (on-demand
briefing for chosen topics), POST /api/editorial, POST /api/cleo.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from cura.contracts import Article
from cura.orchestrator import Pipeline
from cura.progress import ProgressReporter, build_printer

DESIGN_DIR = Path(__file__).resolve().parent.parent / "design"
DESKTOP_HTML = "Cura - Desktop.html"
# Cheapest model on the API ($1/$5 per MTok) - Cleo's grounded Q&A is a light
# task, so this keeps per-question cost to fractions of a cent. Override with
# CURA_CLEO_MODEL if you ever want a smarter model.
CLEO_MODEL = os.environ.get("CURA_CLEO_MODEL", "claude-haiku-4-5")

_CLAUDE_SHIM = """<script>
window.claude = {
  complete: async (prompt) => {
    const r = await fetch('/api/cleo', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({prompt}),
    });
    if (!r.ok) throw new Error('cleo backend ' + r.status);
    return (await r.json()).completion;
  },
};
</script>"""

# Must be type="text/babel" so it runs in document order with the other
# babel modules - after data.jsx assigns the canned globals, before the
# views mount in root.jsx.
_LIVE_MERGE = """<script type="text/babel">
if (window.CURA_LIVE) {
  if (window.CURA_LIVE.stories && window.CURA_LIVE.stories.length) {
    window.CURA_STORIES = window.CURA_LIVE.stories;
  }
  if (window.CURA_LIVE.briefing && window.CURA_LIVE.briefing.length) {
    window.CURA_BRIEFING = window.CURA_LIVE.briefing;
  }
  if (window.CURA_LIVE.trends && window.CURA_LIVE.trends.length) {
    window.CURA_TRENDS = window.CURA_LIVE.trends;
  }
  window.CURA_MORE = window.CURA_LIVE.moreStories || [];
  window.CURA_AUDIO = window.CURA_LIVE.audio || null;
}
</script>"""

# First page load while the first edition is still building: the app mounts
# with its curating state and this poller swaps the live data in (and lifts
# CURA_PENDING) the moment the background build lands.
_LIVE_POLL = """<script>
window.CURA_LIVE = null;
window.CURA_PENDING = true;
(function poll() {
  fetch('/api/edition').then(function (r) {
    if (r.status !== 200) throw new Error('building');
    return r.json();
  }).then(function (data) {
    window.CURA_LIVE = data;
    if (data.stories && data.stories.length) window.CURA_STORIES = data.stories;
    if (data.briefing && data.briefing.length) window.CURA_BRIEFING = data.briefing;
    if (data.trends && data.trends.length) window.CURA_TRENDS = data.trends;
    window.CURA_MORE = data.moreStories || [];
    window.CURA_AUDIO = data.audio || null;
    window.CURA_PENDING = false;
    window.dispatchEvent(new CustomEvent('cura-live-ready'));
  }).catch(function () { setTimeout(poll, 2000); });
})();
</script>"""

# On-demand briefing: ask the server to re-run the whole pipeline for a
# topic, show the curating state, and swap the new edition in when its
# `topics` match the request.
_BRIEF_API = """<script>
window.curaRequestBriefing = function (topics) {
  topics = (topics || []).map(function (t) { return String(t).trim(); })
                         .filter(Boolean);
  window.CURA_REQUESTED = topics;
  window.CURA_PENDING = true;
  window.dispatchEvent(new CustomEvent('cura-live-pending'));
  fetch('/api/brief', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({topics: topics}),
  }).then(function () {
    (function poll() {
      fetch('/api/edition').then(function (r) {
        if (r.status !== 200) throw new Error('building');
        return r.json();
      }).then(function (data) {
        const got = JSON.stringify(data.topics || []);
        if (got !== JSON.stringify(topics)) throw new Error('stale');
        window.CURA_LIVE = data;
        if (data.stories && data.stories.length) window.CURA_STORIES = data.stories;
        if (data.briefing && data.briefing.length) window.CURA_BRIEFING = data.briefing;
        if (data.trends && data.trends.length) window.CURA_TRENDS = data.trends;
        window.CURA_MORE = data.moreStories || [];
        window.CURA_AUDIO = data.audio || null;
        window.CURA_PENDING = false;
        window.dispatchEvent(new CustomEvent('cura-live-ready'));
      }).catch(function () { setTimeout(poll, 2500); });
    })();
  });
};
</script>"""


class EditionCache:
    """Builds editions in a background thread; requests never wait.

    `peek()` returns the freshest cached edition immediately - possibly
    slightly stale (a rebuild starts behind the scenes), or None before the
    first build lands, in which case the page shows its curating state and
    polls. With a slow summariser (--abstractive, ~2 min/edition) this is
    the difference between an instant page and a 2-minute blank one."""

    def __init__(self, pipeline: Pipeline | None = None,
                 topics: list[str] | None = None,
                 articles: list[Article] | None = None,
                 ttl_seconds: int = 15 * 60,
                 tts=None):
        # One Pipeline for the server's lifetime, so a heavy stretch model
        # (e.g. --abstractive BART) loads once, not on every refresh.
        self.pipeline = pipeline or Pipeline()
        self.topics = topics
        self.articles = articles  # offline mode when provided
        self.ttl = ttl_seconds
        self.tts = tts  # neural narration engine (synthesize_text) or None
        self._lock = threading.Lock()
        self._edition: dict | None = None
        self._fetched_at = 0.0
        self._building = False
        self._editorial: dict | None = None  # Cleo's editorial, per edition
        self._audio_dir: str | None = None   # current edition's rendered WAVs
        # Live build progress: terminal readout + /api/status loading bar.
        self._status: dict = {"status": "idle", "fraction": 0.0}
        self._print_progress = build_printer()

    def _tracked_sources(self) -> list[str]:
        if self.articles is not None:
            return sorted({a.source for a in self.articles})
        from cura.ingest.reddit import DEFAULT_SUBREDDITS
        from cura.ingest.rss import DEFAULT_FEEDS
        feeds = self.pipeline.feeds or DEFAULT_FEEDS
        return (sorted({f["source"] for f in feeds})
                + [f"Reddit r/{s}" for s in DEFAULT_SUBREDDITS])

    def _render_audio(self, briefing) -> tuple[list[str], str] | None:
        """One WAV per briefing segment, so the Listen view keeps its
        sentence-level transcript sync and chapter seeking. Any failure
        degrades to no audio - the UI falls back to Web Speech."""
        import shutil
        import tempfile
        out = tempfile.mkdtemp(prefix="cura-audio-")
        urls = []
        for i, seg in enumerate(briefing.segments):
            try:
                self.tts.synthesize_text(seg.text, os.path.join(out, f"{i:03d}.wav"))
            except Exception as exc:
                print(f"[cura] neural narration failed on segment {i} "
                      f"({exc!r}) — falling back to Web Speech")
                shutil.rmtree(out, ignore_errors=True)
                return None
            urls.append(f"/api/audio/{i:03d}.wav")
        return urls, out

    def request(self, topics: list[str] | None) -> None:
        """On-demand briefing: re-run the whole pipeline for `topics`
        (None/empty -> back to the default edition). Non-blocking - the UI
        shows its curating state and polls until the new edition lands."""
        with self._lock:
            self.topics = topics or None
            self._fetched_at = 0.0  # stale -> prewarm rebuilds now
        self.prewarm()

    def _progress_plan(self) -> list[tuple]:
        """The stages this build will actually run, with wall-clock weights -
        full-text fetch and narration dominate, so they get the wide slots.
        Expansion/full-text are live-only; narration only when a TTS engine
        is wired."""
        live = self.articles is None
        plan = [("ingest", "Scanning sources", 3),
                ("dedupe", "Removing duplicates", 1),
                ("cluster", "Clustering events", 1)]
        if live:
            plan += [("expand", "Expanding coverage", 2),
                     ("fulltext", "Reading full articles", 3)]
        plan += [("summarize", "Summarising", 2),
                 ("stance", "Classifying stance", 2),
                 ("assemble", "Assembling briefing", 1)]
        if self.tts is not None:
            plan.append(("narrate", "Narrating audio", 6))
        return plan

    def _progress_sink(self, state: dict) -> None:
        with self._lock:
            self._status = state
        self._print_progress(state)

    def status(self) -> dict:
        """Latest build-progress snapshot for /api/status (a copy, so callers
        can serialise it without holding the lock)."""
        with self._lock:
            return dict(self._status)

    def _build(self) -> dict:
        topics = self.topics  # snapshot: a request() mid-build re-triggers
        reporter = ProgressReporter(self._progress_plan(),
                                    sink=self._progress_sink)
        briefing, report = self.pipeline.run(topics=topics,
                                             articles=self.articles,
                                             progress=reporter)
        edition = briefing.to_ui_dict()
        edition["scannedArticles"] = next(
            (s.items for s in report.stages if s.name == "ingest"), None)
        edition["sources"] = self._tracked_sources()
        edition["topics"] = topics or []
        edition["builtAt"] = int(time.time())
        audio = None
        if self.tts is not None:
            reporter.begin("narrate")
            t0 = time.time()
            audio = self._render_audio(briefing)
            reporter.complete("narrate", len(audio[0]) if audio else 0)
            if audio:
                edition["audio"] = audio[0]
                print(f"[cura] narration rendered: {len(audio[0])} segments "
                      f"in {time.time() - t0:.1f}s")
        with self._lock:
            self._edition = edition
            # A request() that changed topics mid-build leaves this build
            # stale, so the next prewarm rebuilds with the new topics.
            self._fetched_at = time.time() if self.topics == topics else 0.0
            self._editorial = None  # new edition -> editorial must be re-unlocked
            if audio:
                old, self._audio_dir = self._audio_dir, audio[1]
        if audio and old:
            import shutil
            shutil.rmtree(old, ignore_errors=True)
        reporter.finish()
        print(f"[cura] edition refreshed: {len(briefing.stories)} stories, "
              f"{report.total_seconds:.1f}s\n{report.table()}")
        return edition

    def audio_path(self, name: str) -> str | None:
        """Filesystem path for /api/audio/<name>, if it belongs to the
        current edition."""
        with self._lock:
            base = self._audio_dir
        if not base or not re.fullmatch(r"\d{3}\.wav", name):
            return None
        path = os.path.join(base, name)
        return path if os.path.exists(path) else None

    def _build_in_background(self) -> None:
        try:
            self._build()
        except Exception as exc:
            print(f"[cura] edition build failed: {exc!r} — retrying on next request")
            with self._lock:
                # Don't leave the loading bar frozen mid-build; the /api/edition
                # poller keeps retrying and the next prewarm rebuilds.
                self._status = {"status": "error", "fraction": 0.0,
                                "label": "Build hit an error — retrying"}
        finally:
            with self._lock:
                self._building = False
        self.prewarm()  # no-op unless a request() landed mid-build

    def prewarm(self) -> None:
        """Start a background build when the cache is missing or stale."""
        with self._lock:
            stale = (self._edition is None
                     or time.time() - self._fetched_at > self.ttl)
            if self._building or not stale:
                return
            self._building = True
        threading.Thread(target=self._build_in_background, daemon=True).start()

    def peek(self) -> dict | None:
        """Freshest edition without waiting; None before the first build."""
        with self._lock:
            edition = self._edition
        self.prewarm()
        return edition

    def get_editorial(self) -> dict | None:
        with self._lock:
            return self._editorial

    def set_editorial(self, editorial: dict) -> None:
        """Cache Cleo's editorial and inline it into the edition payload, so
        reloads keep it without another model call."""
        with self._lock:
            self._editorial = editorial
            if self._edition is not None:
                self._edition["editorial"] = editorial

    def get(self) -> dict:
        """Blocking variant (tests / direct use): stale serves immediately
        with a background refresh; an empty cache builds synchronously."""
        with self._lock:
            edition = self._edition
            fresh = (edition is not None
                     and time.time() - self._fetched_at <= self.ttl)
        if fresh:
            return edition
        if edition is not None:
            self.prewarm()
            return edition
        return self._build()


def _editorial_prompt(edition: dict, reader_topics: list[str] | None = None) -> str:
    """One grounded prompt for the whole editorial layer of tonight's paper -
    not just the words but the *judgment*: what leads, what gets prominence
    and a photo, how sections are ordered, kickers and captions."""
    def trim(s, full):
        row = {"id": s["id"], "section": s.get("section", ""),
               "headline": s["headline"], "dek": s.get("dek", ""),
               "sources": s.get("sources", 0),
               "contested": s.get("contested", False),
               "hasImage": bool(s.get("image"))}
        if full:
            row["tldr"] = s.get("tldr", [])
        return row
    stories = ([trim(s, True) for s in edition.get("stories", [])]
               + [trim(s, False) for s in edition.get("moreStories", [])])
    sections = sorted({s["section"] for s in stories if s["section"]})
    nightcap_line = (
        ' "nightcap": "2-3 warm sentences signing the paper off for a reader '
        'who follows ' + ", ".join(reader_topics) + " — reference tonight's "
        'actual stories in those areas",\n') if reader_topics else ""
    return (
        "You are Cleo, the editor-in-chief of Cura, a slow-news daily. Tonight's "
        "edition goes to print and you make the calls a print editor makes: what "
        "leads, what gets prominence and a photograph, what is held to a brief. "
        "Use ONLY the stories below — no outside facts, numbers, names, or quotes.\n\n"
        "Respond with ONLY a JSON object (no prose, no code fences):\n"
        '{"note": "2-3 calm sentences from the editor on the character of today\'s '
        'news, naming the thread that ties the edition together",\n'
        ' "lead": "<story id> — the single story that should lead the front page",\n'
        ' "leadWhy": "one short line on why that story leads tonight",\n'
        ' "prominence": {"<story id>": "major" | "standard" | "brief", ... one per '
        "story — majors get photos and space (at most one per section), briefs are "
        'a headline only},\n'
        ' "kickers": {"<story id>": "a 2-4 word printed kicker label", ... majors only},\n'
        ' "captions": {"<story id>": "a one-line photo caption grounded in the '
        'story", ... only where hasImage is true and prominence is major},\n'
        ' "sectionOrder": [' + json.dumps(sections, ensure_ascii=False)[1:-1] +
        ' — reordered by tonight\'s news weight],\n'
        ' "headlines": {"<story id>": "a tight print headline, present tense, '
        '<= 8 words, no clickbait", ... one per story},\n'
        + nightcap_line +
        ' "quotes": {"<story id>": "a short pull quote lifted from that story\'s '
        'own text", ... only where a strong verbatim line exists}}\n\n'
        "Stories (JSON):\n" + json.dumps(stories, ensure_ascii=False))


def _parse_editorial(text: str) -> dict:
    """Validate the model's editorial JSON (tolerating code fences). All
    judgment fields are optional - the renderer falls back to the wire
    layout for anything missing or malformed."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    data = json.loads(cleaned)
    if not isinstance(data, dict) or not isinstance(data.get("note"), str):
        raise ValueError("editorial response missing 'note'")
    str_map = lambda key: {str(k): str(v).strip()  # noqa: E731
                           for k, v in (data.get(key) or {}).items()}
    return {
        "note": data["note"].strip(),
        "lead": str(data.get("lead", "")).strip(),
        "leadWhy": str(data.get("leadWhy", "")).strip(),
        "prominence": {k: v for k, v in str_map("prominence").items()
                       if v in ("major", "standard", "brief")},
        "kickers": str_map("kickers"),
        "captions": str_map("captions"),
        "sectionOrder": [str(s) for s in data.get("sectionOrder") or []
                         if isinstance(s, str)],
        "headlines": str_map("headlines"),
        "nightcap": str(data.get("nightcap", "")).strip(),
        "quotes": str_map("quotes"),
    }


def _cleo_complete(prompt: str, max_tokens: int = 1024) -> str:
    """Proxy one Cleo/Verify prompt to the Anthropic API."""
    import anthropic  # optional extra: pip install -e ".[cleo]"

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    response = client.messages.create(
        model=CLEO_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return next((b.text for b in response.content if b.type == "text"), "")


def _load_dotenv() -> None:
    """Load KEY=value lines from a repo-root .env (gitignored) into the
    environment, so the API key can be set once and forgotten. Real env vars
    always win over the file."""
    env_file = DESIGN_DIR.parent / ".env"
    if not env_file.exists():
        return
    # utf-8-sig: tolerate the BOM that PowerShell's > / Set-Content may write
    for line in env_file.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def _have_cleo() -> bool:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
        return True
    except ImportError:
        print('[cura] ANTHROPIC_API_KEY is set but the SDK is missing — '
              'run: pip install -e ".[cleo]"  (Cleo will use demo mode)')
        return False


def build_index_html(edition: dict | None, cleo_live: bool,
                     static_export: bool = False) -> str:
    """Patch the prototype shell with live data + the Cleo backend shim.

    `edition=None` means the first build is still running: ship the page
    with the curating state and the poller instead of inlined data.
    `static_export` builds a serverless page (GitHub Pages): no /api
    scripts are injected, so nothing in the page can spend API tokens -
    the UI's own gates hide on-demand briefing and fall back to demo Cleo."""
    html = (DESIGN_DIR / DESKTOP_HTML).read_text(encoding="utf-8")
    if edition is None:
        live_block = _LIVE_POLL
    else:
        live_block = f"<script>window.CURA_LIVE = {json.dumps(edition)};</script>"
    if not static_export:
        live_block += "\n" + _BRIEF_API
    if cleo_live and not static_export:
        live_block += "\n" + _CLAUDE_SHIM
    # Inline data before the react/babel scripts load
    html = html.replace("<script src=", live_block + "\n<script src=", 1)
    # Merge over the canned globals right after data.jsx assigns them
    data_tag = '<script type="text/babel" src="app/data.jsx"></script>'
    html = html.replace(data_tag, data_tag + "\n" + _LIVE_MERGE, 1)
    return html


class CuraHandler(SimpleHTTPRequestHandler):
    cache: EditionCache  # set by serve()
    cleo_live: bool = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DESIGN_DIR), **kwargs)

    def _send(self, body: str, content_type: str, status: int = 200) -> None:
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # noqa: N802 (stdlib naming)
        path = self.path.split("?", 1)[0]   # route ignoring query strings
        if path in ("/", f"/{DESKTOP_HTML}"):
            self._send(build_index_html(self.cache.peek(), self.cleo_live), "text/html")
        elif path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
        elif path == "/api/edition":
            edition = self.cache.peek()
            if edition is None:   # first build still running - poller retries
                self._send('{"status": "building"}', "application/json", 202)
            else:
                self._send(json.dumps(edition), "application/json")
        elif path == "/api/status":
            # Live build progress for the curating-screen loading bar.
            self._send(json.dumps(self.cache.status()), "application/json")
        elif path.startswith("/api/audio/"):
            wav = self.cache.audio_path(path.rsplit("/", 1)[-1])
            if wav is None:
                self._send('{"error": "not found"}', "application/json", 404)
            else:
                with open(wav, "rb") as fh:
                    body = fh.read()
                self.send_response(200)
                self.send_header("Content-Type", "audio/wav")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        else:
            super().do_GET()  # static design assets (jsx, html)

    def do_POST(self):  # noqa: N802
        if self.path == "/api/brief":
            try:
                length = int(self.headers.get("Content-Length", 0))
                topics = json.loads(self.rfile.read(length)).get("topics") or []
                topics = [str(t).strip() for t in topics if str(t).strip()][:6]
            except Exception:
                self._send('{"error": "bad request"}', "application/json", 400)
                return
            self.cache.request(topics or None)
            self._send(json.dumps({"status": "building", "topics": topics}),
                       "application/json", 202)
            return
        if self.path == "/api/editorial":
            self._post_editorial()
            return
        if self.path != "/api/cleo":
            self._send('{"error": "not found"}', "application/json", 404)
            return
        if not self.cleo_live:
            self._send('{"error": "no model configured"}', "application/json", 503)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            prompt = json.loads(self.rfile.read(length))["prompt"]
            self._send(json.dumps({"completion": _cleo_complete(prompt)}),
                       "application/json")
        except Exception as exc:  # surface as 502 so the UI falls back gracefully
            self._send(json.dumps({"error": str(exc)}), "application/json", 502)

    def _post_editorial(self) -> None:
        """Click-gated: Cleo edits tonight's paper only when the user asks.
        One model call per edition - cached until the next rebuild."""
        if not self.cleo_live:
            self._send('{"error": "no model configured"}', "application/json", 503)
            return
        cached = self.cache.get_editorial()
        if cached:
            self._send(json.dumps(cached), "application/json")
            return
        edition = self.cache.peek()
        if edition is None:
            self._send('{"status": "building"}', "application/json", 202)
            return
        # Optional reader topics personalise the nightcap sign-off. The
        # editorial is cached per edition, so the first unlocker's topics
        # win - fine for a single-reader research prototype.
        reader_topics = []
        try:
            length = int(self.headers.get("Content-Length", 0) or 0)
            if length:
                body = json.loads(self.rfile.read(length))
                reader_topics = [str(t) for t in (body.get("topics") or [])][:8]
        except Exception:
            reader_topics = []
        try:
            editorial = _parse_editorial(_cleo_complete(
                _editorial_prompt(edition, reader_topics), max_tokens=3000))
            self.cache.set_editorial(editorial)
            self._send(json.dumps(editorial), "application/json")
        except Exception as exc:
            self._send(json.dumps({"error": str(exc)}), "application/json", 502)

    def log_message(self, fmt, *args):
        # args can contain non-strings (e.g. HTTPStatus from send_error)
        if any("/api/" in str(a) for a in args):
            super().log_message(fmt, *args)  # log API calls, not every asset


def serve(topics: list[str] | None = None, articles: list[Article] | None = None,
          port: int = 8765, open_browser: bool = True,
          refresh_minutes: int = 15, summarizer=None, stance_classifier=None,
          feeds: list[dict] | None = None, store: bool = True,
          clusterer=None, tts=None, present: bool = False) -> None:
    _load_dotenv()
    pipeline = Pipeline(summarizer=summarizer, stance_classifier=stance_classifier,
                        feeds=feeds, store=store, clusterer=clusterer)
    CuraHandler.cache = EditionCache(pipeline=pipeline, topics=topics,
                                     articles=articles,
                                     ttl_seconds=refresh_minutes * 60,
                                     tts=tts)
    CuraHandler.cleo_live = _have_cleo()

    server = ThreadingHTTPServer(("127.0.0.1", port), CuraHandler)
    url = f"http://127.0.0.1:{port}/"
    mode = "offline fixture" if articles is not None else "live ingestion"
    cleo = "live (Anthropic API)" if CuraHandler.cleo_live else "demo fallback (set ANTHROPIC_API_KEY)"
    from cura.ingest import fulltext
    body_mode = ("full-article extraction (trafilatura)" if fulltext.available()
                 else 'feed descriptions — pip install -e ".[fulltext]" for full articles')
    print(f"[cura] serving {url}  ({mode}, refresh every {refresh_minutes} min)")
    print(f"[cura] summariser: {pipeline.summarizer.name}")
    print(f"[cura] stance: {pipeline.stance_classifier.name}")
    print(f"[cura] article text: {body_mode}")
    print(f"[cura] narration: "
          + (f"{tts.name} (server-rendered)" if tts else "Web Speech (browser)"))
    print(f"[cura] Cleo & Verify: {cleo}")
    if present:
        print("[cura] presentation mode: the browser will open straight into "
              "the guided tour (press Right-arrow or Space to advance, Esc to exit)")
    CuraHandler.cache.prewarm()   # build the first edition while the page loads
    if open_browser:
        # Presentation mode opens straight into the guided tour. Wait for the
        # first edition first, so every tour target exists the moment it starts
        # (otherwise the early steps spotlight a still-building page).
        open_url = url + "?tour=1" if present else url
        if present:
            print("[cura] building the first edition before opening...")
            for _ in range(480):  # up to ~240s, then open regardless
                if CuraHandler.cache.peek() is not None:
                    break
                time.sleep(0.5)
        threading.Timer(0.5, webbrowser.open, args=(open_url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[cura] stopped")
    finally:
        server.server_close()
