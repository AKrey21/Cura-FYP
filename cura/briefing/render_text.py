# PROVENANCE: ORIGINAL - text-modality renderer. Stdlib only. See PROVENANCE.md.
"""Render a Briefing as the text modality (curated feed, terminal-friendly)."""

from __future__ import annotations

from cura.contracts import Briefing

_BAR = "█"


def render_text(briefing: Briefing) -> str:
    lines = ["=" * 72,
             "CURA — your briefing".center(72),
             f"{len(briefing.stories)} stories · ~{briefing.est_minutes:.1f} minutes".center(72),
             "=" * 72, ""]
    for story, cluster in zip(briefing.stories, briefing.clusters):
        confidence_bar = _BAR * story.confidence + "·" * (5 - story.confidence)
        flags = "  ⚠ CONTESTED" if story.contested else ""
        lines += [f"[{story.section}] {story.headline}",
                  f"  {confidence_bar} {story.confidence_label} "
                  f"({story.sources} sources) · {story.timestamp}{flags}"]
        lines += [f"   • {point}" for point in story.tldr]
        tri = cluster.triangulation
        if tri and tri.n_sources >= 2:
            lines.append(f"   stance: mean {tri.mean_score:+.2f}  "
                         f"spread {tri.spread:.2f}  entropy {tri.entropy:.2f}")
        lines.append("")
    lines += ["-" * 72, "Transcript (CURA_BRIEFING):", ""]
    for seg in briefing.segments:
        if seg.chapter:
            lines.append(f"## {seg.chapter}")
        lines.append(f"   {seg.text}")
    return "\n".join(lines)
