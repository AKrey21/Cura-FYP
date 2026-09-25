// PROVENANCE: ORIGINAL (bespoke to Cura) - React/JSX prototype component; the product spec (see design/HANDOFF.md). Third-party (CDN): React 18, ReactDOM, Babel standalone. See PROVENANCE.md.
// Inline SVG icons for Cura

const CIcon = ({ name, size = 18, color = 'currentColor', strokeWidth = 1.6 }) => {
  const props = { width: size, height: size, viewBox: '0 0 24 24', fill: 'none',
    stroke: color, strokeWidth, strokeLinecap: 'round', strokeLinejoin: 'round' };
  switch (name) {
    case 'read': return (
      <svg {...props}><path d="M3 5h7a3 3 0 0 1 3 3v12"/><path d="M21 5h-7a3 3 0 0 0-3 3v12"/></svg>
    );
    case 'listen': return (
      <svg {...props}><path d="M3 14a9 9 0 0 1 18 0"/><rect x="3" y="14" width="4" height="6" rx="1"/><rect x="17" y="14" width="4" height="6" rx="1"/></svg>
    );
    case 'experience': return (
      <svg {...props}><rect x="3" y="3" width="18" height="18" rx="1"/><path d="M3 8h18"/><path d="M9 8v13"/></svg>
    );
    case 'cleo': return (
      <svg {...props}><path d="M21 12a8 8 0 1 1-3.5-6.6"/><circle cx="9" cy="12" r="1" fill="currentColor"/><circle cx="14" cy="12" r="1" fill="currentColor"/></svg>
    );
    case 'verify': return (
      <svg {...props}><path d="M12 3l8 4v5c0 5-3.5 8-8 9-4.5-1-8-4-8-9V7l8-4z"/><path d="M9 12l2 2 4-4"/></svg>
    );
    case 'search': return (
      <svg {...props}><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
    );
    case 'clock': return (
      <svg {...props}><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>
    );
    case 'bookmark': return (
      <svg {...props}><path d="M6 3h12v18l-6-4-6 4z"/></svg>
    );
    case 'bookmark-fill': return (
      <svg viewBox="0 0 24 24" width={size} height={size} fill={color} stroke={color} strokeWidth={strokeWidth} strokeLinejoin="round"><path d="M6 3h12v18l-6-4-6 4z"/></svg>
    );
    case 'settings': return (
      <svg {...props}><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3h0a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8v0a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></svg>
    );
    case 'play': return (
      <svg viewBox="0 0 24 24" width={size} height={size} fill={color}><path d="M8 5l12 7-12 7V5z"/></svg>
    );
    case 'pause': return (
      <svg viewBox="0 0 24 24" width={size} height={size} fill={color}><rect x="6" y="5" width="4" height="14"/><rect x="14" y="5" width="4" height="14"/></svg>
    );
    case 'skip-back': return (
      <svg {...props}><polygon points="19 20 9 12 19 4 19 20" fill={color}/><line x1="5" y1="19" x2="5" y2="5"/></svg>
    );
    case 'skip-fwd': return (
      <svg {...props}><polygon points="5 4 15 12 5 20 5 4" fill={color}/><line x1="19" y1="5" x2="19" y2="19"/></svg>
    );
    case 'arrow-right': return (
      <svg {...props}><path d="M5 12h14"/><path d="M13 5l7 7-7 7"/></svg>
    );
    case 'close': return (
      <svg {...props}><path d="M5 5l14 14M19 5l-14 14"/></svg>
    );
    case 'send': return (
      <svg {...props}><path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4 20-7z"/></svg>
    );
    case 'sparkle': return (
      <svg {...props}><path d="M12 3l1.8 5.5L19 10l-5.2 1.5L12 17l-1.8-5.5L5 10l5.2-1.5z"/></svg>
    );
    case 'plus': return (
      <svg {...props}><path d="M12 5v14M5 12h14"/></svg>
    );
    default: return null;
  }
};

window.CIcon = CIcon;
