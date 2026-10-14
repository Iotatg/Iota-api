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
    <button class="mu-menu-btn" id="muMenuBtn" type="button" aria-haspopup="true" aria-expanded="false" aria-controls="muMenu" aria-label="Open menu">
      <span class="mu-menu-line"></span>
      <span class="mu-menu-line"></span>
      <span class="mu-menu-line"></span>
    </button>
  </div>
  <div class="mu-menu" id="muMenu" aria-hidden="true">
    <div class="mu-menu-inner">
      <div class="mu-menu-title">EXPLORE</div>
      <a class="mu-menu-item" href="/">
        <span class="mu-menu-ico"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 11.5 12 4l9 7.5"/><path d="M6 10v10h12V10"/></svg></span>
        <span class="mu-menu-txt"><span class="mu-menu-label">Home &middot; Player</span><span class="mu-menu-desc">Search any song, hit play</span></span>
      </a>
      <a class="mu-menu-item" href="/docs">
        <span class="mu-menu-ico"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h9l4 4v14H6z"/><path d="M9 11h7M9 15h7"/></svg></span>
        <span class="mu-menu-txt"><span class="mu-menu-label">API Docs</span><span class="mu-menu-desc">Reference + request playground</span></span>
      </a>
      <a class="mu-menu-item" href="/about">
        <span class="mu-menu-ico"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 8h.01M12 11v6"/></svg></span>
        <span class="mu-menu-txt"><span class="mu-menu-label">About Iota</span><span class="mu-menu-desc">The story of this API</span></span>
      </a>
      <div class="mu-menu-sep"></div>
      <div class="mu-menu-title">POWER TOOLS</div>
      <a class="mu-menu-item" href="/db">
        <span class="mu-menu-ico"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="6" rx="7" ry="3"/><path d="M5 6v12c0 1.7 3.1 3 7 3s7-1.3 7-3V6"/><path d="M5 12c0 1.7 3.1 3 7 3s7-1.3 7-3"/></svg></span>
        <span class="mu-menu-txt"><span class="mu-menu-label">IotaDB</span><span class="mu-menu-desc">Embedded document database</span></span>
      </a>
      <a class="mu-menu-item" href="/status">
        <span class="mu-menu-ico"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M3 12h4l2.5-6 4 12 2.5-6h5"/></svg></span>
        <span class="mu-menu-txt"><span class="mu-menu-label">Live Stats</span><span class="mu-menu-desc">Streams, downloads &amp; latency, live</span></span>
      </a>
      <a class="mu-menu-item" href="/health">
        <span class="mu-menu-ico"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12h4l2.5-6 4 12 2.5-6h5"/></svg></span>
        <span class="mu-menu-txt"><span class="mu-menu-label">Health</span><span class="mu-menu-desc">Service + dependency status</span></span>
      </a>
      <div class="mu-menu-sep"></div>
      <div class="mu-menu-title">LEGAL</div>
      <a class="mu-menu-item" href="/privacy">
        <span class="mu-menu-ico"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3 5 6v6c0 4.4 3 7.4 7 9 4-1.6 7-4.6 7-9V6z"/></svg></span>
        <span class="mu-menu-txt"><span class="mu-menu-label">Privacy</span><span class="mu-menu-desc">No accounts, no trackers</span></span>
      </a>
      <a class="mu-menu-item" href="/terms">
        <span class="mu-menu-ico"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M7 4h11v17H7z"/><path d="M9.5 9h6M9.5 12.5h6M9.5 16h4"/></svg></span>
        <span class="mu-menu-txt"><span class="mu-menu-label">Terms</span><span class="mu-menu-desc">Fair-use ground rules</span></span>
      </a>
    </div>
  </div>
</nav>
<script>
(function () {
  var btn = document.getElementById('muMenuBtn');
  var menu = document.getElementById('muMenu');
  if (!btn || !menu) return;
  function setOpen(open) {
    menu.classList.toggle('open', open);
    btn.classList.toggle('open', open);
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    menu.setAttribute('aria-hidden', open ? 'false' : 'true');
    btn.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
  }
  btn.addEventListener('click', function (e) {
    e.stopPropagation();
    setOpen(!menu.classList.contains('open'));
  });
  document.addEventListener('click', function (e) {
    if (!menu.classList.contains('open')) return;
    if (menu.contains(e.target) || btn.contains(e.target)) return;
    setOpen(false);
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') setOpen(false);
  });
  var path = location.pathname.replace(/\\/$/, '') || '/';
  [].forEach.call(document.querySelectorAll('.nav-link, .mu-menu-item'), function (a) {
    var href = (a.getAttribute('href') || '').replace(/\\/$/, '');
    if (href !== path) return;
    a.classList.add('active');
  });
})();
</script>
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
.card-thumb-fallback { aspect-ratio: 16 / 9; display: flex; align-items: center; justify-content: center;
  font-family: var(--i-font-display); font-weight: 600; font-size: 1.4rem; letter-spacing: 0.14em;
  color: var(--i-ink-lighter); background: var(--i-bg-paper-alt); border: 1px solid var(--i-border); }
.card-chips { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; margin: 10px 0 12px; min-height: 22px; }
.chip-provider { font-family: var(--i-font-mono); font-size: 0.62rem; letter-spacing: 0.08em;
  border-color: var(--i-accent-line) !important; color: var(--i-accent) !important; }
.result-count { transition: color 0.2s ease; }

/* ===== IOTA dark theme — every page ===== */
:root {
  --i-bg-paper: #0d0d10;
  --i-bg-paper-alt: #141419;
  --i-bg-light: #1b1b21;
  --i-bg-light-2: #26262d;
  --i-bg-mid: #2b2b32;
  --i-panel: #1b1b21;
  --i-ink: #f2f0ec;
  --i-ink-muted: rgba(242, 240, 236, 0.55);
  --i-ink-lighter: rgba(242, 240, 236, 0.38);
  --i-border: rgba(255, 255, 255, 0.1);
  --i-border-dark: rgba(255, 255, 255, 0.12);
  --i-accent-soft: rgba(217, 119, 6, 0.14);
  --i-accent-line: rgba(217, 119, 6, 0.32);
  --i-radius: 8px;
  --i-radius-panel: 16px;
}
body {
  background: #0d0d10;
  color: #f2f0ec;
  background-image:
    radial-gradient(640px 420px at 85% -10%, rgba(217, 119, 6, 0.13), transparent 62%),
    radial-gradient(520px 400px at -12% 30%, rgba(251, 113, 133, 0.06), transparent 60%),
    radial-gradient(760px 520px at 55% 115%, rgba(217, 119, 6, 0.06), transparent 62%);
  background-attachment: fixed;
}
h1, h2, h3, h4, h5 { color: #f2f0ec; letter-spacing: -0.01em; }
p, li { color: rgba(242, 240, 236, 0.6); }
p strong, li strong { color: rgba(242, 240, 236, 0.92); }
a { color: #fbbf24; }
::selection { background: rgba(217, 119, 6, 0.4); }
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #2a2a30; border-radius: 8px; border: 2px solid #0d0d10; }
::-webkit-scrollbar-thumb:hover { background: #3d3d46; }

.nav {
  background: rgba(13, 13, 16, 0.72);
  -webkit-backdrop-filter: blur(16px) saturate(1.4);
  backdrop-filter: blur(16px) saturate(1.4);
  border-bottom-color: rgba(255, 255, 255, 0.08);
}
.nav.scrolled {
  background: rgba(13, 13, 16, 0.86);
  box-shadow: 0 10px 34px rgba(0, 0, 0, 0.4);
}
.brand-text { color: #f2f0ec; }

.panel { background: rgba(255, 255, 255, 0.035); border-color: rgba(255, 255, 255, 0.09); }
.panel-dark { background: #121217; border-color: rgba(255, 255, 255, 0.09); color: rgba(242, 240, 236, 0.8); }
.panel-darker { background: #0f0f13; }
.panel-invert { background: #f2f0ec; border: none; color: #14100b; }
.panel-invert .label { color: rgba(20, 16, 11, 0.55); }
.panel-invert p { color: rgba(20, 16, 11, 0.7); }
.card { background: rgba(255, 255, 255, 0.035); border-color: rgba(255, 255, 255, 0.08); }
.card:hover { box-shadow: 0 16px 40px rgba(0, 0, 0, 0.35); }
.card-dark { background: #121217; }
.card-dark .card-title, .card-dark .card-meta { color: rgba(242, 240, 236, 0.85); }
.card-title { color: #f2f0ec; }
.card-meta { color: rgba(242, 240, 236, 0.5); }

.console-border { background: #141419; border-color: rgba(255, 255, 255, 0.1); border-radius: 12px; }
.console-border:focus-within {
  border-color: rgba(245, 158, 11, 0.7);
  box-shadow: 0 0 0 3px rgba(217, 119, 6, 0.14), 0 0 24px rgba(217, 119, 6, 0.08);
}
.console input { color: #f2f0ec; }
input, textarea, select {
  background: #141419;
  color: #f2f0ec;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 10px;
}
input::placeholder { color: rgba(242, 240, 236, 0.35); }
input:focus, textarea:focus, select:focus {
  border-color: rgba(245, 158, 11, 0.6);
  box-shadow: 0 0 0 3px rgba(217, 119, 6, 0.12);
}
input[readonly] { background: #101014; }

pre { background: #121217; color: #dcdbd7; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; }
pre code { background: transparent; }
.btn { background: rgba(255, 255, 255, 0.05); color: #f2f0ec; border: 1px solid rgba(255, 255, 255, 0.13); border-radius: 12px; }
.btn:hover { background: rgba(255, 255, 255, 0.09); border-color: rgba(245, 158, 11, 0.5); }
.btn-ghost, .btn-ghost-dark { color: rgba(242, 240, 236, 0.8); }
.toast {
  background: rgba(18, 18, 22, 0.92);
  -webkit-backdrop-filter: blur(14px);
  backdrop-filter: blur(14px);
  color: #f2f0ec;
  border-radius: 12px;
}
.suggest-list { background: rgba(20, 20, 26, 0.97); border-color: rgba(255, 255, 255, 0.1); border-radius: 12px; }
.suggest-item:hover { background: rgba(217, 119, 6, 0.12); color: #fbbf24; }
.tech-table th { background: rgba(255, 255, 255, 0.04); color: rgba(242, 240, 236, 0.6); }
.tech-table td { color: rgba(242, 240, 236, 0.72); }
.skeleton { background: linear-gradient(90deg, #1a1a20 25%, #26262d 50%, #1a1a20 75%); background-size: 200% 100%; }
.corner-mark { border-color: rgba(255, 255, 255, 0.16); }
.chip { background: rgba(255, 255, 255, 0.05); color: rgba(242, 240, 236, 0.62); }
label { color: rgba(242, 240, 236, 0.55); }
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
  .mu-menu {
    top: 60px;
    right: 10px;
  }
}

/* ---- hamburger menu (all pages) ---- */
.mu-menu-btn {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: rgba(217, 119, 6, 0.1);
  border: 1px solid rgba(217, 119, 6, 0.4);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  flex: none;
  transition: all 0.25s var(--i-ease);
}
.mu-menu-line {
  width: 16px;
  height: 2px;
  border-radius: 2px;
  background: var(--i-accent);
  transition: all 0.3s var(--i-ease);
}
.mu-menu-btn:hover {
  background: rgba(217, 119, 6, 0.22);
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(217, 119, 6, 0.3);
}
.mu-menu-btn:active { transform: scale(0.94); }
.mu-menu-btn.open .mu-menu-line:nth-child(1) { transform: translateY(6px) rotate(45deg); }
.mu-menu-btn.open .mu-menu-line:nth-child(2) { opacity: 0; transform: scaleX(0.3); }
.mu-menu-btn.open .mu-menu-line:nth-child(3) { transform: translateY(-6px) rotate(-45deg); }

.mu-menu {
  position: fixed;
  top: 64px;
  right: 16px;
  z-index: 120;
  width: min(340px, calc(100vw - 24px));
  border-radius: 18px;
  background: rgba(15, 15, 18, 0.94);
  -webkit-backdrop-filter: blur(22px) saturate(1.4);
  backdrop-filter: blur(22px) saturate(1.4);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 30px 70px rgba(0, 0, 0, 0.55), 0 0 0 1px rgba(217, 119, 6, 0.06);
  opacity: 0;
  transform: translateY(-10px) scale(0.98);
  transform-origin: top right;
  pointer-events: none;
  transition: all 0.28s var(--i-ease);
  overflow: hidden;
}
.mu-menu::before {
  content: '';
  position: absolute;
  top: -70px;
  right: -40px;
  width: 220px;
  height: 200px;
  pointer-events: none;
  background: radial-gradient(closest-side, rgba(217, 119, 6, 0.2), transparent);
}
.mu-menu.open {
  opacity: 1;
  transform: none;
  pointer-events: auto;
}
.mu-menu-inner {
  position: relative;
  padding: 8px;
}
.mu-menu-title {
  font-family: var(--i-font-mono);
  font-size: 0.6rem;
  letter-spacing: 0.2em;
  color: rgba(242, 240, 236, 0.38);
  padding: 12px 12px 6px;
}
.mu-menu-sep {
  height: 1px;
  background: rgba(255, 255, 255, 0.07);
  margin: 6px 12px;
}
.mu-menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 9px 12px;
  border-radius: 12px;
  text-decoration: none;
  border: 1px solid transparent;
  transition: all 0.2s var(--i-ease);
}
.mu-menu-item:hover {
  background: rgba(217, 119, 6, 0.1);
  border-color: rgba(217, 119, 6, 0.28);
  transform: translateX(3px);
}
.mu-menu-item.active {
  border-color: rgba(245, 158, 11, 0.45);
  background: rgba(217, 119, 6, 0.1);
}
.mu-menu-ico {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.09);
  display: grid;
  place-items: center;
  color: #fbbf24;
  flex: none;
}
.mu-menu-item.active .mu-menu-ico {
  background: rgba(217, 119, 6, 0.18);
  border-color: rgba(245, 158, 11, 0.4);
}
.mu-menu-txt {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.mu-menu-label {
  font-family: var(--i-font-mono);
  font-size: 0.74rem;
  letter-spacing: 0.06em;
  color: #f2f0ec;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.mu-menu-item.active .mu-menu-label { color: #fbbf24; }
.mu-menu-desc {
  font-size: 0.68rem;
  color: rgba(242, 240, 236, 0.42);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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
    <style>
      /* ===== IOTA MUSIC UI — landing-scoped theme (ships only with this page) ===== */
      body { background: #0d0d10; color: #f2f0ec; }
      body::before { content: ''; position: fixed; inset: -10%; z-index: -1; pointer-events: none;
        background:
          radial-gradient(640px 420px at 85% -10%, rgba(217, 119, 6, 0.17), transparent 62%),
          radial-gradient(520px 400px at -10% 34%, rgba(251, 113, 133, 0.10), transparent 60%),
          radial-gradient(760px 520px at 55% 112%, rgba(217, 119, 6, 0.09), transparent 62%);
        animation: muDrift 16s ease-in-out infinite alternate; }
      @keyframes muDrift { from { transform: translateY(-10px) scale(1); } to { transform: translateY(12px) scale(1.04); } }

      ::-webkit-scrollbar { width: 10px; height: 10px; }
      ::-webkit-scrollbar-track { background: transparent; }
      ::-webkit-scrollbar-thumb { background: #2a2a30; border-radius: 8px; border: 2px solid #0d0d10; }
      ::-webkit-scrollbar-thumb:hover { background: #3d3d46; }
      ::selection { background: rgba(217, 119, 6, 0.4); }

      /* ---- nav, dark ---- */
      .nav { background: rgba(13, 13, 16, 0.72); -webkit-backdrop-filter: blur(16px) saturate(1.4);
        backdrop-filter: blur(16px) saturate(1.4); border-bottom-color: rgba(255, 255, 255, 0.08); }
      .nav.scrolled { background: rgba(13, 13, 16, 0.86); box-shadow: 0 10px 34px rgba(0, 0, 0, 0.4);
        border-bottom-color: var(--i-accent-line); }
      .brand { color: #f2f0ec; }
      .nav-link { color: rgba(242, 240, 236, 0.55); }
      .nav-link:hover { color: #ffffff; }

      /* ---- hero ---- */
      .mu-hero { position: relative; overflow: visible; padding-top: 34px; }
      .mu-aurora { position: absolute; inset: -60px -10% auto; height: 420px; pointer-events: none; z-index: -1; filter: blur(70px); opacity: .8; }
      .mu-aurora i { position: absolute; border-radius: 50%; }
      .mu-aurora i:nth-child(1) { width: 340px; height: 340px; left: 6%; top: -80px; background: rgba(217, 119, 6, 0.35); animation: muFloat 9s ease-in-out infinite alternate; }
      .mu-aurora i:nth-child(2) { width: 260px; height: 260px; right: 10%; top: -40px; background: rgba(251, 113, 133, 0.20); animation: muFloat 11s ease-in-out infinite alternate-reverse; }
      .mu-aurora i:nth-child(3) { width: 200px; height: 200px; right: 34%; top: 60px; background: rgba(245, 158, 11, 0.16); animation: muFloat 13s ease-in-out infinite alternate; }
      @keyframes muFloat { from { transform: translate3d(0, -22px, 0) scale(1); } to { transform: translate3d(26px, 22px, 0) scale(1.12); } }

      .mu-hero .label { color: rgba(242, 240, 236, 0.55); animation: muRise 0.6s var(--i-ease) both; }
      .mu-hero .label::after { content: '_'; color: var(--i-accent); animation: muBlink 1.1s steps(1) infinite; }
      @keyframes muBlink { 50% { opacity: 0; } }
      @keyframes muRise { from { opacity: 0; transform: translateY(26px); } to { opacity: 1; transform: none; } }

      .mu-title { margin-bottom: 20px !important; }
      .mu-title .mu-line { display: block; font-family: var(--i-font-display); font-weight: 600;
        font-size: clamp(2.6rem, 6.5vw, 4.4rem); letter-spacing: -0.035em; line-height: 1.04;
        animation: muRise 0.7s var(--i-ease) both; }
      .mu-title .mu-line:nth-child(2) { animation-delay: 0.09s; }
      .mu-title .mu-line:nth-child(3) { animation-delay: 0.18s; }
      .mu-title .grad { background: linear-gradient(92deg, #fbbf24 0%, #f59e0b 45%, #fb7185 100%);
        -webkit-background-clip: text; background-clip: text; color: transparent; }

      .mu-hero p.lead { color: rgba(242, 240, 236, 0.62); animation: muRise 0.7s var(--i-ease) 0.26s both; max-width: 640px; }
      .mu-hero p.lead strong { color: rgba(242, 240, 236, 0.9); font-weight: 600; }

      /* ---- search console ---- */
      .console { animation: muRise 0.7s var(--i-ease) 0.34s both; }
      .console .label { color: rgba(242, 240, 236, 0.55); }
      .console-border { border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px;
        background: rgba(255, 255, 255, 0.04); padding: 8px 10px 8px 16px; position: relative;
        transition: border-color var(--i-dur-normal) var(--i-ease), box-shadow var(--i-dur-normal) var(--i-ease), background var(--i-dur-normal) var(--i-ease); }
      .console-border:focus-within { border-color: rgba(245, 158, 11, 0.65);
        box-shadow: 0 0 0 4px rgba(217, 119, 6, 0.14), 0 14px 44px rgba(217, 119, 6, 0.12);
        background: rgba(255, 255, 255, 0.06); }
      .console-prompt { color: var(--i-accent); font-weight: 700; }
      .console input { color: #f2f0ec; font-size: 0.98rem; padding: 8px 0; }
      .console input::placeholder { color: rgba(242, 240, 236, 0.32); }
      .mu-kbd { font-family: var(--i-font-mono); font-size: 0.66rem; color: rgba(242, 240, 236, 0.45);
        border: 1px solid rgba(255, 255, 255, 0.14); border-bottom-width: 2px; border-radius: 6px;
        padding: 2px 8px; flex: none; }

      .btn { background: rgba(255, 255, 255, 0.05); color: #f2f0ec; border: 1px solid rgba(255, 255, 255, 0.13); }
      .btn:hover { background: rgba(255, 255, 255, 0.1); border-color: rgba(245, 158, 11, 0.5); transform: translateY(-1px); }
      .btn:active { transform: translateY(0) scale(0.98); }
      .btn-primary, .btn-accent { background: linear-gradient(135deg, #f59e0b, #d97706); border: none; color: #14100b;
        box-shadow: 0 6px 22px rgba(217, 119, 6, 0.35); font-weight: 600; }
      .btn-primary:hover, .btn-accent:hover { background: linear-gradient(135deg, #fbbf24, #f59e0b);
        box-shadow: 0 10px 30px rgba(217, 119, 6, 0.5); transform: translateY(-1px); }

      .mu-quick { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; animation: muRise 0.7s var(--i-ease) 0.42s both; }
      .mu-chip { font-family: var(--i-font-mono); font-size: 0.72rem; letter-spacing: 0.05em;
        color: rgba(242, 240, 236, 0.65); background: rgba(255, 255, 255, 0.045);
        border: 1px solid rgba(255, 255, 255, 0.11); border-radius: 999px; padding: 7px 14px;
        cursor: pointer; transition: all var(--i-dur-fast) var(--i-ease); }
      .mu-chip:hover { color: #fbbf24; border-color: rgba(245, 158, 11, 0.55); background: rgba(217, 119, 6, 0.12);
        transform: translateY(-2px); }
      .mu-chip:active { transform: scale(0.96); }

      #resultCount { font-family: var(--i-font-mono); font-size: 0.78rem; color: rgba(242, 240, 236, 0.55); margin-top: 12px; min-height: 1.2em; }
      #resultCount.mu-searching { color: var(--i-accent); }
      #resultCount.mu-searching::after { content: ''; animation: muDots 1.2s steps(4, end) infinite; }
      @keyframes muDots { 0% { content: ''; } 25% { content: '.'; } 50% { content: '..'; } 75% { content: '...'; } }

      /* ---- sections ---- */
      .mu-sec-head { display: flex; align-items: center; gap: 14px; }
      .mu-sec-head h2 { margin: 0; }
      .mu-sec-sub { color: rgba(242, 240, 236, 0.5); font-size: 0.9rem; margin: 6px 0 0; }
      .mu-eq { display: inline-flex; align-items: flex-end; gap: 3px; height: 18px; flex: none; }
      .mu-eq i { width: 3px; border-radius: 2px; background: linear-gradient(180deg, #fbbf24, #d97706); height: 30%; }
      .mu-eq-static i:nth-child(1) { animation: muBar 1s ease-in-out infinite; }
      .mu-eq-static i:nth-child(2) { animation: muBar 1s ease-in-out 0.18s infinite; }
      .mu-eq-static i:nth-child(3) { animation: muBar 1s ease-in-out 0.36s infinite; }
      .mu-eq-static i:nth-child(4) { animation: muBar 1s ease-in-out 0.54s infinite; }
      @keyframes muBar { 0%, 100% { height: 26%; } 50% { height: 100%; } }

      /* ---- track cards ---- */
      .mu-grid { margin-top: 26px; grid-template-columns: repeat(auto-fill, minmax(196px, 1fr)); gap: 18px; }
      @media (max-width: 640px) { .mu-grid { grid-template-columns: repeat(2, 1fr); gap: 14px; } }
      #results .card { background: rgba(255, 255, 255, 0.035); border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 18px; padding: 12px; overflow: hidden; animation: muCardIn 0.5s cubic-bezier(0.2, 0.8, 0.2, 1) both;
        transition: transform 0.3s var(--i-ease), border-color 0.3s var(--i-ease), box-shadow 0.3s var(--i-ease), background 0.3s var(--i-ease); }
      @keyframes muCardIn { from { opacity: 0; transform: translateY(26px) scale(0.97); } to { opacity: 1; transform: none; } }
      #results .card:hover { transform: translateY(-6px); border-color: rgba(245, 158, 11, 0.45);
        background: rgba(255, 255, 255, 0.05); box-shadow: 0 18px 44px rgba(0, 0, 0, 0.42), 0 0 0 1px rgba(217, 119, 6, 0.12); }
      #results .card-title { color: #f2f0ec; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      #results .card-meta { color: rgba(242, 240, 236, 0.5); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .mu-art { position: relative; border-radius: 12px; overflow: hidden; aspect-ratio: 1 / 1;
        cursor: pointer; background: #17171b; }
      .mu-art-img, .mu-art-fallback { width: 100%; height: 100%; object-fit: cover; display: block;
        transition: transform 0.55s cubic-bezier(0.2, 0.8, 0.2, 1); }
      .mu-art-fallback { display: grid; place-items: center; font-family: var(--i-font-display);
        font-weight: 600; font-size: 2rem; letter-spacing: 0.12em; color: rgba(242, 240, 236, 0.35);
        background: linear-gradient(135deg, #1b1b21, #232329); }
      .mu-art:hover .mu-art-img, .mu-art:hover .mu-art-fallback { transform: scale(1.07); }
      .mu-art-shade { position: absolute; inset: 0; opacity: 0; transition: opacity 0.3s var(--i-ease);
        background: linear-gradient(180deg, transparent 40%, rgba(10, 10, 12, 0.72)); }
      .mu-art:hover .mu-art-shade { opacity: 1; }
      .mu-art-play { position: absolute; right: 10px; bottom: 10px; width: 44px; height: 44px; border-radius: 50%;
        display: grid; place-items: center; color: #14100b;
        background: linear-gradient(135deg, #fbbf24, #f59e0b); box-shadow: 0 8px 26px rgba(217, 119, 6, 0.55);
        opacity: 0; transform: translateY(12px) scale(0.85); transition: all 0.3s cubic-bezier(0.2, 0.8, 0.2, 1); }
      .mu-art:hover .mu-art-play { opacity: 1; transform: none; }
      .mu-art-play:hover { transform: scale(1.1) !important; }
      .mu-eq-card { position: absolute; left: 10px; bottom: 10px; height: 20px; padding: 0 7px;
        border-radius: 999px; background: rgba(10, 10, 12, 0.62); -webkit-backdrop-filter: blur(6px); backdrop-filter: blur(6px);
        align-items: center; display: none; }
      .mu-eq-card i { width: 3px; height: 40%; border-radius: 2px; background: linear-gradient(180deg, #fbbf24, #d97706); }
      .card.playing .mu-eq-card { display: inline-flex; }
      .card.playing .mu-art-play { display: none; }
      .card.playing .mu-eq-card i { animation: muBar 0.9s ease-in-out infinite; }
      .card.playing .mu-eq-card i:nth-child(2) { animation-delay: 0.15s; }
      .card.playing .mu-eq-card i:nth-child(3) { animation-delay: 0.3s; }
      .card.playing .mu-eq-card i:nth-child(4) { animation-delay: 0.45s; }
      #results .card.playing { border-color: var(--i-accent);
        box-shadow: 0 0 0 1px var(--i-accent), 0 14px 40px rgba(217, 119, 6, 0.22);
        animation: none; opacity: 1; transform: none; }
      #results .card.playing .card-title { color: #fbbf24; }
      .mu-card-foot { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; margin: 10px 0 12px; min-height: 22px; }
      .chip { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.12); color: rgba(242, 240, 236, 0.6); }
      .chip-provider { font-family: var(--i-font-mono); font-size: 0.62rem; letter-spacing: 0.08em;
        border-color: rgba(245, 158, 11, 0.35) !important; color: #fbbf24 !important; background: rgba(217, 119, 6, 0.08); }

      /* ---- skeleton cards ---- */
      .sk-card { border-radius: 18px; border: 1px solid rgba(255, 255, 255, 0.06);
        background: rgba(255, 255, 255, 0.03); padding: 12px; animation: muCardIn 0.5s cubic-bezier(0.2, 0.8, 0.2, 1) both; }
      .sk-art { width: 100%; aspect-ratio: 1 / 1; border-radius: 12px; margin-bottom: 12px; }
      .sk-line { height: 12px; border-radius: 6px; margin-top: 8px; }
      .sk-w60 { width: 60%; }

      /* ---- docked glass player ---- */
      .mu-dock { height: 0; }
      #player { position: fixed; left: 0; right: 0; bottom: 0; z-index: 90; border: none;
        border-top: 1px solid rgba(255, 255, 255, 0.09); border-radius: 0;
        background: rgba(18, 18, 22, 0.82); -webkit-backdrop-filter: blur(20px) saturate(1.4); backdrop-filter: blur(20px) saturate(1.4);
        box-shadow: 0 -14px 48px rgba(0, 0, 0, 0.5); padding: 14px max(20px, calc((100vw - 1160px) / 2)) 16px;
        animation: muDockIn 0.5s cubic-bezier(0.2, 0.8, 0.2, 1); }
      @keyframes muDockIn { from { transform: translateY(110%); } to { transform: none; } }
      .mu-has-player .wrap { padding-bottom: 190px; }
      .player-thumb { width: 58px; max-width: none; aspect-ratio: 1 / 1; border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.12); background: #1b1b21; }
      .mu-dock-title { font-family: var(--i-font-display); font-size: 1.02rem; font-weight: 600; color: #f2f0ec; }
      #player .muted { color: rgba(242, 240, 236, 0.5); }
      #player .label { color: rgba(242, 240, 236, 0.4); }
      .player-controls { margin-top: 12px; gap: 14px; flex-wrap: wrap; }
      .player-btn { width: 42px; height: 42px; border-radius: 50%; color: #f2f0ec;
        background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.12);
        transition: all var(--i-dur-fast) var(--i-ease); }
      .player-btn:hover { background: rgba(217, 119, 6, 0.22); border-color: rgba(245, 158, 11, 0.6); transform: scale(1.07); }
      .player-btn:active { transform: scale(0.93); }
      .mu-play-main { width: 52px; height: 52px; background: linear-gradient(135deg, #fbbf24, #f59e0b);
        border: none; color: #14100b; box-shadow: 0 8px 26px rgba(217, 119, 6, 0.45); }
      .mu-play-main:hover { background: linear-gradient(135deg, #fcd34d, #fbbf24); transform: scale(1.08); }
      .player-track { background: rgba(255, 255, 255, 0.1); height: 5px; border-radius: 3px;
        transition: height 0.15s var(--i-ease); overflow: visible; }
      .player-track:hover { height: 8px; }
      .player-fill { background: linear-gradient(90deg, #f59e0b, #fb7185); border-radius: 3px;
        box-shadow: 0 0 14px rgba(245, 158, 11, 0.55); transition: width 0.2s linear; position: relative; }
      .player-fill::after { content: ''; position: absolute; right: -6px; top: 50%; width: 12px; height: 12px;
        border-radius: 50%; background: #fbbf24; transform: translateY(-50%) scale(0);
        transition: transform 0.2s var(--i-ease); box-shadow: 0 0 10px rgba(251, 191, 36, 0.8); }
      .player-track:hover .player-fill::after { transform: translateY(-50%) scale(1); }
      .player-time { color: rgba(242, 240, 236, 0.55); }
      .status { color: rgba(242, 240, 236, 0.7); }
      .mu-dock-close { width: 34px; height: 34px; border-radius: 50%; font-size: 1rem; background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.12); color: rgba(242, 240, 236, 0.6); cursor: pointer; transition: all var(--i-dur-fast) var(--i-ease); }
      .mu-dock-close:hover { color: #fff; border-color: rgba(251, 113, 133, 0.6); background: rgba(251, 113, 133, 0.14); transform: rotate(90deg); }
      .mu-dock-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
      .mu-dock-side { display: flex; align-items: center; gap: 12px; }

      /* ---- suggest / skeleton / empty / toast / arch, dark ---- */
      .suggest-list { background: rgba(20, 20, 25, 0.96); border: 1px solid rgba(255, 255, 255, 0.1);
        -webkit-backdrop-filter: blur(16px); backdrop-filter: blur(16px);
        box-shadow: 0 18px 50px rgba(0, 0, 0, 0.55); border-radius: 12px; overflow: hidden; }
      .suggest-item { color: rgba(242, 240, 236, 0.75); transition: background var(--i-dur-fast) var(--i-ease), padding-left var(--i-dur-fast) var(--i-ease); }
      .suggest-item:hover, .suggest-item.active { background: rgba(217, 119, 6, 0.14); color: #fbbf24; padding-left: 16px; }
      .skeleton { background: linear-gradient(90deg, #17171c 25%, #232329 50%, #17171c 75%) !important;
        background-size: 200% 100% !important; border-radius: 8px; }
      .empty { color: rgba(242, 240, 236, 0.55); }
      .empty svg { animation: muSwing 3s ease-in-out infinite; transform-origin: top center; }
      @keyframes muSwing { 0%, 100% { transform: rotate(-4deg); } 50% { transform: rotate(4deg); } }
      .empty .btn { margin-top: 14px; }
      .toast { background: rgba(20, 20, 25, 0.95); color: #f2f0ec; border: 1px solid rgba(255, 255, 255, 0.12);
        -webkit-backdrop-filter: blur(12px); backdrop-filter: blur(12px); }
      .mu-arch > div { border-radius: 20px !important; border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 24px 70px rgba(0, 0, 0, 0.45); }
      h2 { color: #f2f0ec; }
    </style>

    <section class="hero section mu-hero">
      <div class="mu-aurora" aria-hidden="true"><i></i><i></i><i></i></div>
      <div class="label">IOTA / OPEN AUDIO INFRASTRUCTURE</div>
      <h1 class="mu-title">
        <span class="mu-line">Search.</span>
        <span class="mu-line grad">Stream.</span>
        <span class="mu-line">Store.</span>
      </h1>
      <p class="lead">
        <strong>Any song, live.</strong> Type above and Iota finds it across providers in
        realtime — then streams it straight in your browser with HTTP Range / 206.
        A public audio API with indexed catalog search and IotaDB underneath.
      </p>
      <div class="console">
        <div class="label">LIVE SEARCH &middot; ANY SONG</div>
        <div class="console-border">
          <span class="console-prompt">/&gt;</span>
          <div class="console-wrap">
            <input id="q" type="search" placeholder="Search any song, artist or album — results appear as you type" aria-label="Search songs" autocomplete="off" role="combobox" aria-expanded="false" aria-autocomplete="list" aria-controls="suggest">
            <div class="suggest-list" id="suggest" role="listbox" aria-label="Search suggestions"></div>
          </div>
          <span class="mu-kbd" aria-hidden="true">/</span>
          <button class="btn btn-primary" id="go" type="button">Search</button>
          <button class="btn" id="rand" type="button">Random</button>
          <button class="btn" id="getkey" type="button">Get API Key</button>
        </div>
        <div class="result-count" id="resultCount" role="status" aria-live="polite"></div>
        <div class="mu-quick" aria-label="Quick searches">
          <button class="mu-chip" type="button" data-q="Lo-fi beats">lo-fi beats</button>
          <button class="mu-chip" type="button" data-q="Adele">adele</button>
          <button class="mu-chip" type="button" data-q="Queen">queen</button>
          <button class="mu-chip" type="button" data-q="K-pop">k-pop</button>
          <button class="mu-chip" type="button" data-q="Top hits 2026">top hits 2026</button>
        </div>
      </div>
    </section>

    <!-- Infrastructure diagram -->
    <section class="section mu-arch">
      {INFRA_DIAGRAM_PLACEHOLDER}
    </section>

    <!-- Audio player (docked) -->
    <section class="section mu-dock">
      <div id="player" class="panel-dark player" style="display:none;" aria-label="Audio player">
        <div style="display:flex;gap:16px;align-items:flex-start;flex-wrap:wrap;">
          <img id="pthumb" class="player-thumb" alt="Album art" style="display:none;">
          <div style="flex:1;min-width:240px;">
            <div class="mu-dock-head">
              <div>
                <div class="label">NOW PLAYING</div>
                <div id="ptitle" class="mu-dock-title">No selection</div>
                <div class="mono muted" id="pmeta" style="font-size:0.75rem;"></div>
              </div>
              <div class="mu-dock-side">
                <span class="status status-green" id="pstatus" style="margin:0">
                  <span class="status-dot"></span><span id="pstatustext">READY</span>
                </span>
                <button class="mu-dock-close" id="pclose" type="button" aria-label="Hide player" title="Hide player">&times;</button>
              </div>
            </div>
            <div class="player-controls">
              <button class="player-btn" id="pprev" type="button" aria-label="Previous track">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M6 6h2v12H6zm3.5 6l8.5 6V6z"/></svg>
              </button>
              <button class="player-btn mu-play-main" id="pplay" type="button" aria-label="Play or pause">
                <svg id="pplayicon" width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
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
      <div class="mu-sec-head">
        <h2>Trending</h2>
        <span class="mu-eq mu-eq-static" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
      </div>
      <p class="mu-sec-sub">Hot in the catalog right now — or search any song above.</p>
      <div id="results" class="grid mu-grid"></div>
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

      function initialsOf(title) {
        var parts = String(title || '?').trim().split(/\\s+/).slice(0, 2);
        return parts.map(function (w) { return w.charAt(0); }).join('').toUpperCase() || 'IO';
      }

      function norm(s, live) {
        var vid = live ? (s.media_id || '') : (s.video_id || '');
        var thumb = s.thumbnail || s.thumbnail_url || null;
        if (thumb && thumb.indexOf('default.svg') !== -1) thumb = null;
        return {
          copy_id: vid,
          title: s.title || 'Unknown title',
          artist: s.artist || 'Unknown',
          duration: s.duration_seconds || 0,
          thumb: thumb,
          url: live ? (s.play_url || ('/api/live-play/' + vid)) : (s.stream_url || ('/api/file/' + vid)),
          tags: s.tags || [],
          provider: live ? (s.provider || 'live') : 'catalog'
        };
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
        el.style.animationDelay = String((idx % 12) * 45) + 'ms';
        var tags = (s.tags || []).slice(0, 3).map(function (t) {
          return '<span class="chip">' + escapeHtml(t) + '</span>';
        }).join('');
        var providerLabel = s.provider === 'catalog'
          ? 'CATALOG'
          : String(s.provider || 'live').toUpperCase();
        var art = s.thumb
          ? '<img class="mu-art-img" loading="lazy" src="' + escapeHtml(s.thumb) + '" alt="' + escapeHtml(s.title) + ' album art">'
          : '<div class="mu-art-fallback" aria-hidden="true">' + escapeHtml(initialsOf(s.title)) + '</div>';
        el.innerHTML =
          '<div class="mu-art" role="button" tabindex="0" aria-label="Play ' + escapeHtml(s.title) + '">' +
            art +
            '<div class="mu-art-shade"></div>' +
            '<span class="mu-eq-card" aria-hidden="true"><i></i><i></i><i></i><i></i></span>' +
            '<span class="mu-art-play" aria-hidden="true">' +
              '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" style="margin-left:2px">' + ICON_PLAY + '</svg>' +
            '</span>' +
          '</div>' +
          '<div class="card-title">' + escapeHtml(s.title) + '</div>' +
          '<div class="card-meta">' + escapeHtml(s.artist) + '  &middot;  ' + fmtDuration(s.duration) + '</div>' +
          '<div class="mu-card-foot">' + tags +
            '<span class="chip chip-provider">' + escapeHtml(providerLabel) + '</span>' +
            '<button class="chip copy-btn" type="button" style="cursor:pointer" data-id="' + escapeHtml(s.copy_id) + '" aria-label="Copy track ID">ID</button>' +
          '</div>';
        var artEl = el.querySelector('.mu-art');
        artEl.onclick = function () { playAt(idx); };
        artEl.onkeydown = function (e) {
          if (e.key === 'Enter' || e.key === ' ') { playAt(idx); e.preventDefault(); }
        };
        el.querySelector('.copy-btn').onclick = function () {
          if (window.copyToClipboard) window.copyToClipboard(s.copy_id);
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
        pmeta.textContent = s.artist + '  ·  ' + s.copy_id;
        pthumb.style.display = s.thumb ? 'block' : 'none';
        if (s.thumb) pthumb.src = s.thumb;
        audioEl.src = s.url;
        audioEl.volume = pvol.value;
        player.style.display = 'block';
        audioEl.play().then(function () {
          setStatus('PLAYING', 'green');
        }).catch(function () {
          setStatus('ERROR', 'red');
          if (window.showToast) showToast('Playback failed - press PLAY to retry', 'error');
        });
        setStatus('BUFFERING', 'amber');
        document.body.classList.add('mu-has-player');
        if ('mediaSession' in navigator) {
          try {
            navigator.mediaSession.metadata = new MediaMetadata({
              title: s.title || 'Unknown track',
              artist: s.artist || 'Iota',
              artwork: s.thumb ? [{src: s.thumb, sizes: '512x288', type: 'image/jpeg'}] : []
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
      pclose.onclick = function () {
        audioEl.pause();
        player.style.display = 'none';
        player.classList.remove('mu-open');
        document.body.classList.remove('mu-has-player');
      };

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

      function showSkeletons() {
        results.innerHTML = '';
        for (var i = 0; i < 6; i++) {
          var sk = document.createElement('div');
          sk.className = 'sk-card';
          sk.innerHTML =
            '<div class="skeleton sk-art"></div>' +
            '<div class="skeleton sk-line"></div>' +
            '<div class="skeleton sk-line sk-w60"></div>';
          results.appendChild(sk);
        }
      }

      function resetPlaying() {
        if (currentCard) {
          currentCard.classList.remove('playing');
          currentCard.removeAttribute('aria-current');
          currentCard = null;
        }
      }

      function emptyState(headline, note, withRetry, retryFn) {
        results.innerHTML = '<div class="empty">' +
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>' +
          '<h3>' + escapeHtml(headline) + '</h3><p>' + escapeHtml(note) + '</p>' +
          (withRetry ? '<button class="btn" id="retry" type="button">Retry</button>' : '') +
          '</div>';
        if (withRetry) {
          var rb = document.getElementById('retry');
          if (rb) rb.onclick = retryFn;
        }
      }

      function setSearching(on) {
        if (on) resultCount.classList.add('mu-searching');
        else resultCount.classList.remove('mu-searching');
      }

      function render(list, mode, elapsedMs) {
        queue = list;
        qIndex = -1;
        resetPlaying();
        setSearching(false);
        results.innerHTML = '';
        list.forEach(function (s, i) { results.appendChild(card(s, i)); });
        if (!list.length) {
          emptyState(
            mode === 'live' ? 'No tracks found' : 'No matches found',
            mode === 'live' ? 'Try a different song, artist or album.' : 'Try a different search term.',
            false, null
          );
          resultCount.textContent = '';
          return;
        }
        var label = mode === 'live' ? 'live results' : 'catalog results';
        resultCount.textContent = list.length + ' ' + label +
          (elapsedMs != null ? '  ·  ' + elapsedMs + 'ms' : '') +
          '  ·  provider-backed audio, Range / 206';
      }

      function fetchJSON(url) {
        return fetch(url).then(function (r) {
          if (!r.ok) throw new Error('HTTP ' + r.status);
          return r.json();
        });
      }

      function runCatalog(url, fallbackLabel) {
        var seq = ++runSeq;
        showSkeletons();
        setSearching(true);
        resultCount.textContent = fallbackLabel || 'Loading...';
        fetchJSON(url).then(function (data) {
          if (seq !== runSeq) return;
          render((data.results || []).map(function (s) { return norm(s, false); }), 'catalog', null);
        }).catch(function () {
          if (seq !== runSeq) return;
          emptyState('Error', 'Failed to fetch results.', true, function () { runCatalog(url, fallbackLabel); });
          setSearching(false);
          resultCount.textContent = '';
          if (window.showToast) showToast('Failed to load results', 'error');
        });
      }

      function liveSearch(q) {
        q = (q || '').trim();
        if (!q) { runCatalog('/api/trending?limit=12', 'Trending now'); return; }
        var seq = ++runSeq;
        showSkeletons();
        setSearching(true);
        resultCount.textContent = 'Searching any song: "' + q + '" ...';
        var liveUrl = '/api/live?q=' + encodeURIComponent(q) + '&limit=20';
        cachedFetchJSON(liveUrl)
          .then(function (out) {
            if (seq !== runSeq) return;
            render((out.data.results || []).map(function (s) { return norm(s, true); }), 'live', out.data.elapsed_ms);
          })
          .catch(function () {
            if (seq !== runSeq) return;
            resultCount.textContent = 'Live search unavailable - falling back to catalog';
            cachedFetchJSON('/api/search?q=' + encodeURIComponent(q) + '&limit=12')
              .then(function (out) {
                if (seq !== runSeq) return;
                render((out.data.results || []).map(function (s) { return norm(s, false); }), 'catalog', null);
              })
              .catch(function () {
                 if (seq !== runSeq) return;
                 emptyState('Search failed', 'Live search and catalog are both unavailable.', true, function () { liveSearch(q); });
                 setSearching(false);
                 resultCount.textContent = '';
               });
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
        liveSearch(qInput.value);
        return true;
      }

      var suggestTimer = null;
      var searchTimer = null;
      var searchCache = new Map();
      var CACHE_TTL = 300000;

      function cachedFetchJSON(url) {
        var hit = searchCache.get(url);
        var now = Date.now();
        if (hit && now - hit.at < CACHE_TTL) {
          return Promise.resolve({ data: hit.data, cached: true });
        }
        return fetchJSON(url).then(function (data) {
          searchCache.set(url, { data: data, at: now });
          if (searchCache.size > 50) {
            var oldest = searchCache.keys().next().value;
            searchCache.delete(oldest);
          }
          return { data: data, cached: false };
        });
      }

      qInput.addEventListener('input', function () {
        clearTimeout(suggestTimer);
        clearTimeout(searchTimer);
        var q = qInput.value.trim();
        if (q.length < 3) { closeSuggest(); return; }
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
                liveSearch(qInput.value);
              };
            });
            suggestBox.classList.add('open');
            qInput.setAttribute('aria-expanded', 'true');
          }).catch(function () {});
        }, 200);
        searchTimer = setTimeout(function () { liveSearch(q); }, 600);
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
          liveSearch(qInput.value || 'iota');
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

      document.getElementById('go').onclick = function () { liveSearch(qInput.value || 'iota'); };
      document.getElementById('rand').onclick = function () { runCatalog('/api/random?limit=12', 'Shuffling...'); };

      var muQuick = document.querySelector('.mu-quick');
      if (muQuick) {
        muQuick.addEventListener('click', function (e) {
          var chip = e.target.closest ? e.target.closest('[data-q]') : null;
          if (!chip) return;
          qInput.value = chip.getAttribute('data-q');
          closeSuggest();
          qInput.focus();
          liveSearch(qInput.value);
        });
      }

      runCatalog('/api/trending?limit=12', 'Trending now');
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
          <div class="card-meta">Provider audio (audio/mp4), Range / 206</div>
        </div>
      </div>
      <p class="section-note">The public catalog indexes real tracks. <code>/api/file/{video_id}</code> streams the actual provider audio (YouTube, <code>audio/mp4</code>) — no API key required, IP rate-limited. Only IDs present in the curated catalog resolve, so this is not an open proxy.</p>
    </section>

    <section class="section">
      <div class="label">LIVE</div>
      <h2>Live endpoints (no API key)</h2>
      <div class="grid">
        <div class="card">
          <div class="label">SEARCH</div>
          <div class="card-title">GET /api/live</div>
          <div class="card-meta">Query params: q, limit &middot; any song via providers</div>
        </div>
        <div class="card">
          <div class="label">PLAY</div>
          <div class="card-title">GET /api/live-play/{media_id}</div>
          <div class="card-meta">Audio for ids from /api/live, Range / 206</div>
        </div>
      </div>
      <p class="section-note"><code>/api/live</code> searches every provider, not just the catalog. Playback is session-scoped: only media ids your IP just received from <code>/api/live</code> can stream (15-minute allowlist), so this is not an open proxy. IP rate-limited like the rest of the public surface.</p>
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


def about_html() -> str:
    body = """
    <style>
      body { background: #0d0d10; color: #f2f0ec; }
      body::before { content: ''; position: fixed; inset: -10%; z-index: -1; pointer-events: none;
        background:
          radial-gradient(640px 420px at 85% -10%, rgba(217, 119, 6, 0.16), transparent 62%),
          radial-gradient(520px 400px at -10% 34%, rgba(251, 113, 133, 0.08), transparent 60%),
          radial-gradient(760px 520px at 55% 112%, rgba(217, 119, 6, 0.08), transparent 62%);
        animation: muDrift 16s ease-in-out infinite alternate; }
      @keyframes muDrift { from { transform: translateY(-10px) scale(1); } to { transform: translateY(12px) scale(1.04); } }

      .nav { background: rgba(13, 13, 16, 0.72); -webkit-backdrop-filter: blur(16px) saturate(1.4);
        backdrop-filter: blur(16px) saturate(1.4); border-bottom-color: rgba(255, 255, 255, 0.08); }
      .nav.scrolled { background: rgba(13, 13, 16, 0.86); }
      .nav-link { color: rgba(242, 240, 236, 0.55); }
      .nav-link:hover { color: #ffffff; }
      .brand-text { color: #f2f0ec; }
      .mu-menu-btn { background: rgba(217, 119, 6, 0.12); border-color: rgba(217, 119, 6, 0.45); }
      ::-webkit-scrollbar { width: 10px; height: 10px; }
      ::-webkit-scrollbar-track { background: transparent; }
      ::-webkit-scrollbar-thumb { background: #2a2a30; border-radius: 8px; border: 2px solid #0d0d10; }
      ::selection { background: rgba(217, 119, 6, 0.4); }

      .ab-hero { padding-top: 34px; }
      .ab-hero .label { color: rgba(242, 240, 236, 0.55); animation: muRise 0.6s var(--i-ease) both; }
      .ab-hero .label::after { content: '_'; color: var(--i-accent); animation: muBlink 1.1s steps(1) infinite; }
      .ab-hero h1 { font-family: var(--i-font-display); font-size: clamp(2.4rem, 6vw, 4.2rem); line-height: 1.04;
        letter-spacing: -0.02em; margin: 14px 0 0; color: #f2f0ec; animation: muRise 0.7s var(--i-ease) 0.08s both; }
      .ab-hero h1 em { font-style: normal;
        background: linear-gradient(92deg, #fbbf24, #f59e0b 55%, #fb7185); -webkit-background-clip: text;
        background-clip: text; -webkit-text-fill-color: transparent; }
      .ab-hero p.lead { color: rgba(242, 240, 236, 0.62); max-width: 620px; animation: muRise 0.7s var(--i-ease) 0.22s both; }
      .ab-run { display: inline-flex; align-items: center; gap: 10px; margin-top: 18px; padding: 8px 16px;
        border-radius: 999px; border: 1px solid rgba(255, 255, 255, 0.1); background: rgba(255, 255, 255, 0.04);
        font-family: var(--i-font-mono); font-size: 0.72rem; letter-spacing: 0.08em; color: rgba(242, 240, 236, 0.6);
        animation: muRise 0.7s var(--i-ease) 0.3s both; }
      .ab-dot { width: 8px; height: 8px; border-radius: 50%; background: #fbbf24; box-shadow: 0 0 0 0 rgba(251, 191, 36, 0.5); }
      .ab-dot.on { background: #34d399; animation: abPulse 2s ease-in-out infinite; }
      .ab-dot.warn { background: #fbbf24; }
      @keyframes abPulse { 0% { box-shadow: 0 0 0 0 rgba(52, 211, 153, 0.5); } 70% { box-shadow: 0 0 0 9px rgba(52, 211, 153, 0); } 100% { box-shadow: 0 0 0 0 rgba(52, 211, 153, 0); } }
      @keyframes muRise { from { opacity: 0; transform: translateY(26px); } to { opacity: 1; transform: none; } }
      @keyframes muBlink { 0%, 49% { opacity: 1; } 50%, 100% { opacity: 0; } }

      .ab-story { display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 26px; align-items: stretch; }
      @media (max-width: 800px) { .ab-story { grid-template-columns: 1fr; } }
      .ab-panel { background: rgba(255, 255, 255, 0.035); border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px; padding: 26px 28px; }
      .ab-panel h2 { font-family: var(--i-font-display); color: #f2f0ec; margin: 8px 0 12px; }
      .ab-panel p { color: rgba(242, 240, 236, 0.58); line-height: 1.75; margin: 0 0 12px; }
      .ab-panel p strong { color: rgba(242, 240, 236, 0.92); font-weight: 600; }
      .ab-panel .label { color: rgba(242, 240, 236, 0.4); }

      .ab-feats { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 16px; margin-top: 24px; }
      .ab-feat { background: rgba(255, 255, 255, 0.035); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 18px;
        padding: 22px; transition: all 0.3s var(--i-ease); }
      .ab-feat:hover { transform: translateY(-5px); border-color: rgba(245, 158, 11, 0.4);
        background: rgba(255, 255, 255, 0.05); box-shadow: 0 18px 44px rgba(0, 0, 0, 0.4); }
      .ab-feat-ico { width: 44px; height: 44px; border-radius: 14px; display: grid; place-items: center; color: #fbbf24;
        background: rgba(217, 119, 6, 0.1); border: 1px solid rgba(217, 119, 6, 0.28); margin-bottom: 14px; }
      .ab-feat h3 { font-family: var(--i-font-display); font-size: 1.02rem; color: #f2f0ec; margin: 0 0 8px; }
      .ab-feat p { font-size: 0.86rem; color: rgba(242, 240, 236, 0.55); line-height: 1.65; margin: 0; }

      .ab-flow { display: flex; align-items: stretch; gap: 0; flex-wrap: wrap; margin-top: 24px; }
      .ab-step { flex: 1 1 180px; background: rgba(255, 255, 255, 0.035); border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px; padding: 18px 20px; position: relative; transition: all 0.3s var(--i-ease); }
      .ab-step:hover { border-color: rgba(245, 158, 11, 0.4); background: rgba(217, 119, 6, 0.06); }
      .ab-step b { display: block; font-family: var(--i-font-mono); font-size: 0.66rem; letter-spacing: 0.16em;
        color: #fbbf24; margin-bottom: 6px; }
      .ab-step span { font-size: 0.82rem; color: rgba(242, 240, 236, 0.55); line-height: 1.55; }
      .ab-step + .ab-step { margin-left: 10px; }
      .ab-step + .ab-step::before { content: ''; position: absolute; left: -8px; top: 50%; width: 7px; height: 7px;
        border-top: 2px solid var(--i-accent); border-right: 2px solid var(--i-accent); transform: translateY(-50%) rotate(45deg); }

      .ab-stats { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 14px; margin-top: 24px; }
      .ab-stat { background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px;
        padding: 18px 20px; transition: border-color 0.3s var(--i-ease); }
      .ab-stat:hover { border-color: rgba(245, 158, 11, 0.4); }
      .ab-stat b { display: block; font-family: var(--i-font-display); font-size: 1.7rem; color: #fbbf24; }
      .ab-stat span { font-family: var(--i-font-mono); font-size: 0.62rem; letter-spacing: 0.16em; color: rgba(242, 240, 236, 0.45); }

      .ab-cta { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 26px; }
      .ab-btn { display: inline-flex; align-items: center; gap: 8px; padding: 12px 22px; border-radius: 14px;
        font-family: var(--i-font-mono); font-size: 0.78rem; letter-spacing: 0.1em; text-decoration: none;
        border: 1px solid rgba(255, 255, 255, 0.12); color: #f2f0ec; background: rgba(255, 255, 255, 0.04);
        transition: all 0.25s var(--i-ease); }
      .ab-btn:hover { transform: translateY(-2px); border-color: rgba(245, 158, 11, 0.55); }
      .ab-btn.primary { background: linear-gradient(135deg, #f59e0b, #d97706); border: none; color: #14100b;
        box-shadow: 0 8px 26px rgba(217, 119, 6, 0.4); font-weight: 600; }
      .ab-btn.primary:hover { background: linear-gradient(135deg, #fbbf24, #f59e0b); }
      .ab-foot { display: flex; gap: 18px; align-items: center; margin: 60px 0 10px; padding-top: 22px;
        border-top: 1px solid rgba(255, 255, 255, 0.07); font-family: var(--i-font-mono); font-size: 0.7rem;
        letter-spacing: 0.06em; color: rgba(242, 240, 236, 0.4); }
      .ab-foot a { color: rgba(242, 240, 236, 0.55); text-decoration: none; }
      .ab-foot a:hover { color: #fbbf24; }
      .section { padding: 34px 0; }
    </style>

    <section class="section ab-hero">
      <div class="label">ABOUT IOTA</div>
      <h1>The audio computer behind<br>every <em>Iota</em> app.</h1>
      <p class="lead">
        One small service that searches any song on the internet, streams it with fast-seek
        precision, and stores your own catalog &mdash; with no accounts for listeners, ever.
      </p>
      <span class="ab-run">
        <span class="ab-dot" id="abDot"></span>
        <span id="abStatus">CHECKING SERVICE...</span>
      </span>
    </section>

    <section class="section">
      <div class="ab-story">
        <div class="ab-panel">
          <div class="label">WHY IOTA EXISTS</div>
          <h2>Play anything. Own the stack.</h2>
          <p>
            Most music apps are walled gardens: someone else's catalog, someone else's rules,
            someone else's downtime. <strong>Iota flips it</strong> &mdash; you run one process,
            and it becomes a search engine, a streaming server, and a database for your music.
          </p>
          <p>
            When a request lands, Iota fans out to public catalogue providers
            (<strong>YouTube, Datazalidy, Apple&nbsp;Music, Spotify&nbsp;search metadata, MusicBrainz</strong>),
            resolves the best playable URI for your setup, and serves the audio itself &mdash;
            byte-range by byte-range, so dragging the seek bar actually feels instant.
          </p>
          <p>
            It grew out of the <strong>Iota music player</strong> project: the player needed a
            reliable audio brain, and the brain grew its own web-grade API. Everything you
            hear on the home page is powered by the exact same endpoints documented in the API reference.
          </p>
        </div>
        <div class="ab-panel">
          <div class="label">KEEP IT SMALL</div>
          <h2>Designed like a baby repo.</h2>
          <p>
            A single FastAPI process. SQLite or Postgres behind one setting. An embedded
            document database (<strong>iotaDB</strong>) for app data &mdash; inserts, queries,
            aggregation, all over plain HTTP.
          </p>
          <p>
            No message queues. No kubernetes manifests. No accounts for listeners.
            Anonymous sandbox keys are minted with a single POST, and rate limiting is
            built into the filesystem- and memory-friendly layers of the core.
          </p>
          <div class="ab-cta">
            <a class="ab-btn primary" href="/">&#9654; OPEN THE PLAYER</a>
            <a class="ab-btn" href="/docs">READ THE DOCS</a>
          </div>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="label">CAPABILITIES</div>
      <h2>What's inside the box</h2>
      <div class="ab-feats">
        <div class="ab-feat">
          <div class="ab-feat-ico"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="11" cy="11" r="6.5"/><path d="m20 20-4.2-4.2"/></svg></div>
          <h3>Live search, any song</h3>
          <p>Debounced free-text search across five providers as you type &mdash; results in seconds, cached client-side.</p>
        </div>
        <div class="ab-feat">
          <div class="ab-feat-ico"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 4v16M6 9l6-5 6 5M6 15l6 5 6-5"/></svg></div>
          <h3>Byte-range streaming</h3>
          <p>HTTP 206 partial responses mean real seeking: scrub to 3:41 and audio resumes from there, not from zero.</p>
        </div>
        <div class="ab-feat">
          <div class="ab-feat-ico"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="10" width="16" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg></div>
          <h3>Sandbox keys</h3>
          <p>Anonymous API keys in one POST call &mdash; start building before you even sign up. Because there is no signup.</p>
        </div>
        <div class="ab-feat">
          <div class="ab-feat-ico"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="6" rx="7" ry="3"/><path d="M5 6v12c0 1.7 3.1 3 7 3s7-1.3 7-3V6"/><path d="M5 12c0 1.7 3.1 3 7 3s7-1.3 7-3"/></svg></div>
          <h3>iotaDB inside</h3>
          <p>A tiny document database with insert / find / update / aggregate &mdash; the database your project data lives in, exposed over REST.</p>
        </div>
        <div class="ab-feat">
          <div class="ab-feat-ico"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="6" cy="12" r="2.4"/><circle cx="18" cy="6" r="2.4"/><circle cx="18" cy="18" r="2.4"/><path d="M8.2 11 15.8 7M8.2 13l7.6 4"/></svg></div>
          <h3>Session-aware playback</h3>
          <p>Play links are scoped to your session window &mdash; they work for you right now, they are not an open proxy.</p>
        </div>
        <div class="ab-feat">
          <div class="ab-feat-ico"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12h4l2.5-6 4 12 2.5-6h5"/></svg></div>
          <h3>Observability first</h3>
          <p>Health checks, live stats and per-provider cache telemetry &mdash; a self-respecting API you can actually debug.</p>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="label">THE PIPELINE</div>
      <h2>From keystroke to sound</h2>
      <div class="ab-flow">
        <div class="ab-step"><b>01 &middot; SEARCH</b><span>"/api/live" fans a typed query out to five catalogue providers in parallel.</span></div>
        <div class="ab-step"><b>02 &middot; RESOLVE</b><span>Playback picks the best direct audio URI for the user's runtime, no fallback soup.</span></div>
        <div class="ab-step"><b>03 &middot; STREAM</b><span>"/api/live-play/{id}" serves the bytes with Range/206 and proxy headers handled for you.</span></div>
        <div class="ab-step"><b>04 &middot; PLAY</b><span>Any &lt;audio&gt; element, any client, any language &mdash; it's just HTTP.</span></div>
      </div>
    </section>

    <section class="section">
      <div class="label">BY THE NUMBERS</div>
      <h2>Small, sharp, tested</h2>
      <div class="ab-stats">
        <div class="ab-stat"><b>5</b><span>SEARCH PROVIDERS</span></div>
        <div class="ab-stat"><b>1</b><span>PROCESS DEPLOYMENT</span></div>
        <div class="ab-stat"><b>0</b><span>ACCOUNTS REQUIRED</span></div>
        <div class="ab-stat"><b>270</b><span>AUTOMATED TESTS</span></div>
        <div class="ab-stat"><b>v2.0</b><span>API GENERATION</span></div>
      </div>
      <p style="color: rgba(242, 240, 236, 0.5); font-size: 0.9rem; margin: 14px 0 0">Numbers are from this very deployment &mdash; the same build you're listening through right now.</p>
    </section>

    <section class="section">
      <div class="label">STACK</div>
      <h2>Built with</h2>
      <div class="ab-feats">
        <div class="ab-feat">
          <h3>FastAPI + Uvicorn</h3>
          <p>Async Python engine; typed routes, OpenAPI schema generated automatically.</p>
        </div>
        <div class="ab-feat">
          <h3>SQLite &middot; Postgres</h3>
          <p>One DATABASE_URL swap moves you from laptop to server with zero code changes.</p>
        </div>
        <div class="ab-feat">
          <h3>yt-dlp &middot; provider adapters</h3>
          <p>Resolution stays pluggable per provider &mdash; timeouts and retries are handled centrally.</p>
        </div>
        <div class="ab-feat">
          <h3>Vanilla web UI</h3>
          <p>No frameworks in this player &mdash; hand-rolled CSS animations, zero build step, instant first paint on 3G.</p>
        </div>
      </div>
    </section>

    <div class="ab-foot">
      <span>IOTA &middot; a baby-repo audio computer</span>
      <span style="flex:1"></span>
      <a href="/privacy">PRIVACY</a>
      <a href="/terms">TERMS</a>
      <a href="/docs">DOCS</a>
      <a href="/">PLAYER</a>
    </div>

    <script>
      (function () {
        var dot = document.getElementById('abDot');
        var label = document.getElementById('abStatus');
        fetch('/health').then(function (r) { return r.json(); }).then(function (d) {
          var ok = d && d.checks && d.checks.postgres === 'ok';
          dot.classList.add(ok ? 'on' : 'warn');
          label.textContent = ok ? 'SERVICE ONLINE' : 'SERVICE DEGRADED';
        }).catch(function () {
          dot.classList.add('warn');
          label.textContent = 'SERVICE UNREACHABLE';
        });
      })();
    </script>
    """
    return _page("About Iota API", body)


def stats_page_html() -> str:
    body = """
    <style>
      body::before { content: ''; position: fixed; inset: -10%; z-index: -1; pointer-events: none;
        background:
          radial-gradient(640px 420px at 85% -10%, rgba(217, 119, 6, 0.15), transparent 62%),
          radial-gradient(520px 400px at -10% 34%, rgba(251, 113, 133, 0.08), transparent 60%),
          radial-gradient(760px 520px at 55% 112%, rgba(217, 119, 6, 0.08), transparent 62%);
        animation: muDrift 16s ease-in-out infinite alternate; }
      @keyframes muDrift { from { transform: translateY(-10px) scale(1); } to { transform: translateY(12px) scale(1.04); } }
      @keyframes muRise { from { opacity: 0; transform: translateY(26px); } to { opacity: 1; transform: none; } }
      @keyframes stFlash { 0% { color: #fbbf24; transform: scale(1.07); } 100% { transform: scale(1); } }
      @keyframes stEvIn { from { opacity: 0; transform: translateX(-10px); } to { opacity: 1; transform: none; } }
      @keyframes stCd { from { stroke-dashoffset: 0; } to { stroke-dashoffset: 138.2; } }

      .st-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; flex-wrap: wrap;
        padding-top: 30px; animation: muRise 0.6s var(--i-ease) both; }
      .st-head h1 { font-family: var(--i-font-display); font-size: clamp(1.9rem, 4.6vw, 3rem); margin: 10px 0 0;
        color: #f2f0ec; letter-spacing: -0.02em; }
      .st-head h1 em { font-style: normal;
        background: linear-gradient(92deg, #fbbf24, #f59e0b 55%, #fb7185); -webkit-background-clip: text;
        background-clip: text; -webkit-text-fill-color: transparent; }
      .st-livebox { display: flex; align-items: center; gap: 16px; }
      .st-status { display: inline-flex; align-items: center; gap: 9px; padding: 9px 18px; border-radius: 999px;
        border: 1px solid rgba(255, 255, 255, 0.12); background: rgba(255, 255, 255, 0.04);
        font-family: var(--i-font-mono); font-size: 0.74rem; letter-spacing: 0.1em; color: #f2f0ec; }
      .st-dot { width: 9px; height: 9px; border-radius: 50%; background: #6b7280; }
      .st-dot.on { background: #34d399; box-shadow: 0 0 0 0 rgba(52, 211, 153, 0.5); animation: abPulse 2s ease-in-out infinite; }
      .st-dot.warn { background: #fbbf24; }
      .st-dot.bad { background: #fb7185; }
      @keyframes abPulse { 0% { box-shadow: 0 0 0 0 rgba(52, 211, 153, 0.5); } 70% { box-shadow: 0 0 0 9px rgba(52, 211, 153, 0); } 100% { box-shadow: 0 0 0 0 rgba(52, 211, 153, 0); } }
      .st-countdown { position: relative; width: 72px; height: 72px; flex: none; }
      .st-countdown svg { width: 72px; height: 72px; transform: rotate(-90deg); }
      .st-cd-num { position: absolute; inset: 0; display: grid; place-items: center; text-align: center;
        font-family: var(--i-font-mono); font-size: 0.66rem; letter-spacing: 0.06em; color: rgba(242, 240, 236, 0.6); line-height: 1.2; }
      .st-cd-num b { display: block; color: #fbbf24; font-size: 1rem; }

      .st-tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 14px; margin-top: 26px; }
      .st-tile { background: rgba(255, 255, 255, 0.035); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 18px;
        padding: 18px 20px; transition: all 0.3s var(--i-ease); animation: muRise 0.6s var(--i-ease) both; }
      .st-tile:hover { border-color: rgba(245, 158, 11, 0.4); transform: translateY(-4px); background: rgba(255, 255, 255, 0.05); }
      .st-tile .k { font-family: var(--i-font-mono); font-size: 0.6rem; letter-spacing: 0.18em; color: rgba(242, 240, 236, 0.4); }
      .st-tile .v { font-family: var(--i-font-display); font-size: 1.8rem; color: #f2f0ec; margin-top: 6px; display: inline-block;
        font-variant-numeric: tabular-nums; }
      .st-tile .v.skel { color: transparent !important;
        background: linear-gradient(90deg, #1a1a20 25%, #26262d 50%, #1a1a20 75%);
        background-size: 200% 100%; animation: skeletonLoading 1.5s infinite; border-radius: 8px; }
      @keyframes skeletonLoading { 0% { background-position: -200% 0; } 100% { background-position: 200% 0; } }
      .st-spark { width: 100%; height: 36px; margin-top: 8px; display: block; overflow: visible; }
      .st-spark .line { fill: none; stroke: #fbbf24; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
      .st-spark .area { fill: rgba(217, 119, 6, 0.14); stroke: none; }
      .st-tile .v.flash { animation: stFlash 0.55s ease; }
      .st-tile .s { font-size: 0.68rem; color: rgba(242, 240, 236, 0.45); margin-top: 3px; min-height: 1em; }
      .st-tile.hot .v { color: #fbbf24; }

      .st-grid2 { display: grid; grid-template-columns: 1.25fr 0.75fr; gap: 16px; margin-top: 16px; }
      @media (max-width: 900px) { .st-grid2 { grid-template-columns: 1fr; } }
      .st-panel { background: rgba(255, 255, 255, 0.035); border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px; padding: 22px 24px; }
      .st-sec-head { display: flex; align-items: center; gap: 12px; }
      .st-sec-head h2 { font-family: var(--i-font-display); font-size: 1.05rem; color: #f2f0ec; margin: 0; }
      .st-sec-head .hint { font-size: 0.72rem; color: rgba(242, 240, 236, 0.4); margin-left: auto; text-align: right; }

      .st-prow { display: grid; grid-template-columns: 10px 110px 1fr 46px 74px; align-items: center; gap: 10px;
        padding: 11px 4px; border-bottom: 1px solid rgba(255, 255, 255, 0.05); font-size: 0.8rem; }
      .st-prow:last-child { border-bottom: none; }
      .st-pdot { width: 9px; height: 9px; border-radius: 50%; background: #3a3a42; }
      .st-pdot.on { background: #34d399; }
      .st-pdot.warn { background: #fbbf24; }
      .st-pname { color: #f2f0ec; font-family: var(--i-font-mono); font-size: 0.74rem; white-space: nowrap;
        overflow: hidden; text-overflow: ellipsis; }
      .st-pbar, .st-tbar { height: 6px; border-radius: 4px; background: rgba(255, 255, 255, 0.07); overflow: hidden; }
      .st-pbar i, .st-tbar i { display: block; height: 100%; border-radius: 4px; width: 0;
        background: linear-gradient(90deg, #f59e0b, #fbbf24); transition: width 0.6s var(--i-ease); }
      .st-pnum { font-family: var(--i-font-mono); font-size: 0.72rem; color: #fbbf24; text-align: right; }
      .st-plat { font-family: var(--i-font-mono); font-size: 0.66rem; color: rgba(242, 240, 236, 0.45); text-align: right; }

      .st-trow { display: grid; grid-template-columns: 34px 1fr 64px 90px 44px; align-items: center; gap: 10px;
        padding: 9px 4px; border-bottom: 1px solid rgba(255, 255, 255, 0.05); font-size: 0.82rem; }
      .st-trow:last-child { border-bottom: none; }
      .st-rank { font-family: var(--i-font-mono); font-size: 0.72rem; color: rgba(242, 240, 236, 0.35); }
      .st-title { color: #f2f0ec; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .st-chip { font-family: var(--i-font-mono); font-size: 0.62rem; color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3);
        background: rgba(217, 119, 6, 0.08); border-radius: 999px; padding: 3px 8px; text-align: center; }
      .st-tnum { font-family: var(--i-font-mono); font-size: 0.72rem; color: #fbbf24; text-align: right; }

      .st-qq { display: flex; flex-wrap: wrap; gap: 8px; }
      .st-qchip { font-family: var(--i-font-mono); font-size: 0.74rem; color: rgba(242, 240, 236, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.12); background: rgba(255, 255, 255, 0.045); border-radius: 999px; padding: 7px 13px; }
      .st-qchip b { color: #fbbf24; margin-left: 6px; }

      .st-events { max-height: 300px; overflow-y: auto; border-radius: 14px; background: rgba(10, 10, 13, 0.55);
        border: 1px solid rgba(255, 255, 255, 0.07); padding: 6px 0; font-family: var(--i-font-mono); font-size: 0.74rem; }
      .st-ev { display: flex; align-items: baseline; gap: 10px; padding: 6px 14px; color: rgba(242, 240, 236, 0.55); }
      .st-ev.new { animation: stEvIn 0.45s var(--i-ease); }
      .st-ev-t { color: rgba(242, 240, 236, 0.3); flex: none; }
      .st-ev-k { flex: none; width: 78px; font-size: 0.62rem; letter-spacing: 0.08em; }
      .st-ev-l { flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: rgba(242, 240, 236, 0.8); }
      .st-ev-search .st-ev-k { color: #fbbf24; }
      .st-ev-stream .st-ev-k { color: #34d399; }
      .st-ev-download .st-ev-k { color: #60a5fa; }
      .st-ev-error .st-ev-k { color: #fb7185; }

      .st-sys { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; }
      .st-sysrow { background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 14px; padding: 13px 16px; }
      .st-sysrow .k { font-family: var(--i-font-mono); font-size: 0.58rem; letter-spacing: 0.16em; color: rgba(242, 240, 236, 0.4); }
      .st-sysrow .v { font-family: var(--i-font-mono); font-size: 0.84rem; color: #f2f0ec; margin-top: 4px; }
      .st-sysrow .v.ok { color: #34d399; }
      .st-sysrow .v.warn { color: #fbbf24; }
      .st-section { padding: 30px 0 10px; }
      .st-actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 20px; }
      .st-btn { display: inline-flex; align-items: center; gap: 8px; padding: 10px 20px; border-radius: 12px;
        font-family: var(--i-font-mono); font-size: 0.74rem; letter-spacing: 0.08em; text-decoration: none;
        border: 1px solid rgba(255, 255, 255, 0.13); color: #f2f0ec; background: rgba(255, 255, 255, 0.045);
        transition: all 0.25s var(--i-ease); }
      .st-btn:hover { transform: translateY(-2px); border-color: rgba(245, 158, 11, 0.55); }
      .st-btn.primary { background: linear-gradient(135deg, #f59e0b, #d97706); border: none; color: #14100b;
        box-shadow: 0 8px 24px rgba(217, 119, 6, 0.35); }
    </style>

    <section class="st-section">
      <div class="st-head">
        <div>
          <div class="label" style="color: rgba(242, 240, 236, 0.55)">LIVE TELEMETRY</div>
          <h1>Status &amp; <em>live stats</em></h1>
          <p style="color: rgba(242, 240, 236, 0.55); max-width: 560px; margin-top: 10px">
            Everything this deployment is doing right now — songs fetched, streams served,
            bytes on the wire, per-provider health and latency. Auto-refreshing dashboard.
          </p>
        </div>
        <div class="st-livebox">
          <span class="st-status"><span class="st-dot" id="stDot"></span><span id="stStatus">CONNECTING...</span></span>
          <div class="st-countdown" title="Next refresh">
            <svg viewBox="0 0 72 72" aria-hidden="true">
              <circle cx="36" cy="36" r="22" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="4"/>
              <circle class="st-cd-fg" cx="36" cy="36" r="22" fill="none" stroke="#fbbf24" stroke-width="4"
                      stroke-linecap="round" stroke-dasharray="138.2" style="animation: stCd 5s linear infinite;"/>
            </svg>
            <span class="st-cd-num"><b id="stCd">5</b>NEXT</span>
          </div>
        </div>
      </div>
    </section>

    <section class="st-section">
      <div class="st-tiles">
        <div class="st-tile hot"><span class="k">SONGS FETCHED</span><br><span class="v skel" id="stFetched">—</span>
          <div class="s">tracks delivered to listeners</div></div>
        <div class="st-tile hot"><span class="k">TOTAL STREAMS</span><br><span class="v skel" id="stStreams">—</span>
          <div class="s" id="stStreamDelta">playback requests served</div></div>
        <div class="st-tile hot"><span class="k">DOWNLOADS</span><br><span class="v skel" id="stDownloads">—</span>
          <div class="s">attachment saves (MP3)</div></div>
        <div class="st-tile"><span class="k">DATA STREAMED</span><br><span class="v skel" id="stBytes">—</span>
          <div class="s">audio bytes sent to clients</div></div>
        <div class="st-tile"><span class="k">AVG PLAY LATENCY</span><br><span class="v skel" id="stLatency">—</span>
          <div class="s" id="stLatSub">p50 — &middot; p95 —</div>
          <svg class="st-spark" id="stSparkLat" viewBox="0 0 120 36" preserveAspectRatio="none" aria-hidden="true"></svg>
        </div>
      </div>
    </section>

    <section class="st-section">
      <div class="st-grid2">
        <div class="st-panel">
          <div class="st-sec-head"><h2>Live right now</h2><span class="hint" id="stUpdated">last update —</span></div>
          <div class="st-tiles" style="margin-top:14px">
            <div class="st-tile" style="animation:none"><span class="k">ACTIVE LISTENERS</span><br><span class="v skel" id="stListeners">—</span>
              <div class="s">requests in the last 30s</div>
              <svg class="st-spark" id="stSparkList" viewBox="0 0 120 36" preserveAspectRatio="none" aria-hidden="true"></svg>
            </div>
            <div class="st-tile" style="animation:none"><span class="k">IN-FLIGHT STREAMS</span><br><span class="v skel" id="stInflight">—</span>
              <div class="s">audio responses streaming now</div></div>
            <div class="st-tile" style="animation:none"><span class="k">UNIQUE (1H)</span><br><span class="v skel" id="stUnique">—</span>
              <div class="s">distinct listeners, last hour</div></div>
            <div class="st-tile" style="animation:none"><span class="k">SEARCHES</span><br><span class="v skel" id="stSearches">—</span>
              <div class="s" id="stSearchAvg">avg — ms per query</div></div>
          </div>
        </div>
        <div class="st-panel">
          <div class="st-sec-head"><h2>Top queries</h2><span class="hint">what listeners are looking for</span></div>
          <div class="st-qq" id="stQueries" style="margin-top:14px"><span class="st-qchip">no searches yet...</span></div>
        </div>
      </div>
    </section>

    <section class="st-section">
      <div class="st-grid2">
        <div class="st-panel">
          <div class="st-sec-head"><h2>Providers</h2><span class="hint">share &middot; latency &middot; health</span></div>
          <div id="stProviders" style="margin-top:8px"></div>
        </div>
        <div class="st-panel">
          <div class="st-sec-head"><h2>Top tracks</h2><span class="hint">by plays this server</span></div>
          <div id="stTracks" style="margin-top:8px"></div>
        </div>
      </div>
    </section>

    <section class="st-section">
      <div class="st-panel">
        <div class="st-sec-head"><h2>Event feed</h2><span class="hint">newest first &middot; last 40 events</span></div>
        <div class="st-events" id="stEvents" role="log" aria-live="polite" aria-label="Live event feed" style="margin-top:12px"></div>
      </div>
    </section>

    <section class="st-section">
      <div class="st-panel">
        <div class="st-sec-head"><h2>System</h2><span class="hint">this deployment, not marketing</span></div>
        <div class="st-sys" style="margin-top:14px">
          <div class="st-sysrow"><div class="k">SERVER UPTIME</div><div class="v" id="stUptime">0s</div></div>
          <div class="st-sysrow"><div class="k">API VERSION</div><div class="v" id="stVersion">2.0.0</div></div>
          <div class="st-sysrow"><div class="k">CATALOG SONGS</div><div class="v" id="stCatalog">0</div></div>
          <div class="st-sysrow"><div class="k">RATE LIMIT</div><div class="v" id="stRate">—</div></div>
          <div class="st-sysrow"><div class="k">DATABASE</div><div class="v" id="stDb">checking</div></div>
          <div class="st-sysrow"><div class="k">RATE LIMIT LAYER</div><div class="v" id="stRedis">checking</div></div>
        </div>
        <div class="st-actions">
          <a class="st-btn primary" href="/">&#9654; OPEN THE PLAYER</a>
          <a class="st-btn" href="/api/stats/live">VIEW RAW JSON</a>
          <a class="st-btn" href="/docs">API DOCS</a>
        </div>
      </div>
    </section>

    <script>
    (function () {
      var POLL_MS = 5000;
      var seen = {};
      var startedAt = Date.now() / 1000;

      function $(id) { return document.getElementById(id); }
      function fmtNum(n) {
        n = Number(n) || 0;
        return n.toLocaleString('en-US');
      }
      function fmtBytes(n) {
        n = Number(n) || 0;
        if (n < 1024) return fmtNum(n) + ' B';
        if (n < 1048576) return (n / 1024).toFixed(1) + ' KB';
        if (n < 1073741824) return (n / 1048576).toFixed(1) + ' MB';
        return (n / 1073741824).toFixed(2) + ' GB';
      }
      function fmtAgo(ts) {
        if (!ts) return 'never';
        var s = Math.max(0, Math.round(Date.now() / 1000 - ts));
        if (s < 60) return s + 's ago';
        if (s < 3600) return Math.floor(s / 60) + 'm ago';
        return Math.floor(s / 3600) + 'h ago';
      }
      function fmtUptime(secs) {
        secs = Math.max(0, Math.floor(secs));
        var d = Math.floor(secs / 86400), h = Math.floor(secs % 86400 / 3600),
            m = Math.floor(secs % 3600 / 60), s = secs % 60;
        var out = '';
        if (d) out += d + 'd ';
        out += (d ? String(h).padStart(2, '0') : h) + 'h ' + String(m).padStart(2, '0') + 'm ' + String(s).padStart(2, '0') + 's';
        return out;
      }
      function set(el, text, flash) {
        if (!el) return;
        if (el.classList && el.classList.contains('skel')) el.classList.remove('skel');
        if (el.textContent === text) return;
        el.textContent = text;
        if (flash && el.classList) {
          el.classList.remove('flash');
          void el.offsetWidth;
          el.classList.add('flash');
        }
      }
      function spark(id, values) {
        var el = $(id);
        if (!el) return;
        if (!values || values.length < 2) { el.innerHTML = ''; return; }
        var max = Math.max.apply(null, values), min = Math.min.apply(null, values);
        var span = (max - min) || 1, W = 120, H = 36;
        var pts = values.map(function (v, i) {
          var x = (i / (values.length - 1)) * W;
          var y = H - 4 - ((v - min) / span) * (H - 10);
          return x.toFixed(1) + ',' + y.toFixed(1);
        });
        el.innerHTML =
          '<path class="area" d="M0,' + H + ' L' + pts.join(' L') + ' L' + W + ',' + H + ' Z"/>' +
          '<polyline class="line" points="' + pts.join(' ') + '"/>';
      }
      function esc(s) {
        return String(s).replace(/[&<>"]/g, function (c) {
          return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c];
        });
      }

      var hist = { lat: [], listeners: [] };
      var prev = null, feedLostShown = false;

      function renderLive(data) {
        startedAt = data.server_started_at || (Date.now() / 1000);
        var t = data.totals || {}, live = data.live || {}, lat = data.latency || {};
        set($('stFetched'), fmtNum(t.songs_fetched), true);
        set($('stStreams'), fmtNum(t.streams), true);
        set($('stDownloads'), fmtNum(t.downloads), true);
        set($('stBytes'), fmtBytes(t.bytes_served), true);
        set($('stLatency'), fmtNum(Math.round(lat.avg_ms || 0)) + ' ms', true);
        set($('stLatSub'), 'p50 ' + fmtNum(Math.round(lat.p50_ms || 0)) + ' ms · p95 ' + fmtNum(Math.round(lat.p95_ms || 0)) + ' ms');
        hist.lat.push(Number(lat.avg_ms) || 0);
        if (hist.lat.length > 48) hist.lat.shift();
        spark('stSparkLat', hist.lat);
        if (prev && (t.streams || 0) > prev) {
          set($('stStreamDelta'), '+' + fmtNum((t.streams || 0) - prev) + ' since last update');
        } else if (prev !== null && (t.streams || 0) === prev) {
          set($('stStreamDelta'), 'playback requests served');
        }
        prev = t.streams || 0;
        set($('stListeners'), fmtNum(live.active_listeners || 0), true);
        hist.listeners.push(Number(live.active_listeners) || 0);
        if (hist.listeners.length > 48) hist.listeners.shift();
        spark('stSparkList', hist.listeners);
        set($('stInflight'), fmtNum(live.active_streams || 0), true);
        set($('stUnique'), fmtNum(live.unique_listeners_1h || 0), true);
        set($('stSearches'), fmtNum(live.searches_total || 0), true);
        set($('stSearchAvg'), 'avg ' + fmtNum(Math.round(live.search_avg_ms || 0)) + ' ms per query');
        set($('stVersion'), data.version || '—');
        set($('stCatalog'), fmtNum(data.catalog_total || 0));
        set($('stRate'), (Number(data.rate_limit_per_minute) > 0
          ? fmtNum(data.rate_limit_per_minute) + ' rpm'
          : 'unlimited'), true);
        var redis = $('stRedis');
        if (redis) {
          redis.textContent = data.redis ? 'redis (fast counter window)' : 'in-memory window';
          redis.className = 'v';
        }
        setHealthOk(true);

        var prov = $('stProviders');
        if (prov) {
          var rows = (data.providers || []).map(function (p) {
            var cls = p.last_used && (Date.now() / 1000 - p.last_used) < 120 ? 'on' : '';
            var latTxt = p.avg_latency_ms ? Math.round(p.avg_latency_ms) + ' ms' : '—';
            return '<div class="st-prow">' +
              '<span class="st-pdot ' + cls + '"></span>' +
              '<span class="st-pname">' + esc(p.name) + '</span>' +
              '<span class="st-pbar"><i style="width:' + (p.share || 0) + '%"></i></span>' +
              '<span class="st-pnum">' + fmtNum(p.streams) + '</span>' +
              '<span class="st-plat">' + latTxt + '</span>' +
              '</div>';
          });
          var busy = (data.providers || []).reduce(function (a, p) { return a + p.streams; }, 0);
          if (!busy) rows.push('<div class="st-prow"><span class="st-pdot"></span><span class="st-pname" style="color:rgba(242,240,236,0.45)">No plays yet</span><span class="st-pbar"></span><span class="st-pnum">0</span><span class="st-plat">—</span></div>');
          prov.innerHTML = rows.join('');
        }

        var trk = $('stTracks');
        if (trk) {
          var list = data.tracks || [];
          var top = list.length ? list[0].streams + list[0].downloads : 0;
          if (!list.length) {
            trk.innerHTML = '<div class="st-trow"><span class="st-rank">—</span><span class="st-title" style="color:rgba(242,240,236,0.45)">No songs played yet</span><span></span><span class="st-tbar"></span><span class="st-tnum">0</span></div>';
          } else {
            trk.innerHTML = list.map(function (t, i) {
              var plays = t.streams + t.downloads;
              var pct = top > 0 ? Math.max(4, Math.round(plays / top * 100)) : 4;
              return '<div class="st-trow">' +
                '<span class="st-rank">' + String(i + 1).padStart(2, '0') + '</span>' +
                '<span class="st-title">' + esc(t.title) + '</span>' +
                '<span class="st-chip">' + esc(t.provider) + '</span>' +
                '<span class="st-tbar"><i style="width:' + pct + '%"></i></span>' +
                '<span class="st-tnum">' + fmtNum(plays) + '</span>' +
                '</div>';
            }).join('');
          }
        }

        var q = $('stQueries');
        if (q) {
          var qs = data.queries || [];
          q.innerHTML = qs.length
            ? qs.map(function (x) { return '<span class="st-qchip">' + esc(x.q) + '<b>' + fmtNum(x.count) + '</b></span>'; }).join('')
            : '<span class="st-qchip">no searches yet...</span>';
        }

        var ev = $('stEvents');
        if (ev) {
          var lines = (data.events || []).map(function (e) {
            var key = e.at + ':' + e.kind + ':' + e.label + ':' + e.meta;
            var fresh = !seen[key];
            seen[key] = 1;
            var d = new Date(e.at * 1000);
            var hh = String(d.getHours()).padStart(2, '0'), mm = String(d.getMinutes()).padStart(2, '0'), ss = String(d.getSeconds()).padStart(2, '0');
            return '<div class="st-ev st-ev-' + esc(e.kind) + (fresh ? ' new' : '') + '">' +
              '<span class="st-ev-t">' + hh + ':' + mm + ':' + ss + '</span>' +
              '<span class="st-ev-k">' + esc(e.kind.toUpperCase()) + '</span>' +
              '<span class="st-ev-l">' + esc(e.label) + '</span>' +
              '<span class="st-ev-k" style="width:auto">' + esc(e.meta) + '</span>' +
              '</div>';
          }).join('');
          ev.innerHTML = lines || '<div class="st-ev"><span class="st-ev-l">No activity yet — play something on the home page.</span></div>';
        }

        var now = new Date();
        set($('stUpdated'), 'last update ' + String(now.getHours()).padStart(2, '0') + ':' + String(now.getMinutes()).padStart(2, '0') + ':' + String(now.getSeconds()).padStart(2, '0'));
      }

      function setHealthOk(ok) {
        var dot = $('stDot');
        if (!dot) return;
        if (ok) {
          dot.className = 'st-dot on';
          set($('stStatus'), 'LIVE');
          var db = $('stDb');
          if (db) { db.textContent = 'ok'; db.className = 'v ok'; }
        }
      }
      function setHealthBad(msg, isError) {
        var dot = $('stDot');
        if (dot) dot.className = 'st-dot ' + (isError ? 'bad' : 'warn');
        set($('stStatus'), msg);
        var db = $('stDb');
        if (db) { db.textContent = isError ? 'unreachable' : 'degraded'; db.className = 'v warn'; }
      }

      function poll() {
        fetch('/api/stats/live').then(function (r) {
          if (!r.ok) throw new Error('http ' + r.status);
          return r.json();
        }).then(function (data) {
          feedLostShown = false;
          renderLive(data);
          return fetch('/health').then(function (r) { return r.ok ? r.json() : null; })
            .catch(function () { return null; });
        }).then(function (h) {
          var db = $('stDb');
          if (db && h && h.checks) {
            var ok = h.checks.postgres === 'ok';
            db.textContent = ok ? 'ok' : 'degraded';
            db.className = 'v ' + (ok ? 'ok' : 'warn');
          }
        }).catch(function (err) {
          setHealthBad('RETRYING', true);
          if (!feedLostShown && window.showToast) {
            window.showToast('Live stats feed interrupted - retrying', 'error');
            feedLostShown = true;
          }
        });
      }

      poll();
      setInterval(poll, POLL_MS);

      var cdEl = $('stCd');
      setInterval(function () {
        var v = parseInt(cdEl.textContent, 10);
        v = v > 1 ? v - 1 : 5;
        cdEl.textContent = v;
      }, 1000);

      setInterval(function () {
        var up = $('stUptime');
        if (up && startedAt) up.textContent = fmtUptime(Date.now() / 1000 - startedAt);
      }, 1000);
    })();
    </script>
    """
    return _page("Iota Live Stats", body)


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
