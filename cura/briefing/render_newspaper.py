# PROVENANCE: ORIGINAL - one-page newspaper HTML/CSS renderer (design tokens
# from design/HANDOFF.md). Third-party: Google Fonts via CDN at render time.
# See PROVENANCE.md.
"""Render a Briefing as "The Cura Daily" - the one-page newspaper modality.

Self-contained HTML (no build step, fonts from Google Fonts) using the design
tokens from design/HANDOFF.md: paper/ink palette, Fraunces serif headlines,
Inter body, JetBrains Mono eyebrows, masthead with double rule, drop-cap lead.
Print-friendly: the visible state is the base style (no entrance animations).
"""

from __future__ import annotations

import html
from datetime import datetime, timezone

from cura.contracts import Briefing, Story

_CSS = """
:root{--paper:#F4EFE6;--paper-2:#EBE3D4;--ink:#0E1A2B;--ink-soft:#2A3548;
--ink-muted:#6B7280;--rule:rgba(14,26,43,0.18);--accent:#B8331E;--green:#1F5E3F;}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--paper);color:var(--ink);font-family:'Inter',sans-serif;
padding:48px 24px}
.page{max-width:1080px;margin:0 auto}
.masthead{text-align:center;border-bottom:3px double var(--ink);padding-bottom:14px}
.masthead .vol{font-family:'JetBrains Mono',monospace;font-size:11px;
letter-spacing:.22em;text-transform:uppercase;color:var(--ink-muted);
display:flex;justify-content:space-between}
.masthead h1{font-family:'Fraunces',serif;font-size:54px;font-weight:600;
letter-spacing:.01em;margin:6px 0 2px}
.grid{display:grid;grid-template-columns:1.5fr 1fr;gap:32px;margin-top:28px}
@media(max-width:760px){.grid{grid-template-columns:1fr}}
.eyebrow{font-family:'JetBrains Mono',monospace;font-size:10px;
letter-spacing:.22em;text-transform:uppercase;color:var(--accent)}
.lead h2{font-family:'Fraunces',serif;font-size:36px;line-height:1.15;
margin:8px 0 10px}
.lead .body{column-count:2;column-gap:24px;font-size:14.5px;line-height:1.65;
color:var(--ink-soft)}
@media(max-width:760px){.lead .body{column-count:1}}
.lead .body p:first-of-type::first-letter{font-family:'Fraunces',serif;
font-size:52px;float:left;line-height:.85;padding:4px 8px 0 0;color:var(--accent)}
.story{border-top:1px solid var(--rule);padding:14px 0}
.story h3{font-family:'Fraunces',serif;font-size:19px;line-height:1.25;margin:4px 0 6px}
.story p{font-size:13px;line-height:1.55;color:var(--ink-soft)}
.meta{font-family:'JetBrains Mono',monospace;font-size:10px;
letter-spacing:.14em;text-transform:uppercase;color:var(--ink-muted);margin-top:6px}
.contested{color:var(--accent);font-weight:600}
.confidence{color:var(--green)}
.sidebar{background:var(--paper-2);padding:20px;border:1px solid var(--rule)}
.sidebar h4{font-family:'JetBrains Mono',monospace;font-size:11px;
letter-spacing:.22em;text-transform:uppercase;margin-bottom:12px}
.sidebar li{font-size:13px;line-height:1.5;margin:0 0 10px 18px;color:var(--ink-soft)}
.footer{border-top:3px double var(--ink);margin-top:32px;padding-top:10px;
font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:.18em;
text-transform:uppercase;color:var(--ink-muted);text-align:center}
"""


def _meta_line(story: Story) -> str:
    parts = [f'<span class="confidence">{html.escape(story.confidence_label)}'
             f" · {story.sources} sources</span>",
             html.escape(story.timestamp)]
    if story.contested:
        parts.append('<span class="contested">⚠ contested coverage</span>')
    return " · ".join(parts)


def _lead_html(story: Story) -> str:
    body = "".join(f"<p>{html.escape(point)}</p>" for point in story.tldr)
    return f"""<article class="lead">
  <div class="eyebrow">{html.escape(story.section)}</div>
  <h2>{html.escape(story.headline)}</h2>
  <div class="body">{body}</div>
  <div class="meta">{_meta_line(story)}</div>
</article>"""


def _story_html(story: Story) -> str:
    return f"""<article class="story">
  <div class="eyebrow">{html.escape(story.section)}</div>
  <h3>{html.escape(story.headline)}</h3>
  <p>{html.escape(story.dek)}</p>
  <div class="meta">{_meta_line(story)}</div>
</article>"""


def render_newspaper(briefing: Briefing, date: datetime | None = None) -> str:
    date = date or datetime.now(timezone.utc)
    lead, *rest = briefing.stories or [None]
    briefly = "".join(f"<li>{html.escape(s.headline)}</li>" for s in briefing.stories)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>The Cura Daily — {date:%d %B %Y}</title>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600&family=Inter:wght@400;600&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>{_CSS}</style></head>
<body><div class="page">
<header class="masthead">
  <div class="vol"><span>Vol. 1</span><span>~{briefing.est_minutes:.0f} minute read</span></div>
  <h1>The Cura Daily</h1>
  <div class="vol"><span>{date:%A}</span><span>{date:%d %B %Y}</span></div>
</header>
<main class="grid">
  <section>
    {_lead_html(lead) if lead else "<p>No stories in this edition.</p>"}
    {"".join(_story_html(s) for s in rest)}
  </section>
  <aside class="sidebar">
    <h4>The Daily, Briefly</h4>
    <ul>{briefly}</ul>
  </aside>
</main>
<footer class="footer">Cura · slow news, examined · {len(briefing.stories)} stories from independent sources</footer>
</div></body></html>"""
