"""IOTA AUDIO application shell (music streaming SPA).

Served at "/". Developer landing page moved to "/dev".
"""
from __future__ import annotations

_FAVICON = (
    "data:image/svg+xml,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E"
    "%3Crect width='64' height='64' rx='14' fill='%230B0B0E'/%3E"
    "%3Cpath d='M46 14v26a7 7 0 1 1-4-6.3V24l-14 4v16a7 7 0 1 1-4-6.3V20z'"
    " fill='%23FFAA19'/%3E%3C/svg%3E"
)


def app_shell_html() -> str:
    """Full application shell: sidebar + topbar + views + player + queue."""
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0B0B0E">
<meta name="description" content="IOTA AUDIO - cinematic music discovery and streaming with live provider-backed playback.">
<title>IOTA AUDIO</title>
<link rel="icon" href="_FAVICON_">
<link rel="stylesheet" href="/static/app.css">
<link rel="preconnect" href="https://i.ytimg.com">
</head>
<body>
<div class="app-grid">
  <a class="skip-link" href="#view">Skip to content</a>

  <aside class="sidebar" id="sidebar" aria-label="Primary navigation">
    <a class="brand" href="#/" aria-label="IOTA AUDIO home">
      <span class="brand-mark" aria-hidden="true"><svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M9 18V6l12-2v11.1a3.9 3.9 0 1 1-2-3.4V7.6L11 9v9.1A3.9 3.9 0 1 1 9 14.7z"/></svg></span>
      <span class="brand-name">IOTA <em>AUDIO</em></span>
    </a>

    <nav class="side-nav" aria-label="Main">
      <p class="side-label">Menu</p>
      <a class="nav-item" data-route="home" href="#/">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h5v-6h4v6h5V9.5"/></svg>
        <span>Home</span></a>
      <a class="nav-item" data-route="search" href="#/search">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.5" y2="16.5"/></svg>
        <span>Search</span></a>
      <a class="nav-item" data-route="songs" href="#/songs">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M9 18V6l12-2v11.1"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="15.1" r="3"/></svg>
        <span>All Songs</span></a>
      <a class="nav-item" data-route="moods" href="#/moods">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M8 14s1.6 2 4 2 4-2 4-2"/><line x1="9" y1="9.5" x2="9.01" y2="9.5"/><line x1="15" y1="9.5" x2="15.01" y2="9.5"/></svg>
        <span>Moods &amp; Tags</span></a>
      <p class="side-label">Your Library</p>
      <a class="nav-item" data-route="liked" href="#/liked">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" aria-hidden="true"><path d="M12 21s-7.5-4.6-9.5-9.1C1 8 3.5 4.5 7 4.5c2.2 0 3.9 1.2 5 3 1.1-1.8 2.8-3 5-3 3.5 0 6 3.5 4.5 7.4C19.5 16.4 12 21 12 21z"/></svg>
        <span>Liked Songs</span></a>
      <a class="nav-item" data-route="recent" href="#/recent">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/></svg>
        <span>Recently Played</span></a>
      <a class="nav-item" data-route="playlists" href="#/playlists">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><line x1="4" y1="7" x2="14" y2="7"/><line x1="4" y1="12" x2="14" y2="12"/><line x1="4" y1="17" x2="10" y2="17"/><circle cx="18" cy="16" r="2.5"/><path d="M20.5 16V6l-2 .5"/></svg>
        <span>Playlists</span></a>
      <a class="nav-item" data-route="queue" href="#/queue">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><line x1="4" y1="8" x2="20" y2="8"/><line x1="4" y1="16" x2="12" y2="16"/><path d="M16 18.5v-5l4 2.5z" fill="currentColor" stroke="none"/></svg>
        <span>Queue</span></a>
    </nav>

    <div class="side-playlists" id="sidePlaylists" aria-label="Your playlists"></div>

    <div class="side-foot">
      <p class="side-label">Tools</p>
      <a class="nav-item nav-mini" href="/dev"><span>Developer Console</span></a>
      <a class="nav-item nav-mini" href="/docs"><span>API Docs</span></a>
      <a class="nav-item nav-mini" href="/status"><span>Live Stats</span></a>
      <a class="nav-item nav-mini" href="/about"><span>About</span></a>
      <p class="guest-note">
        <span class="dot dot-ok" aria-hidden="true"></span>Guest mode
        <span>Library stays in this browser</span>
      </p>
    </div>
  </aside>

  <div class="backdrop" id="backdrop" hidden></div>

  <header class="topbar" id="topbar">
    <button class="icon-btn mobile-only" id="navToggle" aria-label="Open navigation" aria-controls="sidebar" aria-expanded="false">
      <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><line x1="4" y1="7" x2="20" y2="7"/><line x1="4" y1="12" x2="20" y2="12"/><line x1="4" y1="17" x2="20" y2="17"/></svg>
    </button>
    <form class="search-wrap" id="searchForm" role="search" autocomplete="off">
      <svg class="search-ic" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.5" y2="16.5"/></svg>
      <input id="searchInput" type="search" placeholder="Search for songs, artists, albums..." aria-label="Search" enterkeyhint="search">
      <button type="button" class="search-clear" id="searchClear" aria-label="Clear search" hidden>&times;</button>
      <div class="suggest" id="suggestBox" role="listbox" aria-label="Search suggestions" hidden></div>
    </form>
    <div class="topbar-right">
      <kbd class="kbd desktop-only" title="Press Ctrl+K to search">Ctrl K</kbd>
      <span class="status-pill" id="apiPill" title="API status"><span class="dot" aria-hidden="true"></span><span id="apiPillText">API</span></span>
    </div>
  </header>

  <main class="view" id="view" tabindex="-1" aria-live="off"></main>

  <aside class="queue-drawer" id="queueDrawer" aria-label="Playback queue" aria-hidden="true">
    <div class="queue-head">
      <h2>Queue <span id="queueCount" class="muted"></span></h2>
      <div class="queue-actions">
        <button class="btn btn-dim btn-s" id="queueClear" type="button">Clear</button>
        <button class="icon-btn" id="queueClose" aria-label="Close queue" type="button">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><line x1="6" y1="6" x2="18" y2="18"/><line x1="18" y1="6" x2="6" y2="18"/></svg>
        </button>
      </div>
    </div>
    <div class="queue-list" id="queueList" role="list"></div>
  </aside>

  <footer class="playerbar" id="playerbar" aria-label="Player" hidden>
    <audio id="audio" preload="none"></audio>

    <div class="pb-left">
      <button class="pb-art" id="pbExpand" type="button" aria-label="Expand player">
        <span class="art-fallback" id="pbArtFallback" hidden></span>
        <img id="pbArt" alt="" hidden>
        <span class="pb-eq" id="pbEq" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
      </button>
      <div class="pb-meta">
        <p class="pb-title" id="pbTitle" title="">Ready</p>
        <p class="pb-artist" id="pbArtist">Pick a track to start</p>
      </div>
      <button class="icon-btn like-btn" id="pbLike" aria-label="Like current track" aria-pressed="false" type="button">
        <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" aria-hidden="true"><path d="M12 21s-7.5-4.6-9.5-9.1C1 8 3.5 4.5 7 4.5c2.2 0 3.9 1.2 5 3 1.1-1.8 2.8-3 5-3 3.5 0 6 3.5 4.5 7.4C19.5 16.4 12 21 12 21z"/></svg>
      </button>
    </div>

    <div class="pb-center">
      <div class="pb-ctrls">
        <button class="icon-btn" id="shuffleBtn" aria-label="Shuffle" aria-pressed="false" type="button" title="Shuffle">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 6h3.5c1.6 0 3 .8 3.9 2.1l1.2 1.8M21 6h-3.5c-5 0-6 9-11 12H3"/><path d="M18.5 3.5 21 6l-2.5 2.5M3 18h3.5c1.6 0 3-.8 3.9-2.1l1.2-1.8M21 18h-3.5"/><path d="M18.5 15.5 21 18l-2.5 2.5"/></svg>
        </button>
        <button class="icon-btn" id="prevBtn" aria-label="Previous track" type="button">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true"><path d="M7 6h2v12H7zM19 6v12l-9-6z"/></svg>
        </button>
        <button class="pb-play" id="playBtn" aria-label="Play" type="button" disabled>
          <svg id="playIc" viewBox="0 0 24 24" width="22" height="22" fill="currentColor" aria-hidden="true"><path d="M8 5v14l11-7z"/></svg>
        </button>
        <button class="icon-btn" id="nextBtn" aria-label="Next track" type="button">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true"><path d="M17 6h-2v12h2zM5 6l9 6-9 6z"/></svg>
        </button>
        <button class="icon-btn" id="repeatBtn" aria-label="Repeat off" aria-pressed="false" type="button" title="Repeat">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17 3.5 21 7l-4 3.5"/><path d="M4 12V9a3 3 0 0 1 3-3h14"/><path d="M7 20.5 3 17l4-3.5"/><path d="M20 12v3a3 3 0 0 1-3 3H3"/></svg>
          <span class="rep-one" hidden>1</span>
        </button>
      </div>
      <div class="pb-seek">
        <span class="pb-time" id="curTime">0:00</span>
        <input id="seek" class="seek-range" type="range" min="0" max="100" step="0.1" value="0" aria-label="Seek" disabled>
        <span class="pb-time" id="durTime">0:00</span>
      </div>
    </div>

    <div class="pb-right">
      <button class="icon-btn" id="queueBtn" aria-label="Toggle queue" data-count="0" type="button" title="Queue">
        <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><line x1="4" y1="8" x2="20" y2="8"/><line x1="4" y1="16" x2="12" y2="16"/><path d="M16 18.5v-5l4 2.5z" fill="currentColor" stroke="none"/></svg>
      </button>
      <button class="icon-btn vol-mute" id="muteBtn" aria-label="Mute" type="button">
        <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 9v6h3.5L12 19V5L7.5 9z" fill="currentColor" stroke="none"/><path id="volWaves" d="M15.5 9.5a3.5 3.5 0 0 1 0 5M18 7.5a6.5 6.5 0 0 1 0 9"/></svg>
      </button>
      <input id="vol" class="vol-range" type="range" min="0" max="1" step="0.01" value="1" aria-label="Volume">
    </div>
  </footer>

  <div class="statusline" id="statusline" role="status" aria-live="polite"></div>

  <div class="toast-wrap" id="toastWrap" aria-live="polite"></div>

  <div class="modal-back" id="modalBack" hidden>
    <div class="modal" id="modal" role="dialog" aria-modal="true" aria-labelledby="modalTitle"></div>
  </div>
</div>
<script src="/static/app.js" defer></script>
</body>
</html>""".replace("_FAVICON_", _FAVICON)
