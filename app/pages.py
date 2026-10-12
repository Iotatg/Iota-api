"""Retro-computing / technical editorial HTML pages for Iota."""
from __future__ import annotations

CSS = """
/* ===== Iota Design System — Technical Editorial ===== */

:root {
  /* Monochrome technical base */
  --i-bg-paper: #f8f6f2;
  --i-bg-paper-alt: #f0eee9;
  --i-bg-light: #e7e7e3;
  --i-bg-light-2: #d6d6d2;
  --i-bg-mid: #c8c8c3;
  --i-panel: #404040;
  --i-panel-dark: #242424;
  --i-panel-darker: #191919;
  --i-panel-darkest: #111111;
  --i-ink: #1a1a1a;
  --i-ink-muted: #605f5d;
  --i-ink-lighter: #908f8d;
  --i-border: #b8b6b1;
  --i-border-dark: #333333;
  --i-border-darker: #1a1a1a;
  --i-accent: #d97706;          /* muted warm orange */
  --i-accent-soft: #d977061a;
  --i-accent-line: #d9770640;

  /* Typography */
  --i-font-body: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --i-font-display: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif;
  --i-font-mono: 'IBM Plex Mono', 'Fira Code', ui-monospace, monospace;

  /* Spacing */
  --i-radius: 3px;
  --i-radius-panel: 0;
  --i-gap: 24px;

  /* Animation timing */
  --i-ease: cubic-bezier(0.2, 0, 0.2, 1);
  --i-dur-fast: 150ms;
  --i-dur-normal: 250ms;
}

* { box-sizing: border-box; }

html, body {
  margin: 0;
  padding: 0;
  background: var(--i-bg-paper);
  color: var(--i-ink);
  font-family: var(--i-font-body);
  font-size: 16px;
  line-height: 1.6;
  overflow-x: hidden;
}

/* Scanline texture overlay */
body {
  background: var(--i-bg-paper);
  position: relative;
}

/* Grid background for dark sections */
.grid-bg {
  background-image:
    linear-gradient(to right, var(--i-border-dark) 1px, transparent 1px),
    linear-gradient(to bottom, var(--i-border-dark) 1px, transparent 1px);
  background-size: 24px 24px;
}

/* Editorial content area */
.wrap {
  max-width: 1200px;
  margin: 0 auto;
  padding: 48px 24px 100px;
  position: relative;
  z-index: 1;
}

/* Typography */
h1, h2, h3, h4 {
  font-family: var(--i-font-display);
  font-weight: 500;
  letter-spacing: -0.02em;
  line-height: 1.15;
  margin: 0 0 16px 0;
}
h1 { font-size: clamp(2.2rem, 5vw, 3.5rem); }
h2 { font-size: clamp(1.5rem, 3vw, 2rem); letter-spacing: -0.01em; }
h3 { font-size: 1.125rem; letter-spacing: 0.02em; }
h4 { font-size: 0.95rem; }

/* Mono technical labels */
.mono { font-family: var(--i-font-mono); font-size: 0.85rem; }
.mono-sm { font-family: var(--i-font-mono); font-size: 0.75rem; }
.mono-xs { font-family: var(--i-font-mono); font-size: 0.7rem; }

/* Technical labels */
.label {
  font-family: var(--i-font-mono);
  font-size: 0.7rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--i-ink-muted);
  margin-bottom: 8px;
  display: block;
}

/* Accent text */
.accent { color: var(--i-accent); }
.accent-warm { color: var(--i-accent); }

/* Utility text */
.muted { color: var(--i-ink-muted); }
.text-lighter { color: var(--i-ink-lighter); }

/* ===== Borders: thin 1px technical ===== */
.border-b { border-bottom: 1px solid var(--i-border); }
.border-l { border-left: 1px solid var(--i-border); }
.border-t { border-top: 1px solid var(--i-border); }

/* ===== Panels ===== */
.panel {
  background: white;
  border: 1px solid var(--i-border);
  border-radius: var(--i-radius-panel);
  padding: 24px;
  margin-bottom: var(--i-gap);
}

.panel-dark {
  background: var(--i-panel-dark);
  border: 1px solid var(--i-border-dark);
  border-radius: var(--i-radius-panel);
  padding: 24px;
  margin-bottom: var(--i-gap);
  color: #e0e0e0;
}

.panel-darker {
  background: var(--i-panel-darker);
  border: 1px solid var(--i-border-dark);
  border-radius: var(--i-radius-panel);
  padding: 24px;
}

.panel-invert {
  background: var(--i-ink);
  border: 1px solid var(--i-border-dark);
  border-radius: var(--i-radius-panel);
  padding: 24px;
  color: white;
}

/* ===== Technical corner markings ===== */
.corner-mark {
  position: absolute;
  width: 12px; height: 12px;
  border: 1px solid var(--i-accent);
}
.corner-mark.tt { top: -1px; left: -1px; border-bottom: none; border-right: none; }
.corner-mark.tl { top: -1px; right: -1px; border-bottom: none; border-left: none; }
.corner-mark.bt { bottom: -1px; left: -1px; border-top: none; border-right: none; }
.corner-mark.bl { bottom: -1px; right: -1px; border-top: none; border-left: none; }

.panel-rel { position: relative; }

/* ===== Buttons ===== */
.btn {
  cursor: pointer;
  border: 1px solid var(--i-border);
  border-radius: var(--i-radius);
  padding: 10px 20px;
  font-family: var(--i-font-mono);
  font-size: 0.8rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 500;
  background: white;
  color: var(--i-ink);
  transition: all var(--i-dur-fast) var(--i-ease);
  min-height: 40px;
  position: relative;
  overflow: hidden;
}

.btn:hover {
  transform: translateY(-1px);
  border-color: var(--i-accent);
}

.btn:active {
  transform: translateY(0);
}

.btn:focus {
  outline: 2px solid var(--i-accent);
  outline-offset: 2px;
}

.btn::before {
  content: '';
  position: absolute;
  top: 0; left: -100%;
  width: 100%; height: 100%;
  background: linear-gradient(90, transparent, var(--i-accent-soft), transparent);
  transition: left 0.4s ease;
}

.btn:hover::before { left: 100%; }

.btn-primary {
  background: var(--i-accent);
  color: white;
  border-color: var(--i-accent);
}

.btn-primary:hover {
  background: #c46300;
  box-shadow: 0 0 0 3px var(--i-accent-soft);
}

.btn-accent {
  background: var(--i-accent);
  color: white;
  border-color: var(--i-accent);
}

.btn-ghost {
  background: transparent;
  color: var(--i-ink);
}

.btn-ghost:hover {
  background: rgba(217, 119, 6, 0.06);
}

.btn-ghost-dark {
  background: transparent;
  color: #e0e0e0;
  border-color: var(--i-border-dark);
}

.btn-ghost-dark:hover {
  background: var(--i-accent-soft);
  color: var(--i-ink);
}

/* ===== Forms ===== */
input, textarea, select {
  background: white;
  border: 1px solid var(--i-border);
  border-radius: var(--i-radius);
  padding: 12px 14px;
  color: var(--i-ink);
  font-family: var(--i-font-mono);
  font-size: 0.85rem;
  width: 100%;
  transition: border-color var(--i-dur-fast) var(--i-ease);
}

input:focus, textarea:focus, select:focus {
  outline: none;
  border-color: var(--i-accent);
  box-shadow: 0 0 0 2px var(--i-accent-soft);
}

input::placeholder { color: var(--i-ink-lighter); }

input[readonly] {
  background: var(--i-bg-light);
  color: var(--i-ink-muted);
  cursor: default;
}

label {
  font-family: var(--i-font-mono);
  font-size: 0.7rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: 6px;
  display: block;
  color: var(--i-ink-muted);
}

/* ===== Code blocks ===== */
code, pre {
  font-family: var(--i-font-mono);
  font-size: 0.85rem;
}

code.inline {
  background: var(--i-bg-light);
  padding: 2px 6px;
  border-radius: 2px;
  border: 1px solid var(--i-border);
  color: var(--i-ink);
  white-space: nowrap;
}

pre {
  background: var(--i-panel-darker);
  border: 1px solid var(--i-border-dark);
  border-radius: var(--i-radius);
  padding: 16px;
  overflow-x: auto;
  color: #d0d0d0;
  margin: 0;
}

pre code {
  background: none;
  padding: 0;
  border: none;
  color: inherit;
}

/* ===== Grid ===== */
.grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--i-gap);
}

@media (min-width: 640px) {
  .grid { grid-template-columns: 1fr 1fr; }
}

@media (min-width: 1024px) {
  .grid { grid-template-columns: 1fr 1fr 1fr; }
}

.grid-2 { grid-template-columns: 1fr 1fr; }
.grid-3 { grid-template-columns: 1fr 1fr 1fr; }

/* ===== Cards (rectangular, no excessive rounding) ===== */
.card {
  background: white;
  border: 1px solid var(--i-border);
  border-radius: var(--i-radius-panel);
  padding: 20px;
  transition: all var(--i-dur-normal) var(--i-ease);
  position: relative;
}

.card:hover {
  transform: translateY(-2px);
  border-color: var(--i-accent-line);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
}

.card-dark {
  background: var(--i-panel-dark);
  border: 1px solid var(--i-border-dark);
  color: #e0e0e0;
}

.card-dark:hover {
  border-color: var(--i-accent);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
}

.card-title {
  font-family: var(--i-font-display);
  font-size: 0.85rem;
  font-weight: 500;
  letter-spacing: 0.04em;
  margin-bottom: 8px;
  color: var(--i-ink);
}

.card-dark .card-title { color: #f0f0f0; }

.card-meta {
  color: var(--i-ink-muted);
  font-size: 0.8rem;
  font-family: var(--i-font-mono);
}

.card-dark .card-meta { color: var(--i-ink-lighter); }

/* ===== Technical table ===== */
.tech-table {
  width: 100%;
  border-collapse: collapse;
  margin: 0;
}

.tech-table th, .tech-table td {
  text-align: left;
  padding: 8px 12px;
  border-bottom: 1px solid var(--i-border);
  font-family: var(--i-font-mono);
  font-size: 0.85rem;
}

.tech-table th {
  color: var(--i-ink-muted);
  letter-spacing: 0.04em;
  font-weight: 500;
  text-transform: uppercase;
  font-size: 0.7rem;
}

.tech-table td .mono { color: var(--i-ink); }

/* ===== Status indicators ===== */
.status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--i-font-mono);
  font-size: 0.75rem;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--i-accent);
}

.status-green .status-dot { background: #22c55e; }
.status-amber .status-dot { background: #f59e0b; }
.status-red .status-dot { background: #ef4444; }
.status-gray .status-dot { background: #6b7280; }

.status-pulse {
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* ===== Navigation ===== */
.nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid var(--i-border);
  background: white;
  position: sticky;
  top: 0;
  z-index: 50;
  transition: background var(--i-dur-fast) var(--i-ease), box-shadow var(--i-dur-fast) var(--i-ease);
}

.nav.scrolled {
  background: rgba(248, 246, 242, 0.95);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  border-bottom-color: var(--i-accent-line);
}

.nav-left { display: flex; align-items: center; gap: 24px; }
.nav-right { display: flex; align-items: center; gap: 12px; }

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  text-decoration: none;
  color: var(--i-ink);
}

.logo {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
}

.logo svg { display: block; }

.brand-text {
  font-family: var(--i-font-mono);
  font-size: 0.8rem;
  letter-spacing: 0.12em;
  font-weight: 500;
}

.brand-text .accent { color: var(--i-accent); }

.nav-link {
  font-family: var(--i-font-mono);
  font-size: 0.75rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--i-ink-muted);
  text-decoration: none;
  padding: 6px 4px;
  position: relative;
  transition: color var(--i-dur-fast) var(--i-ease);
  white-space: nowrap;
}

.nav-link:hover { color: var(--i-ink); }

.nav-link.active {
  color: var(--i-accent);
}

.nav-link.active::after {
  content: '';
  position: absolute;
  bottom: -4px;
  left: 0;
  right: 0;
  height: 1px;
  background: var(--i-accent);
  animation: lineHeight 2s linear infinite;
}

@keyframes lineHeight {
  0% { opacity: 0.3; }
  50% { opacity: 1; }
  100% { opacity: 0.3; }
}

/* ===== Hero ===== */
.hero {
  margin-bottom: var(--i-gap);
}

.hero .label {
  font-size: 0.7rem;
  letter-spacing: 0.18em;
  color: var(--i-ink-muted);
  margin-bottom: 16px;
}

.hero h1 {
  font-family: var(--i-font-display);
  font-weight: 500;
  font-size: clamp(2.5rem, 6vw, 4rem);
  letter-spacing: -0.03em;
  margin-bottom: 24px;
  line-height: 1.05;
}

.hero h1 .accent {
  color: var(--i-accent);
  position: relative;
}

.hero h1 .accent::after {
  content: '';
  position: absolute;
  bottom: -4px;
  left: 0;
  right: 0;
  height: 1px;
  background: var(--i-accent);
  width: 30%;
  opacity: 0.4;
}

.hero p.lead {
  font-size: 1.1rem;
  max-width: 600px;
  margin-bottom: 32px;
  color: var(--i-ink);
}

/* ===== Technical console search ===== */
.console {
  position: relative;
  margin-bottom: var(--i-gap);
}

.console .label {
  margin-bottom: 12px;
}

.console-border {
  border: 1px solid var(--i-border);
  border-radius: var(--i-radius);
  background: white;
  padding: 8px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.console-border:focus-within {
  border-color: var(--i-accent);
  box-shadow: 0 0 0 2px var(--i-accent-soft);
}

.console input {
  border: none;
  outline: none;
  background: transparent;
  flex: 1;
  font-family: var(--i-font-mono);
  font-size: 0.9rem;
  padding: 0;
  color: var(--i-ink);
}

.console input::placeholder {
  color: var(--i-ink-lighter);
}

.console .console-prompt {
  font-family: var(--i-font-mono);
  font-size: 0.85rem;
  color: var(--i-accent);
  white-space: nowrap;
}

/* ===== Stats grid ===== */
.stats-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
  margin-bottom: var(--i-gap);
}

@media (min-width: 768px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
}

@media (min-width: 1024px) {
  .stats-grid { grid-template-columns: repeat(4, 1fr); }
}

.stat-number {
  font-family: var(--i-font-mono);
  font-size: 2rem;
  font-weight: 500;
  color: var(--i-accent);
}

.stat-label {
  font-size: 0.75rem;
  letter-spacing: 0.04em;
  color: var(--i-ink-muted);
  margin-top: 4px;
}

/* ===== Empty state ===== */
.empty {
  text-align: center;
  padding: 64px 24px;
  color: var(--i-ink-muted);
}

.empty svg {
  width: 48px;
  height: 48px;
  margin-bottom: 16px;
  opacity: 0.3;
}

/* ===== Toast ===== */
.toast {
  position: fixed;
  bottom: 32px;
  left: 50%;
  transform: translateX(-50%) translateY(40px);
  background: white;
  border: 1px solid var(--i-border);
  border-radius: var(--i-radius);
  padding: 12px 24px;
  font-family: var(--i-font-mono);
  font-size: 0.8rem;
  color: var(--i-ink);
  z-index: 1000;
  transition: transform 250ms var(--i-ease), opacity 250ms var(--i-ease);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
  display: flex;
  align-items: center;
  gap: 8px;
}

.toast.visible {
  transform: translateX(-50%) translateY(0);
  opacity: 1;
}

.toast:not(.visible) {
  opacity: 0;
}

.toast.toast-error { border-color: var(--i-accent); }
.toast.toast-success { border-color: #22c55e; }
.toast.toast-error .toast-dot { background: var(--i-accent); }
.toast.toast-success .toast-dot { background: #22c55e; }

.toast-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--i-ink-lighter);
}

/* ===== Reduced motion ===== */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}

/* ===== Responsive ===== */
@media (max-width: 640px) {
  .wrap { padding: 32px 16px 80px; }
  h1 { font-size: 2rem; }
  .nav { padding: 12px 16px; }
  .nav-left, .nav-right { gap: 12px; }
  .stats-grid { grid-template-columns: 1fr; }
}

/* Measurement marks / tiny numbers */
.measure {
  position: relative;
}

.measure::after {
  content: attr(data-measure);
  position: absolute;
  top: -12px;
  right: -4px;
  font-family: var(--i-font-mono);
  font-size: 0.6rem;
  color: var(--i-ink-lighter);
}

/* ===== Tag ===== */
.tag {
  display: inline-block;
  font-family: var(--i-font-mono);
  font-size: 0.7rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  border: 1px solid var(--i-border);
  border-radius: var(--i-radius);
  padding: 2px 8px;
  color: var(--i-ink-muted);
}

.tag-accent {
  border-color: var(--i-accent-line);
  color: var(--i-accent);
}

/* ===== Divider ===== */
.divider {
  height: 1px;
  background: var(--i-border);
  margin: 24px 0;
}

.divider-accent {
  height: 1px;
  background: var(--i-accent-line);
  margin: 24px 0;
}

/* ===== Section ===== */
 .section {
   margin-bottom: var(--i-gap);
 }

 .section-note {
   margin-top: calc(var(--i-gap) * 0.5);
   font-family: var(--i-font-mono);
   font-size: 0.75rem;
   line-height: 1.6;
   color: var(--i-ink-muted);
   border-left: 2px solid var(--i-border);
   padding-left: 0.75rem;
 }

 .section-note code {
   font-family: var(--i-font-mono);
   background: var(--i-bg-light);
   padding: 0.1em 0.35em;
   border-radius: 2px;
   border: 1px solid var(--i-border);
 }

/* ===== Skeleton loading ===== */
.skeleton {
  background: linear-gradient(90deg, var(--i-bg-light) 25%, var(--i-bg-light-2) 50%, var(--i-bg-light) 75%);
  background-size: 200% 100%;
  animation: skeletonLoading 1.5s infinite;
  border-radius: var(--i-radius);
  height: 16px;
}

@keyframes skeletonLoading {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

/* ===== Card entrance (dynamic content) ===== */
.card[data-reveal] {
  animation: cardIn 0.4s cubic-bezier(0.2, 0, 0.2, 1) both;
}

@keyframes cardIn {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Console border inputs */
.console-border input {
  flex: 1;
  min-width: 0;
}

/* ===== Catalog track thumbnails ===== */
.card-thumb {
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  display: block;
  background: var(--i-bg-light);
  border: 1px solid var(--i-border);
  margin-bottom: 14px;
}

.card-thumb-fallback {
  width: 100%;
  aspect-ratio: 16 / 9;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--i-bg-light);
  border: 1px solid var(--i-border);
  margin-bottom: 14px;
  color: var(--i-ink-lighter);
  font-family: var(--i-font-mono);
  font-size: 0.7rem;
  letter-spacing: 0.08em;
}

/* ===== Tag chips ===== */
.chip {
  display: inline-block;
  font-family: var(--i-font-mono);
  font-size: 0.62rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--i-ink-muted);
  background: var(--i-bg-light);
  border: 1px solid var(--i-border);
  padding: 2px 7px;
  margin: 0 4px 4px 0;
  border-radius: var(--i-radius);
}

/* ===== Playing card highlight ===== */
.card.playing {
  border-color: var(--i-accent);
  box-shadow: 0 0 0 1px var(--i-accent), 0 4px 16px rgba(217, 119, 6, 0.10);
}

.card.playing .card-title { color: var(--i-accent); }

/* ===== Player ===== */
.player { border: 1px solid var(--i-accent); }
.player-thumb {
  width: 100%;
  max-width: 300px;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  border: 1px solid var(--i-border-dark);
  display: block;
  background: var(--i-bg-light);
}
.player-controls {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
}
.player-btn {
  width: 42px;
  height: 42px;
  flex: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--i-accent);
  color: #fff;
  border: none;
  border-radius: var(--i-radius);
  cursor: pointer;
  transition: background var(--i-dur-fast) var(--i-ease);
}
.player-btn:hover { background: #b45309; }
.player-progress {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.player-track {
  flex: 1;
  height: 4px;
  background: var(--i-bg-light-2);
  border-radius: 2px;
  cursor: pointer;
  position: relative;
  overflow: hidden;
}
.player-fill {
  height: 100%;
  width: 0%;
  background: var(--i-accent);
  border-radius: 2px;
}
.player-time {
  font-family: var(--i-font-mono);
  font-size: 0.72rem;
  color: var(--i-ink-muted);
  min-width: 40px;
  text-align: center;
}
.player-volume {
  width: 90px;
  flex: none;
  accent-color: var(--i-accent);
  cursor: pointer;
}

/* ===== Search suggestions ===== */
.console-wrap { position: relative; flex: 1; display: flex; min-width: 0; }
.suggest-list {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  background: white;
  border: 1px solid var(--i-border);
  border-radius: var(--i-radius);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.10);
  z-index: 50;
  overflow: hidden;
  display: none;
}
.suggest-list.open { display: block; }
.suggest-item {
  padding: 9px 12px;
  font-family: var(--i-font-mono);
  font-size: 0.82rem;
  color: var(--i-ink);
  cursor: pointer;
  border-bottom: 1px solid var(--i-bg-light);
}
.suggest-item:last-child { border-bottom: none; }
.suggest-item:hover, .suggest-item.active {
  background: var(--i-accent-soft);
  color: var(--i-accent);
}
.result-count {
  font-family: var(--i-font-mono);
  font-size: 0.72rem;
  color: var(--i-ink-muted);
  margin-top: 10px;
  letter-spacing: 0.03em;
}
"""

NAV = """
<nav class="nav" id="mainNav">
  <a href="/" class="brand">
    <span class="logo">I</span>
    <span class="brand-text">IOTA<span class="accent"> API</span></span>
  </a>
  <div class="nav-right">
    <a class="nav-link" href="/">PLAYER</a>
    <a class="nav-link" href="/docs">DOCS</a>
    <a class="nav-link" href="/db">IOTADB</a>
    <a class="nav-link" href="/health">HEALTH</a>
    <a class="nav-link" href="/api/stats" id="nav-stats">STATS</a>
  </div>
</nav>
"""

INFRA_DIAGRAM = """
<div class="panel-dark" style="margin-bottom:48px">
  <div class="label">IOTA AUDIO COMPUTER — SYSTEM ARCHITECTURE</div>
  <div style="overflow-x:auto">
    <svg viewBox="0 0 800 420" width="100%" height="auto" style="min-height:300px;font-family:var(--i-font-mono)">
      <defs>
        <linearGradient id="linkGrad" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="#d9770600"/>
          <stop offset="50%" stop-color="#d97706"/>
          <stop offset="100%" stop-color="#d9770600"/>
        </linearGradient>
      </defs>
      <!-- Background grid lines -->
      <line x1="60" y1="0" x2="60" y2="420" stroke="#333" stroke-width="1"/>
      <line x1="0" y1="60" x2="800" y2="60" stroke="#333" stroke-width="1"/>
      <line x1="0" y1="360" x2="800" y2="360" stroke="#333" stroke-width="1"/>

      <!-- USER -->
      <rect x="60" y="20" width="100" height="40" fill="none" stroke="#fff" stroke-width="1"/>
      <text x="110" y="48" text-anchor="middle" fill="#fff" font-size="12">USER</text>
      <text x="110" y="66" text-anchor="middle" fill="#888" font-size="9">HTTP / HTTPS</text>

      <!-- Connection: USER -> API -->
      <line x1="110" y1="60" x2="110" y2="100" stroke="#d97706" stroke-width="1" stroke-dasharray="3,3">
        <animate attributeName="stroke-opacity" values="0.2;0.8;0.2" dur="3s" repeatCount="indefinite"/>
      </line>
      <text x="116" y="82" fill="#888" font-size="9">GET /api/search</text>

      <!-- IOTA API -->
      <rect x="60" y="100" width="100" height="50" fill="#1a1a1a" stroke="#d97706" stroke-width="1"/>
      <text x="110" y="130" text-anchor="middle" fill="#fff" font-size="12">IOTA</text>
      <text x="110" y="142" text-anchor="middle" fill="#888" font-size="9">API v2.0.0</text>

      <!-- CATALOG INDEX -->
      <rect x="200" y="100" width="120" height="50" fill="none" stroke="#fff" stroke-width="1"/>
      <text x="260" y="125" text-anchor="middle" fill="#fff" font-size="12">CATALOG</text>
      <text x="260" y="140" text-anchor="middle" fill="#888" font-size="9">INVERTED INDEX</text>

      <!-- IOTADB -->
      <rect x="360" y="100" width="120" height="50" fill="none" stroke="#fff" stroke-width="1"/>
      <text x="420" y="125" text-anchor="middle" fill="#fff" font-size="12">IOTADB</text>
      <text x="420" y="140" text-anchor="middle" fill="#fff" font-size="9">JSON / FILES</text>

      <!-- AUDIO STREAM -->
      <rect x="200" y="220" width="120" height="50" fill="none" stroke="#fff" stroke-width="1"/>
      <text x="260" y="245" text-anchor="middle" fill="#fff" font-size="12">AUDIO</text>
      <text x="260" y="260" text-anchor="middle" fill="#888" font-size="9">STREAM / WAV</text>

      <!-- STORAGE -->
      <rect x="360" y="220" width="120" height="50" fill="none" stroke="#fff" stroke-width="1"/>
      <text x="420" y="245" text-anchor="middle" fill="#fff" font-size="12">STORAGE</text>
      <text x="420" y="260" text-anchor="middle" fill="#888" font-size="9">OBJECT / LOCAL</text>

      <!-- Connections: API -> INDEX -->
      <line x1="160" y1="125" x2="200" y2="125" stroke="#d97706" stroke-width="1"/>
      <text x="180" y="120" fill="#888" font-size="9">INDEX</text>

      <!-- Connections: API -> IOTADB -->
      <line x1="160" y1="125" x2="360" y2="125" stroke="#d97706" stroke-width="1"/>
      <text x="260" y="120" fill="#888" font-size="9">QUERY</text>
      <text x="260" y="132" fill="#888" font-size="9">INSERT</text>

      <!-- Connections: API -> AUDIO -->
      <line x1="110" y1="150" x2="110" y2="220" stroke="#d97706" stroke-width="1"/>
      <text x="116" y="185" fill="#888" font-size="9">STREAM</text>

      <!-- Connections: AUDIO -> STORAGE -->
      <line x1="260" y1="260" x2="360" y2="245" stroke="#d97706" stroke-width="1"/>
      <text x="310" y="255" fill="#888" font-size="9">WAV</text>

      <!-- IOTADB -> STORAGE -->
      <line x1="420" y1="150" x2="420" y2="220" stroke="#d97706" stroke-width="1"/>
      <text x="426" y="185" fill="#888" font-size="9">FILES</text>

      <!-- Bottom labels -->
      <text x="60" y="390" fill="#888" font-size="9">SEARCH | METADATA | SUGGEST</text>
      <text x="420" y="390" text-anchor="end" fill="#888" font-size="9">OBJECT STORAGE | RANGE / 206</text>
    </svg>
  </div>
</div>
"""

EXTRA_CSS = """
:where(a, button, input, [tabindex]):focus-visible { outline: 2px solid var(--i-accent); outline-offset: 2px; }
.player-track { cursor: pointer; }
.card-thumb-fallback { aspect-ratio: 16 / 9; }
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
@media (max-width: 640px) {
  #player {
    position: fixed;
    left: 8px;
    right: 8px;
    bottom: 8px;
    z-index: 60;
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.28);
  }
}
"""


def _page(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@300;400;500;700&family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>{CSS}
{EXTRA_CSS}</style>
</head>
<body>
{NAV}
<div class="wrap" style="z-index:5">
{body}
</div>
<div id="toast" class="toast" role="alert" aria-live="polite"></div>
<script src="/static/page.js"></script>
</body>
</html>"""


def landing_html() -> str:
    body = """
    <section class="hero section">
      <div class="label">IOTA / OPEN AUDIO INFRASTRUCTURE</div>
      <h1>
        Search.
        <br>
        Stream.
        <br>
        Store.
      </h1>
      <p class="lead">
        Iota Songs API. A public catalog of real tracks with indexed search,
        provider-backed audio streaming (HTTP Range / 206), and IotaDB for
        JSON documents and object storage.
      </p>
      <div class="console">
        <div class="label">CATALOG SEARCH</div>
        <div class="console-border">
          <span class="console-prompt">/&gt;</span>
          <div class="console-wrap">
            <input id="q" type="search" placeholder="try &quot;adele&quot;, &quot;queen&quot;, &quot;k-pop&quot;, &quot;80s&quot;..." aria-label="Search songs" autocomplete="off" role="combobox" aria-expanded="false" aria-autocomplete="list" aria-controls="suggest">
            <div class="suggest-list" id="suggest" role="listbox" aria-label="Search suggestions"></div>
          </div>
          <button class="btn btn-primary" id="go" type="button">Search</button>
          <button class="btn" id="rand" type="button">Random</button>
          <button class="btn" id="getkey" type="button">Get API Key</button>
        </div>
        <div class="result-count" id="resultCount"></div>
      </div>
    </section>

    <!-- Infrastructure diagram -->
    <section class="section">
      {INFRA_DIAGRAM_PLACEHOLDER}
    </section>

    <!-- Audio player -->
    <section class="section">
      <div id="player" class="panel-dark player" style="display:none;" aria-label="Audio player">
        <div style="display:flex;gap:20px;align-items:flex-start;flex-wrap:wrap;">
          <img id="pthumb" class="player-thumb" alt="Album art" style="display:none;">
          <div style="flex:1;min-width:240px;">
            <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;">
              <div>
                <div class="label">NOW PLAYING</div>
                <div id="ptitle" style="font-size:1.1rem;font-family:var(--i-font-display);font-weight:500;">No selection</div>
                <div class="mono muted" id="pmeta"></div>
              </div>
              <div style="display:flex;align-items:center;gap:12px;">
                <span class="status status-green" id="pstatus" style="margin:0">
                  <span class="status-dot"></span><span id="pstatustext">READY</span>
                </span>
                <button class="btn" id="pclose" type="button" aria-label="Hide player">&times;</button>
              </div>
            </div>
            <div class="player-controls">
              <button class="player-btn" id="pprev" type="button" aria-label="Previous track">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M6 6h2v12H6zm3.5 6l8.5 6V6z"/></svg>
              </button>
              <button class="player-btn" id="pplay" type="button" aria-label="Play or pause">
                <svg id="pplayicon" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
              </button>
              <button class="player-btn" id="pnext" type="button" aria-label="Next track">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M16 6h2v12h-2zM6 18l8.5-6L6 6z"/></svg>
              </button>
              <div class="player-progress">
                <span class="player-time" id="pcur">0:00</span>
                <div class="player-track" id="ptrack" role="slider" tabindex="0" aria-label="Seek" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"><div class="player-fill" id="pfill"></div></div>
                <span class="player-time" id="pdur">0:00</span>
              </div>
              <input class="player-volume" id="pvol" type="range" min="0" max="1" step="0.05" value="1" aria-label="Volume">
            </div>
            <audio id="audio" preload="metadata"></audio>
          </div>
        </div>
      </div>
    </section>

    <!-- Trending / Catalog signal -->
    <section class="section">
      <div class="label">CATALOG SIGNAL</div>
      <h2>Trending</h2>
      <div id="results" class="grid" style="margin-top:24px"></div>
    </section>
    <script>
    (function () {
      var results = document.getElementById('results');
      var player = document.getElementById('player');
      var audioEl = document.getElementById('audio');
      var ptitle = document.getElementById('ptitle');
      var pmeta = document.getElementById('pmeta');
      var pthumb = document.getElementById('pthumb');
      var pplay = document.getElementById('pplay');
      var pplayicon = document.getElementById('pplayicon');
      var pprev = document.getElementById('pprev');
      var pnext = document.getElementById('pnext');
      var pclose = document.getElementById('pclose');
      var ptrack = document.getElementById('ptrack');
      var pfill = document.getElementById('pfill');
      var pcur = document.getElementById('pcur');
      var pdur = document.getElementById('pdur');
      var pvol = document.getElementById('pvol');
      var resultCount = document.getElementById('resultCount');
      var qInput = document.getElementById('q');
      var suggestBox = document.getElementById('suggest');
      var getkeyBtn = document.getElementById('getkey');
      var currentCard = null;
      var queue = [];
      var qIndex = -1;
      var runSeq = 0;
      var suggestSeq = 0;
      var sugItems = [];
      var sugActive = -1;

      var ICON_PLAY = '<path d="M8 5v14l11-7z"/>';
      var ICON_PAUSE = '<path d="M6 5h4v14H6zM14 5h4v14h-4z"/>';

      function escapeHtml(str) {
        return String(str == null ? '' : str).replace(/[&<>"']/g, function (c) {
          return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c];
        });
      }

      function fmtDuration(sec) {
        if (!sec) return '--';
        var m = Math.floor(sec / 60);
        var s = Math.floor(sec % 60);
        return m + ':' + s.toString().padStart(2, '0');
      }

      function setStatus(text, color) {
        var el = document.getElementById('pstatus');
        if (!el) return;
        el.className = 'status status-' + color;
        document.getElementById('pstatustext').textContent = text;
      }

      function setPlayIcon(playing) {
        pplayicon.innerHTML = playing ? ICON_PAUSE : ICON_PLAY;
        if ('mediaSession' in navigator) {
          try { navigator.mediaSession.playbackState = playing ? 'playing' : 'paused'; } catch (e) {}
        }
      }

      function card(s, idx) {
        var el = document.createElement('article');
        el.className = 'card';
        el.setAttribute('data-reveal', '');
        var tags = (s.tags || []).slice(0, 4).map(function (t) {
          return '<span class="chip">' + escapeHtml(t) + '</span>';
        }).join('');
        var hasThumb = s.thumbnail && s.thumbnail.indexOf('default.svg') === -1;
        var thumb = hasThumb
          ? '<img class="card-thumb" loading="lazy" src="' + escapeHtml(s.thumbnail) + '" alt="' + escapeHtml(s.title) + ' album art">'
          : '<div class="card-thumb-fallback">IOTA / DEMO</div>';
        el.innerHTML = thumb +
          '<div class="card-title">' + escapeHtml(s.title) + '</div>' +
          '<div class="card-meta">' + escapeHtml(s.artist || 'Unknown') + '  &middot;  ' + fmtDuration(s.duration_seconds) + '</div>' +
          '<div style="margin:10px 0 12px;min-height:22px">' + tags + '</div>' +
          '<div style="display:flex;gap:8px">' +
            '<button class="btn btn-accent play" type="button" style="flex:1">' +
              '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" style="vertical-align:middle;margin-right:4px">' + ICON_PLAY + '</svg>PLAY</button>' +
            '<button class="btn copy-btn" type="button" style="flex:1" data-id="' + escapeHtml(s.video_id) + '">COPY ID</button>' +
          '</div>';
        el.querySelector('.play').onclick = function () { playAt(idx); };
        el.querySelector('.copy-btn').onclick = function () {
          if (window.copyToClipboard) window.copyToClipboard(s.video_id);
        };
        return el;
      }

      function playAt(idx) {
        if (idx < 0 || idx >= queue.length) return;
        qIndex = idx;
        var s = queue[idx];
        var el = results.children[idx] || null;
        if (currentCard) {
          currentCard.classList.remove('playing');
          currentCard.removeAttribute('aria-current');
        }
        currentCard = el;
        if (currentCard) {
          currentCard.classList.add('playing');
          currentCard.setAttribute('aria-current', 'true');
        }
        ptitle.textContent = s.title;
        pmeta.textContent = (s.artist || 'Unknown') + '  ·  ' + s.video_id;
        var hasThumb = s.thumbnail && s.thumbnail.indexOf('default.svg') === -1;
        pthumb.style.display = hasThumb ? 'block' : 'none';
        if (hasThumb) pthumb.src = s.thumbnail;
        audioEl.src = s.stream_url;
        audioEl.volume = pvol.value;
        player.style.display = 'block';
        audioEl.play().then(function () {
          setStatus('PLAYING', 'green');
        }).catch(function () {
          setStatus('ERROR', 'red');
        });
        setStatus('BUFFERING', 'amber');
        player.scrollIntoView({behavior: 'smooth', block: 'nearest'});
        if ('mediaSession' in navigator) {
          try {
            navigator.mediaSession.metadata = new MediaMetadata({
              title: s.title || 'Unknown track',
              artist: s.artist || 'Iota',
              artwork: hasThumb ? [{src: s.thumbnail, sizes: '512x288', type: 'image/jpeg'}] : []
            });
          } catch (e) {}
        }
      }

      pplay.onclick = function () {
        if (!audioEl.src) return;
        if (audioEl.paused) audioEl.play().catch(function () { setStatus('ERROR', 'red'); });
        else audioEl.pause();
      };
      pprev.onclick = function () { playAt(qIndex - 1); };
      pnext.onclick = function () { playAt(qIndex + 1); };
      pclose.onclick = function () { audioEl.pause(); player.style.display = 'none'; };

      audioEl.addEventListener('play', function () { setPlayIcon(true); });
      audioEl.addEventListener('pause', function () { setPlayIcon(false); setStatus('PAUSED', 'gray'); });
      audioEl.addEventListener('playing', function () { setPlayIcon(true); setStatus('PLAYING', 'green'); });
      audioEl.addEventListener('waiting', function () { setStatus('BUFFERING', 'amber'); });
      audioEl.addEventListener('error', function () {
        setPlayIcon(false);
        setStatus('ERROR', 'red');
        if (window.showToast) showToast('Playback failed - press PLAY to retry', 'error');
      });
      audioEl.addEventListener('ended', function () {
        if (qIndex < queue.length - 1) { playAt(qIndex + 1); return; }
        setPlayIcon(false);
        pfill.style.width = '0%';
        pcur.textContent = '0:00';
        setStatus('ENDED', 'gray');
      });
      audioEl.addEventListener('loadedmetadata', function () {
        pdur.textContent = fmtDuration(audioEl.duration || 0);
        ptrack.setAttribute('aria-valuemax', Math.round(audioEl.duration || 0));
      });
      audioEl.addEventListener('timeupdate', function () {
        var d = audioEl.duration || 0;
        var t = audioEl.currentTime || 0;
        var pct = d > 0 ? (t / d * 100) : 0;
        pfill.style.width = pct + '%';
        pcur.textContent = fmtDuration(t);
        ptrack.setAttribute('aria-valuenow', Math.round(t));
        ptrack.setAttribute('aria-valuetext', fmtDuration(t) + ' of ' + fmtDuration(d));
      });

      function seekToRatio(ratio) {
        var d = audioEl.duration || 0;
        if (!d) return;
        audioEl.currentTime = Math.min(1, Math.max(0, ratio)) * d;
      }
      ptrack.onclick = function (e) {
        var rect = ptrack.getBoundingClientRect();
        seekToRatio((e.clientX - rect.left) / rect.width);
      };
      ptrack.onkeydown = function (e) {
        var d = audioEl.duration || 0;
        if (!d) return;
        var t = audioEl.currentTime || 0;
        if (e.key === 'ArrowRight') { audioEl.currentTime = Math.min(d, t + 5); e.preventDefault(); }
        else if (e.key === 'ArrowLeft') { audioEl.currentTime = Math.max(0, t - 5); e.preventDefault(); }
        else if (e.key === 'Home') { audioEl.currentTime = 0; e.preventDefault(); }
        else if (e.key === 'End') { audioEl.currentTime = d; e.preventDefault(); }
      };

      (function restoreVolume() {
        var v = parseFloat(localStorage.getItem('iota-vol'));
        if (!isNaN(v) && v >= 0 && v <= 1) pvol.value = v;
        audioEl.volume = parseFloat(pvol.value);
      })();
      pvol.oninput = function () {
        audioEl.volume = pvol.value;
        localStorage.setItem('iota-vol', String(pvol.value));
      };

      if ('mediaSession' in navigator) {
        try {
          navigator.mediaSession.setActionHandler('play', function () { audioEl.play().catch(function () {}); });
          navigator.mediaSession.setActionHandler('pause', function () { audioEl.pause(); });
          navigator.mediaSession.setActionHandler('previoustrack', function () { playAt(qIndex - 1); });
          navigator.mediaSession.setActionHandler('nexttrack', function () { playAt(qIndex + 1); });
        } catch (e) {}
      }

      function run(url) {
        var seq = ++runSeq;
        results.innerHTML = '';
        for (var i = 0; i < 6; i++) {
          var sk = document.createElement('div');
          sk.className = 'skeleton';
          sk.style.height = '16px';
          sk.style.marginBottom = '8px';
          results.appendChild(sk);
        }
        fetch(url).then(function (r) { return r.json(); }).then(function (data) {
          if (seq !== runSeq) return;
          var list = data.results || [];
          queue = list;
          qIndex = -1;
          if (currentCard) {
            currentCard.classList.remove('playing');
            currentCard.removeAttribute('aria-current');
            currentCard = null;
          }
          results.innerHTML = '';
          list.forEach(function (s, i) { results.appendChild(card(s, i)); });
          resultCount.textContent = list.length
            ? (list.length + ' result' + (list.length === 1 ? '' : 's') + '  ·  provider-backed audio')
            : '';
          if (!list.length) {
            results.innerHTML = '<div class="empty"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg><h3>No matches found</h3><p>Try a different search term.</p></div>';
          }
        }).catch(function () {
          if (seq !== runSeq) return;
          results.innerHTML = '<div class="empty"><h3>Error</h3><p>Failed to fetch results.</p><button class="btn" id="retry" type="button">Retry</button></div>';
          var rb = document.getElementById('retry');
          if (rb) rb.onclick = function () { run(url); };
          if (window.showToast) showToast('Failed to load results', 'error');
        });
      }

      function closeSuggest() {
        suggestBox.classList.remove('open');
        suggestBox.innerHTML = '';
        sugItems = [];
        sugActive = -1;
        qInput.setAttribute('aria-expanded', 'false');
        qInput.removeAttribute('aria-activedescendant');
      }

      function highlightSuggest(n) {
        if (!sugItems.length) return;
        sugActive = (n + sugItems.length) % sugItems.length;
        sugItems.forEach(function (it, i) {
          if (i === sugActive) { it.classList.add('active'); it.setAttribute('aria-selected', 'true'); }
          else { it.classList.remove('active'); it.setAttribute('aria-selected', 'false'); }
        });
        qInput.setAttribute('aria-activedescendant', 'sug-' + sugActive);
      }

      function chooseSuggest() {
        if (sugActive < 0 || !sugItems[sugActive]) return false;
        qInput.value = sugItems[sugActive].getAttribute('data-v');
        closeSuggest();
        run('/api/search?q=' + encodeURIComponent(qInput.value));
        return true;
      }

      var suggestTimer = null;
      qInput.addEventListener('input', function () {
        clearTimeout(suggestTimer);
        var q = qInput.value.trim();
        if (q.length < 2) { closeSuggest(); return; }
        suggestTimer = setTimeout(function () {
          var seq = ++suggestSeq;
          fetch('/api/suggest?q=' + encodeURIComponent(q)).then(function (r) { return r.json(); }).then(function (data) {
            if (seq !== suggestSeq) return;
            var items = data.suggestions || [];
            if (!items.length) { closeSuggest(); return; }
            sugActive = -1;
            suggestBox.innerHTML = items.map(function (t, i) {
              return '<div class="suggest-item" role="option" id="sug-' + i + '" data-v="' + escapeHtml(t) + '">' + escapeHtml(t) + '</div>';
            }).join('');
            sugItems = [].slice.call(suggestBox.querySelectorAll('.suggest-item'));
            sugItems.forEach(function (it) {
              it.onclick = function () {
                qInput.value = it.getAttribute('data-v');
                closeSuggest();
                run('/api/search?q=' + encodeURIComponent(qInput.value));
              };
            });
            suggestBox.classList.add('open');
            qInput.setAttribute('aria-expanded', 'true');
          }).catch(function () {});
        }, 200);
      });
      qInput.addEventListener('blur', function () { setTimeout(closeSuggest, 150); });
      qInput.addEventListener('keydown', function (e) {
        var open = suggestBox.classList.contains('open');
        if (e.key === 'ArrowDown' && open) { highlightSuggest(sugActive + 1); e.preventDefault(); }
        else if (e.key === 'ArrowUp' && open) { highlightSuggest(sugActive - 1); e.preventDefault(); }
        else if (e.key === 'Escape') { closeSuggest(); }
        else if (e.key === 'Enter') {
          if (open && chooseSuggest()) { e.preventDefault(); return; }
          closeSuggest();
          run('/api/search?q=' + encodeURIComponent(qInput.value || 'iota'));
        }
      });

      getkeyBtn.onclick = function () {
        getkeyBtn.disabled = true;
        fetch('/api/v1/keys/anonymous', {method: 'POST'}).then(function (r) { return r.json(); }).then(function (d) {
          getkeyBtn.disabled = false;
          if (d && d.raw_key) {
            if (window.copyToClipboard) window.copyToClipboard(d.raw_key);
            if (window.showToast) showToast('Sandbox key ready - send it as X-API-Key', 'success');
          } else {
            if (window.showToast) showToast('Could not issue a key', 'error');
          }
        }).catch(function () {
          getkeyBtn.disabled = false;
          if (window.showToast) showToast('Could not issue a key', 'error');
        });
      };

      document.getElementById('go').onclick = function () { run('/api/search?q=' + encodeURIComponent(qInput.value || 'iota')); };
      document.getElementById('rand').onclick = function () { run('/api/random?limit=12'); };
      run('/api/trending?limit=12');
    })();
    </script>
    """
    return _page("Iota Songs API", body.replace('{INFRA_DIAGRAM_PLACEHOLDER}', INFRA_DIAGRAM))


def docs_html() -> str:
    body = """
    <section class="section">
      <div class="label">DOCUMENTATION</div>
      <h1>Iota API reference</h1>
      <p class="lead">
        Interactive API scratchpad. Enter an endpoint path to inspect responses.
      </p>
    </section>

    <section class="section">
      <div class="panel">
        <div class="label">ENDPOINT</div>
        <div class="console-border" style="margin-bottom:12px">
          <span class="console-prompt">GET</span>
          <input id="path" value="/api/search?q=adele&limit=5" aria-label="API path">
        </div>
        <button class="btn btn-primary" id="send" type="button">Send request</button>
        <div class="divider-accent"></div>
        <pre id="out"><code class="muted">Response output will appear here...</code></pre>
      </div>
    </section>

    <section class="section">
      <div class="label">CATALOG</div>
      <h2>Public endpoints (no API key)</h2>
      <div class="grid">
        <div class="card">
          <div class="label">SEARCH</div>
          <div class="card-title">GET /api/search</div>
          <div class="card-meta">Query params: q, limit</div>
        </div>
        <div class="card">
          <div class="label">LOOK UP</div>
          <div class="card-title">GET /api/song/{video_id}</div>
          <div class="card-meta">Get one song by ID</div>
        </div>
        <div class="card">
          <div class="label">RANDOM</div>
          <div class="card-title">GET /api/random</div>
          <div class="card-meta">Random picks</div>
        </div>
        <div class="card">
          <div class="label">STREAM</div>
          <div class="card-title">GET /api/file/{video_id}</div>
          <div class="card-meta">Real audio (m4a) + demo WAV, Range / 206</div>
        </div>
      </div>
      <p class="section-note">The public catalog indexes real tracks. <code>/api/file/{video_id}</code> streams the actual provider audio (YouTube, <code>audio/mp4</code>) for catalog tracks and a synthetic WAV for demo tracks — no API key required, IP rate-limited. Only IDs present in the curated catalog resolve, so this is not an open proxy.</p>
    </section>

    <section class="section">
      <div class="label">MEDIA</div>
      <h2>Media endpoints (X-API-Key required)</h2>
      <div class="grid">
        <div class="card">
          <div class="label">STREAM</div>
          <div class="card-title">GET /stream/{media_id}</div>
          <div class="card-meta">Inline audio/video streaming, Range / 206</div>
        </div>
        <div class="card">
          <div class="label">DOWNLOAD</div>
          <div class="card-title">GET /download/{media_id}</div>
          <div class="card-meta">?kind=audio|video — file attachment, Range / 206</div>
        </div>
        <div class="card">
          <div class="label">INFO</div>
          <div class="card-title">GET /info/{media_id}</div>
          <div class="card-meta">Metadata, cached</div>
        </div>
        <div class="card">
          <div class="label">SEARCH</div>
          <div class="card-title">GET /search</div>
          <div class="card-meta">Fan-out provider search: q, limit</div>
        </div>
      </div>
      <p class="section-note">YouTube serves most videos as separate DASH tracks: <code>kind=audio</code> returns the audio stream (m4a), <code>kind=video</code> returns the video stream (mp4). Videos with a single muxed file include audio in <code>kind=video</code>.</p>
      <p class="section-note">Authenticated endpoints are rate-limited per API key (requests/minute, daily quota, concurrent streams). Create a key via <code>POST /admin/keys</code> with <code>rate_per_minute=0</code>, <code>daily_limit=0</code>, <code>concurrent_streams_limit=0</code> for unlimited — reserved for trusted bot backends.</p>
    </section>

    <section class="section">
      <div class="label">IOTADB</div>
      <h2>IotaDB endpoints (X-API-Key required)</h2>
      <div class="grid">
        <div class="card">
          <div class="label">WRITE</div>
          <div class="card-title">POST /api/v1/db/{collection}/insert</div>
          <div class="card-meta">Insert documents</div>
        </div>
        <div class="card">
          <div class="label">QUERY</div>
          <div class="card-title">POST /api/v1/db/{collection}/find</div>
          <div class="card-meta">Query with MongoDB-like operators</div>
        </div>
        <div class="card">
          <div class="label">CRUD</div>
          <div class="card-title">GET/PUT/DELETE /api/v1/db/{id}</div>
          <div class="card-meta">Single document ops</div>
        </div>
        <div class="card">
          <div class="label">UPLOAD</div>
          <div class="card-title">POST /api/v1/storage/upload</div>
          <div class="card-meta">File storage</div>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="label">AUTHENTICATION</div>
      <p>
        Keys: <code class="inline">X-API-Key: iota_live_...</code>
        or create a sandbox key at
        <code class="inline">POST /api/v1/keys/anonymous</code>.
        Visit the <a href="/db">IotaDB dashboard</a> for an interactive playground.
      </p>
    </section>

    <section class="section">
      <div class="label">SINGLE BASE</div>
      <h2>Every endpoint under /v1 (OpenAI-style)</h2>
      <p class="section-note">Every endpoint is also reachable under a single <code>/v1</code> base: <code>/v1/search</code>, <code>/v1/stream/{media_id}</code>, <code>/v1/download/{media_id}</code>, <code>/v1/info/{media_id}</code>, <code>/v1/library/...</code>, <code>/v1/db/...</code>. The root (<code>/search</code>, <code>/stream</code>, ...) and <code>/api/v1/...</code> paths keep working too, so the prefix is forgiving.</p>
    </section>

    <script>
    document.getElementById('send').onclick = async () => {
      const path = document.getElementById('path').value;
      const out = document.getElementById('out');
      out.innerHTML = '<span class="skeleton" style="height:20px;width:120px"></span>';
      try {
        const r = await fetch(path);
        const text = await r.text();
        out.innerHTML = '<pre style="margin:0">' + text.replace(/</g,'&lt;') + '</pre>';
      } catch (err) {
        out.innerHTML = '<span style="color:var(--i-accent)">Error: ' + err.message + '</span>';
      }
    };
    </script>
    """
    return _page("Iota API docs", body)


def privacy_html() -> str:
    return _page(
        "Iota privacy",
        """
        <section class="section">
          <div class="label">PRIVACY POLICY</div>
          <h1>Iota privacy</h1>
          <div class="panel">
            <p>
              Catalog search is anonymous. IotaDB stores documents and files you upload.
              API keys are hashed with SHA-256 at rest. Do not put secrets in public catalogs.
            </p>
          </div>
        </section>
        """,
    )


def terms_html() -> str:
    return _page(
        "Iota terms",
        """
        <section class="section">
          <div class="label">TERMS OF SERVICE</div>
          <h1>Iota terms</h1>
          <div class="panel">
            <p>
              Demo catalog tracks are original placeholders, not third-party commercial recordings.
              You are responsible for media you store in IotaDB. Rate limits apply to public endpoints.
            </p>
          </div>
        </section>
        """,
    )


def db_dashboard_html() -> str:
    body = """
    <section class="section">
      <div class="label">IOTADB / DATA LAB</div>
      <h1>IotaDB</h1>
      <p class="lead">
        JSON documents + object storage. Create a sandbox key, then insert and query.
      </p>
    </section>

    <section class="section">
      <div class="stats-grid">
        <div class="panel-dark">
          <div class="stat-number" id="stats-docs">--</div>
          <div class="stat-label">DOCUMENTS</div>
        </div>
        <div class="panel-dark">
          <div class="stat-number" id="stats-collections">--</div>
          <div class="stat-label">COLLECTIONS</div>
        </div>
        <div class="panel-dark">
          <div class="stat-number" id="stats-keys">--</div>
          <div class="stat-label">API KEYS</div>
        </div>
        <div class="panel-dark">
          <div class="stat-number" id="stats-files">--</div>
          <div class="stat-label">FILES</div>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="panel">
        <div class="label">SANDBOX KEY</div>
        <button class="btn btn-primary mb-2" id="make" type="button">Create sandbox key</button>
        <label for="keyout">Your key (save it — it cannot be recovered)</label>
        <input id="keyout" readonly aria-label="Generated API key">

        <div class="label" style="margin-top:20px">COLLECTION</div>
        <input id="coll" value="posts" aria-label="Collection name">

        <div style="display:flex;gap:8px;margin-top:20px">
          <button class="btn" id="ins" type="button">Insert demo</button>
          <button class="btn" id="find" type="button">Find</button>
          <button class="btn" id="aggregate" type="button">Aggregate</button>
        </div>
      </div>

      <div class="panel-dark">
        <div class="label">RESPONSE</div>
        <pre id="out"><code class="muted">Awaiting query. Insert a document or run a find.</code></pre>
      </div>
    </section>

    <script>
    let key = '';
    const out = document.getElementById('out');

    async function call(method, url, body) {
      const opt = { method, headers: { 'Content-Type': 'application/json' } };
      if (key) opt.headers['X-API-Key'] = key;
      if (body) opt.body = JSON.stringify(body);
      const r = await fetch(url, opt);
      if (!r.ok) {
        const e = await r.json().catch(() => ({}));
        throw new Error(r.statusText + ': ' + (e.error || e.detail || ''));
      }
      return r.json();
    }

    function showMsg(msg, type) {
      out.innerHTML = '<pre style="margin:0">' + msg.replace(/</g,'&lt;') + '</pre>';
    }

    async function updateStats() {
      try {
        const keys = await call('GET', '/api/v1/db/keys');
        document.getElementById('stats-keys').textContent = keys.keys ? keys.keys.length : '--';
      } catch { document.getElementById('stats-keys').textContent = '—'; }
      try {
        const files = await call('GET', '/api/v1/storage/files');
        document.getElementById('stats-files').textContent = files.files ? files.files.length : '--';
      } catch { document.getElementById('stats-files').textContent = '—'; }
      try {
        const cols = await call('GET', '/api/v1/db/collections');
        document.getElementById('stats-collections').textContent = cols.collections ? cols.collections.length : '--';
      } catch { document.getElementById('stats-collections').textContent = '—'; }
    }

    document.getElementById('make').onclick = async () => {
      out.innerHTML = '<span class="skeleton" style="height:20px;width:140px"></span>';
      try {
        const data = await call('POST', '/api/v1/keys/anonymous');
        key = data.raw_key || '';
        document.getElementById('keyout').value = key || JSON.stringify(data);
      } catch (err) {
        document.getElementById('keyout').value = '';
        showMsg('Error: ' + err.message, 'error');
      }
    };

    document.getElementById('ins').onclick = async () => {
      out.innerHTML = '<span class="skeleton" style="height:20px;width:140px"></span>';
      try {
        const coll = document.getElementById('coll').value || 'posts';
        const data = await call('POST', '/api/v1/db/' + coll + '/insert', { title: 'Hello Iota', likes: 1 });
        showMsg(JSON.stringify(data, null, 2));
        updateStats();
      } catch (err) { showMsg('Error: ' + err.message); }
    };

    document.getElementById('find').onclick = async () => {
      out.innerHTML = '<span class="skeleton" style="height:20px;width:140px"></span>';
      try {
        const coll = document.getElementById('coll').value || 'posts';
        const data = await call('POST', '/api/v1/db/' + coll + '/find', {});
        showMsg(JSON.stringify(data, null, 2));
      } catch (err) { showMsg('Error: ' + err.message); }
    };

    document.getElementById('aggregate').onclick = async () => {
      out.innerHTML = '<span class="skeleton" style="height:20px;width:140px"></span>';
      try {
        const coll = document.getElementById('coll').value || 'posts';
        const data = await call('POST', '/api/v1/db/' + coll + '/aggregate', { pipeline: [{ '$count': 'total' }] });
        showMsg(JSON.stringify(data, null, 2));
      } catch (err) { showMsg('Error: ' + err.message); }
    };

    updateStats();
    </script>
    """
    return _page("IotaDB", body)
