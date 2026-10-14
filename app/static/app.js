// IOTA AUDIO - application shell (sidebar, views, player, queue, library)
(function () {
  'use strict';

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  }
  function esc(str) {
    return String(str == null ? '' : str).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function fmt(sec) {
    if (!sec || !isFinite(sec)) return '--:--';
    var m = Math.floor(sec / 60);
    var s = Math.floor(sec % 60);
    return m + ':' + (s < 10 ? '0' : '') + s;
  }
  function initials(title) {
    var parts = String(title || '?').trim().split(/\s+/).slice(0, 2);
    return parts.map(function (w) { return w.charAt(0); }).join('').toUpperCase() || 'IO';
  }
  function debounce(fn, ms) {
    var t = null;
    return function () {
      var args = arguments, self = this;
      clearTimeout(t);
      t = setTimeout(function () { fn.apply(self, args); }, ms);
    };
  }
  function uid() { return Date.now().toString(36) + Math.random().toString(36).slice(2, 7); }
  function timeAgo(ts) {
    var d = Math.floor((Date.now() - ts) / 1000);
    if (d < 60) return 'just now';
    if (d < 3600) return Math.floor(d / 60) + ' min ago';
    if (d < 86400) return Math.floor(d / 3600) + ' h ago';
    return Math.floor(d / 86400) + ' d ago';
  }
  function providerLabel(p) {
    if (!p) return 'Live';
    var k = String(p).toLowerCase();
    return { yt: 'YouTube', youtube: 'YouTube', dz: 'Deezer', deezer: 'Deezer', am: 'Apple Music', 'apple music': 'Apple Music' }[k] ||
      (k.charAt(0).toUpperCase() + k.slice(1));
  }

  var ICONS = {
    play: '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true"><path d="M8 5v14l11-7z"/></svg>',
    pause: '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true"><path d="M6 5h4v14H6zM14 5h4v14h-4z"/></svg>',
    heart: '<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" aria-hidden="true"><path d="M12 21s-7.5-4.6-9.5-9.1C1 8 3.5 4.5 7 4.5c2.2 0 3.9 1.2 5 3 1.1-1.8 2.8-3 5-3 3.5 0 6 3.5 4.5 7.4C19.5 16.4 12 21 12 21z"/></svg>',
    plus: '<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>',
    queueNext: '<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><line x1="4" y1="7" x2="20" y2="7"/><line x1="4" y1="12" x2="14" y2="12"/><line x1="4" y1="17" x2="10" y2="17"/><path d="M15 15.5v6l5-3z" fill="currentColor" stroke="none"/></svg>',
    copy: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg>',
    trash: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M9 7V5h6v2M6 7l1 13h10l1-13"/></svg>',
    up: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 15l6-6 6 6"/></svg>',
    down: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>',
    search: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.5" y2="16.5"/></svg>',
    music: '<svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M9 18V6l12-2v11.1"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="15.1" r="3"/></svg>',
    shuffle: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 6h3.5c1.6 0 3 .8 3.9 2.1l1.2 1.8M21 6h-3.5c-5 0-6 9-11 12H3"/><path d="M18.5 3.5 21 6l-2.5 2.5M21 18h-3.5"/><path d="M18.5 15.5 21 18l-2.5 2.5"/></svg>',
    edit: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/></svg>',
    info: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><line x1="12" y1="10.5" x2="12" y2="16"/><line x1="12" y1="7.5" x2="12.01" y2="7.5"/></svg>',
    link: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 14a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1.5 1.5"/><path d="M14 10a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7L12.5 18.5"/></svg>',
    clock: '<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/></svg>'
  };

  var LS = {
    get: function (k, d) {
      try {
        var raw = localStorage.getItem(k);
        return raw ? JSON.parse(raw) : d;
      } catch (e) { return d; }
    },
    set: function (k, v) {
      try { localStorage.setItem(k, JSON.stringify(v)); return true; } catch (e) { return false; }
    }
  };
  var K = {
    liked: 'iota.liked.v1',
    recent: 'iota.recent.v1',
    playlists: 'iota.playlists.v1',
    settings: 'iota.settings.v1',
    counts: 'iota.counts.v1'
  };

  var settings = LS.get(K.settings, { volume: 1, autoplayNext: true, reduceMotion: false });
  function saveSettings() { LS.set(K.settings, settings); }
  function applySettings() {
    document.body.classList.toggle('reduce-motion', !!settings.reduceMotion);
  }

  var liked = LS.get(K.liked, {});
  var recent = LS.get(K.recent, []);
  var playlists = LS.get(K.playlists, []);
  var counts = LS.get(K.counts, {});
  function saveLiked() { LS.set(K.liked, liked); }
  function saveRecent() { LS.set(K.recent, recent); }
  function savePlaylists() { LS.set(K.playlists, playlists); }
  function saveCounts() { LS.set(K.counts, counts); }
  function bumpCount(t) {
    if (!t || !t.key) return;
    counts[t.key] = (counts[t.key] || 0) + 1;
    saveCounts();
  }

  function isLiked(t) { return !!liked[t.key]; }
  function toggleLike(t) {
    if (liked[t.key]) {
      delete liked[t.key];
      toast('Removed from Liked', 'ok');
    } else {
      liked[t.key] = { track: snap(t), ts: Date.now() };
      toast('Added to Liked', 'ok');
    }
    saveLiked();
    refreshLikeUI(t.key);
    renderSidePlaylists();
  }
  function likedTracks() {
    return Object.keys(liked).map(function (k) { return liked[k]; })
      .sort(function (a, b) { return b.ts - a.ts; })
      .map(function (e) { return e.track; });
  }
  var recentSeen = {};
  function addRecent(t) {
    var now = Date.now();
    if (recentSeen[t.key] && now - recentSeen[t.key] < 30000) return;
    recentSeen[t.key] = now;
    recent = recent.filter(function (x) { return x.key !== t.key; });
    recent.unshift(snap(t));
    if (recent.length > 60) recent = recent.slice(0, 60);
    saveRecent();
  }
  function createPlaylist(name) {
    var pl = { id: uid(), name: name, desc: '', tracks: [], created: Date.now(), updated: Date.now() };
    playlists.unshift(pl);
    savePlaylists();
    renderSidePlaylists();
    return pl;
  }
  function findPlaylist(id) {
    for (var i = 0; i < playlists.length; i++) if (playlists[i].id === id) return playlists[i];
    return null;
  }
  function addToPlaylist(id, t) {
    var pl = findPlaylist(id);
    if (!pl) return false;
    pl.tracks.push(snap(t));
    pl.updated = Date.now();
    savePlaylists();
    return true;
  }

  function snap(t) {
    return {
      key: t.key, id: t.id, source: t.source, title: t.title, artist: t.artist,
      duration: t.duration, thumb: t.thumb, url: t.url, tags: t.tags || [], provider: t.provider
    };
  }

  function norm(s, live) {
    var id = live ? (s.media_id || '') : (s.video_id || '');
    var thumb = s.thumbnail || s.thumbnail_url || '';
    if (thumb && thumb.indexOf('default.svg') !== -1) thumb = '';
    return {
      source: live ? 'live' : 'catalog',
      id: id,
      key: (live ? 'live:' : 'cat:') + id,
      title: s.title || 'Unknown title',
      artist: s.artist || 'Unknown artist',
      duration: s.duration_seconds || 0,
      thumb: thumb,
      url: live ? (s.play_url || ('/api/live-play/' + id)) : (s.stream_url || ('/api/file/' + id)),
      tags: s.tags || [],
      provider: live ? providerLabel(s.provider) : 'Catalog'
    };
  }

  function apiGet(url, ms) {
    var ctrl = ('AbortController' in window) ? new AbortController() : null;
    var timer = setTimeout(function () { if (ctrl) ctrl.abort(); }, ms || 20000);
    return fetch(url, ctrl ? { signal: ctrl.signal } : undefined)
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .finally(function () { clearTimeout(timer); });
  }
  var API = {
    random: function (n) { return apiGet('/api/random?limit=' + (n || 12)); },
    trending: function (n) { return apiGet('/api/trending?limit=' + (n || 12)); },
    songs: function (page, limit) { return apiGet('/api/songs?page=' + page + '&limit=' + (limit || 50)); },
    catalogSearch: function (q, n) { return apiGet('/api/search?q=' + encodeURIComponent(q) + '&limit=' + (n || 30)); },
    suggest: function (q) { return apiGet('/api/suggest?q=' + encodeURIComponent(q), 8000); },
    live: function (q, n) { return apiGet('/api/live?q=' + encodeURIComponent(q) + '&limit=' + (n || 25), 30000); }
  };

  var toastWrap = $('#toastWrap');
  function toast(msg, kind) {
    if (!toastWrap) return;
    var el = document.createElement('div');
    el.className = 'toast toast-' + (kind || 'info');
    el.textContent = msg;
    toastWrap.appendChild(el);
    setTimeout(function () { el.remove(); }, 3200);
  }
  var statusEl = $('#statusline');
  var statusTimer = null;
  function status(msg, kind) {
    if (!statusEl) return;
    statusEl.textContent = msg;
    statusEl.className = 'statusline show' + (kind ? ' ' + kind : '');
    clearTimeout(statusTimer);
    statusTimer = setTimeout(function () { statusEl.classList.remove('show'); }, 2200);
  }

  var modalBack = $('#modalBack');
  var modalEl = $('#modal');
  function openModal(html) {
    modalEl.innerHTML = html;
    modalBack.hidden = false;
    var input = modalEl.querySelector('input[type="text"]');
    if (input) { input.focus(); input.select(); }
    else {
      var firstBtn = modalEl.querySelector('button');
      if (firstBtn) firstBtn.focus();
    }
    return modalEl;
  }
  function closeModal() {
    modalBack.hidden = true;
    modalEl.innerHTML = '';
  }
  if (modalBack) {
    modalBack.addEventListener('click', function (e) { if (e.target === modalBack) closeModal(); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !modalBack.hidden) closeModal(); });
  }
  function confirmModal(title, sub, okLabel, onOk) {
    openModal(
      '<h3>' + esc(title) + '</h3><p class="modal-sub">' + esc(sub) + '</p>' +
      '<div class="modal-acts"><button class="btn btn-dim" id="mCancel" type="button">Cancel</button>' +
      '<button class="btn btn-danger" id="mOk" type="button">' + esc(okLabel) + '</button></div>'
    );
    $('#mCancel').onclick = closeModal;
    $('#mOk').onclick = function () { closeModal(); onOk(); };
  }
  function promptModal(title, sub, placeholder, initial, okLabel, onSubmit) {
    openModal(
      '<h3>' + esc(title) + '</h3><p class="modal-sub">' + esc(sub) + '</p>' +
      '<input type="text" id="mInput" placeholder="' + esc(placeholder) + '" value="' + esc(initial || '') + '" maxlength="80">' +
      '<div class="modal-acts"><button class="btn btn-dim" id="mCancel" type="button">Cancel</button>' +
      '<button class="btn" id="mOk" type="button">' + esc(okLabel) + '</button></div>'
    );
    var input = $('#mInput');
    function submit() {
      var v = input.value.trim();
      if (!v) { input.focus(); return; }
      closeModal();
      onSubmit(v);
    }
    $('#mCancel').onclick = closeModal;
    $('#mOk').onclick = submit;
    input.addEventListener('keydown', function (e) { if (e.key === 'Enter') submit(); });
  }

  // ---------------- player ----------------
  var audio = $('#audio');
  var playerbar = $('#playerbar');
  var queue = [];
  var qi = -1;
  var current = null;
  var playing = false;
  var shuffleOn = false;
  var repeatMode = 'off';
  var order = [];
  var progressHooks = [];

  function renderQueueBadge() {
    var remaining = Math.max(0, queue.length - qi - 1);
    var btn = $('#queueBtn');
    if (btn) btn.setAttribute('data-count', String(remaining));
  }

  function loadTrack(t, autoplay) {
    current = t;
    playerbar.hidden = false;
    document.documentElement.classList.add('has-player');
    var ttl = $('#pbTitle');
    ttl.textContent = t.title;
    ttl.title = t.title;
    $('#pbArtist').textContent = t.artist + '  |  ' + t.provider;
    pendingSeekReset();
    var art = $('#pbArt'), fb = $('#pbArtFallback');
    if (t.thumb) {
      art.src = t.thumb;
      art.hidden = false;
      fb.hidden = true;
    } else {
      art.hidden = true;
      fb.hidden = false;
      fb.textContent = initials(t.title);
    }
    audio.src = t.url;
    audio.volume = settings.volume;
    $('#vol').value = String(settings.volume);
    setRangeFill($('#vol'), settings.volume * 100);
    $('#playBtn').disabled = false;
    updateLikeButton();
    updateMediaSession(t);
    status('BUFFERING', 'warn');
    if (autoplay !== false) {
      audio.play().then(function () {
        status('PLAYING', 'ok');
      }).catch(function () {
        setPlayingUI(false);
        status('TAP PLAY TO START', 'warn');
      });
    }
    markPlayingRows();
    syncSheet();
  }

  function playList(list, idx) {
    queue = list.slice();
    qi = idx;
    buildOrder();
    renderQueueBadge();
    if (queue[qi]) loadTrack(queue[qi], true);
    if (!$('#queueDrawer').classList.contains('open')) renderQueueViewIfActive();
  }

  function buildOrder() {
    order = [];
    for (var i = 0; i < queue.length; i++) order.push(i);
    if (shuffleOn) {
      var rest = order.filter(function (i) { return i !== qi; });
      for (var j = rest.length - 1; j > 0; j--) {
        var k = Math.floor(Math.random() * (j + 1));
        var tmp = rest[j]; rest[j] = rest[k]; rest[k] = tmp;
      }
      order = [qi].concat(rest);
    }
  }

  function positionInOrder() {
    for (var i = 0; i < order.length; i++) if (order[i] === qi) return i;
    return 0;
  }

  function next(manual) {
    if (!queue.length) return;
    if (!manual && repeatMode === 'one') { audio.currentTime = 0; audio.play(); return; }
    var pos = positionInOrder();
    if (pos < order.length - 1) {
      qi = order[pos + 1];
    } else if (repeatMode === 'all') {
      qi = order[0];
    } else {
      setPlayingUI(false);
      status('END OF QUEUE', '');
      return;
    }
    renderQueueBadge();
    loadTrack(queue[qi], true);
    if (isQueueRoute()) renderView();
  }
  function prev() {
    if (!queue.length) return;
    if (audio.currentTime > 3) { audio.currentTime = 0; return; }
    var pos = positionInOrder();
    if (pos > 0) qi = order[pos - 1];
    else if (repeatMode === 'all') qi = order[order.length - 1];
    else { audio.currentTime = 0; return; }
    renderQueueBadge();
    loadTrack(queue[qi], true);
    if (isQueueRoute()) renderView();
  }

  function setPlayingUI(on) {
    playing = on;
    var ic = $('#playIc');
    if (ic) ic.innerHTML = on ? '<path d="M6 5h4v14H6zM14 5h4v14h-4z"/>' : '<path d="M8 5v14l11-7z"/>';
    var pb = $('#playBtn');
    if (pb) {
      pb.setAttribute('aria-label', on ? 'Pause' : 'Play');
      pb.classList.toggle('is-playing', on);
    }
    var eq = $('#pbEq');
    if (eq) eq.classList.toggle('on', on);
    $$('.card.playing .eq-bars, .track-row.playing .eq-bars').forEach(function (e) { e.style.display = on ? '' : 'none'; });
    if ('mediaSession' in navigator) {
      try { navigator.mediaSession.playbackState = on ? 'playing' : 'paused'; } catch (e) {}
    }
    syncSheet();
  }

  function pendingSeekReset() {
    var seek = $('#seek');
    seek.value = '0';
    setRangeFill(seek, 0);
    $('#curTime').textContent = '0:00';
    $('#durTime').textContent = '0:00';
  }
  function setRangeFill(el, pct) {
    if (!el) return;
    el.style.setProperty('--fill', Math.max(0, Math.min(100, pct)) + '%');
  }
  function updateProgress() {
    var d = audio.duration || 0;
    var t = audio.currentTime || 0;
    var pct = d > 0 ? (t / d) * 100 : 0;
    var seek = $('#seek');
    seek.value = String(pct);
    setRangeFill(seek, pct);
    $('#curTime').textContent = fmt(t);
    $('#durTime').textContent = fmt(d);
    progressHooks.forEach(function (fn) { fn(t, d, pct); });
    if ('mediaSession' in navigator && 'setPositionState' in navigator.mediaSession && d > 0) {
      try { navigator.mediaSession.setPositionState({ duration: d, position: Math.min(t, d), playbackRate: 1 }); } catch (e) {}
    }
  }
  function updateLikeButton() {
    var b = $('#pbLike');
    if (!b) return;
    var on = current ? isLiked(current) : false;
    b.setAttribute('aria-pressed', on ? 'true' : 'false');
    b.classList.toggle('liked', on);
  }
  function refreshLikeUI(key) {
    $$('.like-btn[data-key]').forEach(function (b) {
      if (b.getAttribute('data-key') === key) {
        var on = !!liked[key];
        b.setAttribute('aria-pressed', on ? 'true' : 'false');
        b.classList.toggle('liked', on);
      }
    });
    $$('.like-btn-fire[data-key="' + key + '"]').forEach(function (b) {
      var on = !!liked[key];
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
      b.classList.toggle('liked', on);
    });
    updateLikeButton();
  }
  function updateMediaSession(t) {
    if (!('mediaSession' in navigator)) return;
    try {
      navigator.mediaSession.metadata = new MediaMetadata({
        title: t.title || 'Unknown track',
        artist: t.artist || 'IOTA AUDIO',
        album: t.provider || 'IOTA',
        artwork: t.thumb ? [
          { src: t.thumb, sizes: '256x256', type: 'image/jpeg' },
          { src: t.thumb, sizes: '512x512', type: 'image/jpeg' }
        ] : []
      });
    } catch (e) {}
  }
  function markPlayingRows() {
    $$('.playing-row-active').forEach(function (el) { el.classList.remove('playing-row-active'); });
  }

  function togglePlay() {
    if (!current) { toast('Nothing queued yet', 'err'); return; }
    if (audio.paused) {
      audio.play().catch(function () { status('PLAYBACK ERROR', 'err'); });
    } else {
      audio.pause();
    }
  }

  audio.addEventListener('play', function () { setPlayingUI(true); });
  audio.addEventListener('playing', function () {
    setPlayingUI(true);
    status('PLAYING', 'ok');
    if (current) { addRecent(current); bumpCount(current); }
  });
  audio.addEventListener('pause', function () { setPlayingUI(false); status('PAUSED', ''); });
  audio.addEventListener('waiting', function () { status('BUFFERING', 'warn'); });
  audio.addEventListener('stalled', function () { status('STALLED - RETRYING', 'warn'); });
  var skipLock = false;
  audio.addEventListener('error', function () {
    if (!audio.src) return;
    setPlayingUI(false);
    status('UNAVAILABLE', 'err');
    toast('This track could not be played. Try another.', 'err');
    if (!skipLock && queue.length > 1 && qi >= 0) {
      skipLock = true;
      setTimeout(function () {
        skipLock = false;
        if (queue.length > 1 && (positionInOrder() < order.length - 1 || repeatMode === 'all')) {
          status('SKIPPING', 'warn');
          next(true);
        }
      }, 1500);
    }
  });
  audio.addEventListener('loadedmetadata', updateProgress);
  audio.addEventListener('durationchange', updateProgress);
  audio.addEventListener('timeupdate', updateProgress);
  audio.addEventListener('ended', function () {
    if (!settings.autoplayNext && repeatMode === 'off') { setPlayingUI(false); return; }
    next(false);
  });

  $('#playBtn').onclick = togglePlay;
  $('#pbExpand').onclick = openSheet;
  $('#prevBtn').onclick = prev;
  $('#nextBtn').onclick = next;
  $('#pbLike').onclick = function () {
    if (!current) { toast('Nothing playing', 'err'); return; }
    toggleLike(current);
  };
  $('#shuffleBtn').onclick = function () {
    shuffleOn = !shuffleOn;
    this.setAttribute('aria-pressed', shuffleOn ? 'true' : 'false');
    this.classList.toggle('on', shuffleOn);
    buildOrder();
    status(shuffleOn ? 'SHUFFLE ON' : 'SHUFFLE OFF', '');
  };
  $('#repeatBtn').onclick = function () {
    repeatMode = repeatMode === 'off' ? 'all' : (repeatMode === 'all' ? 'one' : 'off');
    this.setAttribute('aria-pressed', repeatMode !== 'off' ? 'true' : 'false');
    this.classList.toggle('on', repeatMode !== 'off');
    this.setAttribute('aria-label', 'Repeat ' + repeatMode);
    this.querySelector('.rep-one').hidden = repeatMode !== 'one';
    status('REPEAT ' + repeatMode.toUpperCase(), '');
  };
  var seek = $('#seek');
  seek.addEventListener('input', function () {
    var d = audio.duration || 0;
    if (!d) return;
    audio.currentTime = (parseFloat(seek.value) / 100) * d;
    setRangeFill(seek, parseFloat(seek.value));
  });
  var vol = $('#vol');
  vol.addEventListener('input', function () {
    settings.volume = parseFloat(vol.value);
    audio.volume = settings.volume;
    audio.muted = false;
    setRangeFill(vol, settings.volume * 100);
    saveSettings();
    updateMuteIcon();
  });
  $('#muteBtn').onclick = function () {
    audio.muted = !audio.muted;
    updateMuteIcon();
    status(audio.muted ? 'MUTED' : 'UNMUTED', '');
  };
  function updateMuteIcon() {
    var w = $('#volWaves');
    if (w) w.style.opacity = (audio.muted || settings.volume === 0) ? '.25' : '1';
  }

  if ('mediaSession' in navigator) {
    try {
      navigator.mediaSession.setActionHandler('play', function () { audio.play().catch(function () {}); });
      navigator.mediaSession.setActionHandler('pause', function () { audio.pause(); });
      navigator.mediaSession.setActionHandler('previoustrack', prev);
      navigator.mediaSession.setActionHandler('nexttrack', function () { next(true); });
    } catch (e) {}
  }

  // ---------------- queue drawer ----------------
  var queueDrawer = $('#queueDrawer');
  function openQueue() {
    renderQueueList();
    queueDrawer.classList.add('open');
    queueDrawer.setAttribute('aria-hidden', 'false');
    $('#queueBtn').setAttribute('aria-pressed', 'true');
  }
  function closeQueue() {
    queueDrawer.classList.remove('open');
    queueDrawer.setAttribute('aria-hidden', 'true');
    $('#queueBtn').setAttribute('aria-pressed', 'false');
  }
  function toggleQueue() {
    if (queueDrawer.classList.contains('open')) closeQueue(); else openQueue();
  }
  $('#queueBtn').onclick = toggleQueue;
  $('#queueClose').onclick = closeQueue;
  $('#queueClear').onclick = function () {
    if (!queue.length) return;
    confirmModal('Clear the queue?', 'This removes all ' + queue.length + ' tracks from the queue. Playback stops.', 'Clear queue', function () {
      audio.pause();
      queue = [];
      qi = -1;
      current = null;
      order = [];
      playerbar.hidden = true;
      renderQueueBadge();
      renderQueueList();
      renderSidePlaylists();
      if (isQueueRoute()) renderView();
      toast('Queue cleared', 'ok');
    });
  };
  function renderQueueList() {
    var list = $('#queueList');
    if (!list) return;
    $('#queueCount').textContent = queue.length ? '(' + queue.length + ')' : '';
    if (!queue.length) {
      list.innerHTML = '<div class="queue-empty">Queue is empty.<br>Play something to fill it up.</div>';
      return;
    }
    list.innerHTML = '';
    queue.forEach(function (t, i) {
      list.appendChild(queueItem(t, i));
    });
  }
  function queueItem(t, i) {
    var row = document.createElement('div');
    row.className = 'queue-item' + (i === qi ? ' now' : '');
    var art = t.thumb
      ? '<img loading="lazy" src="' + esc(t.thumb) + '" alt="">'
      : '<span class="art-fallback">' + esc(initials(t.title)) + '</span>';
    row.innerHTML =
      '<button class="track-art" type="button" aria-label="Play ' + esc(t.title) + '">' + art +
        '<span class="row-play">' + ICONS.play + '</span></button>' +
      '<div class="track-main"><div class="track-title">' + esc(t.title) + '</div>' +
        '<div class="track-sub">' + esc(t.artist) + '</div></div>' +
      '<div class="q-order">' +
        (i === qi ? '<span class="q-idx">NOW</span>' :
          '<button class="icon-btn q-up" aria-label="Move up" type="button">' + ICONS.up + '</button>' +
          '<button class="icon-btn q-down" aria-label="Move down" type="button">' + ICONS.down + '</button>') +
      '</div>';
    row.querySelector('.track-art').onclick = function () { jumpTo(i); };
    var up = row.querySelector('.q-up');
    var down = row.querySelector('.q-down');
    if (up) up.onclick = function () { moveQueue(i, i - 1); };
    if (down) down.onclick = function () { moveQueue(i, i + 1); };
    return row;
  }
  function jumpTo(i) {
    if (i === qi) { togglePlay(); return; }
    qi = i;
    buildOrder();
    renderQueueBadge();
    loadTrack(queue[qi], true);
    renderQueueList();
  }
  function moveQueue(from, to) {
    if (to < 0 || to >= queue.length) return;
    var item = queue.splice(from, 1)[0];
    queue.splice(to, 0, item);
    if (qi === from) qi = to;
    else if (from < qi && to >= qi) qi--;
    else if (from > qi && to <= qi) qi++;
    buildOrder();
    renderQueueBadge();
    renderQueueList();
    if (isQueueRoute()) renderView();
  }

  // ---------------- expanded player sheet ----------------
  var sheetRefs = null;
  function openSheet() {
    if (!current) { toast('Nothing playing', 'err'); return; }
    var el = document.createElement('div');
    el.className = 'player-sheet';
    el.id = 'playerSheet';
    var art = current.thumb
      ? '<img src="' + esc(current.thumb) + '" alt="">'
      : '<span class="art-fallback">' + esc(initials(current.title)) + '</span>';
    el.innerHTML =
      '<div class="sheet-top">' +
        '<button class="icon-btn" id="sheetClose" aria-label="Close player" type="button">' +
          '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="6" y1="6" x2="18" y2="18"/><line x1="18" y1="6" x2="6" y2="18"/></svg>' +
        '</button>' +
        '<span class="chip">' + esc(current.provider) + '</span>' +
      '</div>' +
      '<div class="sheet-art">' + art + '</div>' +
      '<div class="sheet-title">' + esc(current.title) + '</div>' +
      '<div class="sheet-artist">' + esc(current.artist) + '</div>' +
      '<div class="sheet-seek">' +
        '<input id="sheetSeek" class="seek-range" type="range" min="0" max="100" step="0.1" value="0" aria-label="Seek">' +
        '<div class="sheet-times"><span id="sheetCur">0:00</span><span id="sheetDur">0:00</span></div>' +
      '</div>' +
      '<div class="sheet-ctrls">' +
        '<button class="icon-btn" id="sheetPrev" aria-label="Previous" type="button">' +
          '<svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor"><path d="M7 6h2v12H7zM19 6v12l-9-6z"/></svg></button>' +
        '<button class="pb-play" id="sheetPlay" aria-label="Play" type="button">' + ICONS.play + '</button>' +
        '<button class="icon-btn" id="sheetNext" aria-label="Next" type="button">' +
          '<svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor"><path d="M17 6h-2v12h2zM5 6l9 6-9 6z"/></svg></button>' +
      '</div>';
    document.body.appendChild(el);
    sheetRefs = {
      seek: $('#sheetSeek'), cur: $('#sheetCur'), dur: $('#sheetDur'),
      play: $('#sheetPlay')
    };
    sheetRefs.play.onclick = togglePlay;
    $('#sheetPrev').onclick = prev;
    $('#sheetNext').onclick = next;
    $('#sheetClose').onclick = closeSheet;
    sheetRefs.seek.addEventListener('input', function () {
      var d = audio.duration || 0;
      if (!d) return;
      audio.currentTime = (parseFloat(sheetRefs.seek.value) / 100) * d;
    });
    progressHooks.push(function (t, d, pct) {
      if (!sheetRefs) return;
      sheetRefs.seek.value = String(pct);
      setRangeFill(sheetRefs.seek, pct);
      sheetRefs.cur.textContent = fmt(t);
      sheetRefs.dur.textContent = fmt(d);
    });
    syncSheet();
    updateProgress();
  }
  function syncSheet() {
    if (!sheetRefs) return;
    sheetRefs.play.innerHTML = playing ? ICONS.pause : ICONS.play;
    sheetRefs.play.setAttribute('aria-label', playing ? 'Pause' : 'Play');
  }
  function closeSheet() {
    var el = $('#playerSheet');
    if (el) el.remove();
    sheetRefs = null;
    progressHooks = [];
  }
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      if ($('#playerSheet')) closeSheet();
      else if (queueDrawer.classList.contains('open')) closeQueue();
      else closeSidebar();
    }
    var tag = (e.target.tagName || '').toLowerCase();
    if (tag === 'input' || tag === 'textarea' || e.metaKey || e.ctrlKey) return;
    if (e.code === 'Space' && current) { e.preventDefault(); togglePlay(); }
    if (e.key === '/') { e.preventDefault(); focusSearch(); }
    if (e.key === 'ArrowRight' && e.shiftKey) next(true);
    if (e.key === 'ArrowLeft' && e.shiftKey) prev();
    if (e.key.toLowerCase() === 'm') { audio.muted = !audio.muted; updateMuteIcon(); }
  });

  // ---------------- shared components ----------------
  function artBlock(t, sizeClass) {
    if (t.thumb) {
      return '<img loading="lazy" src="' + esc(t.thumb) + '" alt="' + esc(t.title) + ' artwork">';
    }
    return '<span class="art-fallback" aria-hidden="true">' + esc(initials(t.title)) + '</span>';
  }

  function cardEl(t, list, idx) {
    var el = document.createElement('article');
    el.className = 'card';
    el.style.animationDelay = ((idx % 10) * 40) + 'ms';
    el.innerHTML =
      '<div class="card-art" role="button" tabindex="0" aria-label="Play ' + esc(t.title) + ' by ' + esc(t.artist) + '">' +
        artBlock(t) +
        '<div class="card-art-shade"></div>' +
        '<span class="card-acts">' +
          '<button class="icon-btn like-btn like-btn-fire" data-key="' + esc(t.key) + '" aria-label="Like" aria-pressed="' + (isLiked(t) ? 'true' : 'false') + '" type="button">' + ICONS.heart + '</button>' +
        '</span>' +
        '<span class="card-play" aria-hidden="true">' + ICONS.play + '</span>' +
      '</div>' +
      '<div class="card-title">' + esc(t.title) + '</div>' +
      '<div class="card-sub">' + esc(t.artist) + ' &middot; ' + esc(t.duration ? fmt(t.duration) : t.provider) + '</div>' +
      '<div class="card-foot">' +
        '<button class="icon-btn ghost add-pl" aria-label="Add to playlist" type="button">' + ICONS.plus + '</button>' +
        '<button class="icon-btn ghost queue-next" aria-label="Play next" type="button">' + ICONS.queueNext + '</button>' +
        '<button class="icon-btn ghost open-info" aria-label="Track details" type="button">' + ICONS.info + '</button>' +
        '<span class="chip chip-provider">' + esc(t.provider) + '</span>' +
      '</div>';
    var art = el.querySelector('.card-art');
    art.onclick = function (e) {
      if (e.target.closest('.like-btn')) return;
      playList(list, idx);
    };
    art.onkeydown = function (e) {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); playList(list, idx); }
    };
    el.querySelector('.like-btn-fire').onclick = function (e) { e.stopPropagation(); toggleLike(t); updateLikeButton(); };
    el.querySelector('.add-pl').onclick = function () { openAddToPlaylist(t); };
    el.querySelector('.queue-next').onclick = function () { playNext(t); };
    el.querySelector('.open-info').onclick = function () { openTrackModal(t); };
    return el;
  }

  function trackRowEl(t, list, idx) {
    var el = document.createElement('div');
    el.className = 'track-row' + (current && current.key === t.key ? ' playing' : '');
    el.innerHTML =
      '<button class="track-art" type="button" aria-label="Play ' + esc(t.title) + '">' + artBlock(t) +
        '<span class="row-play">' + ICONS.play + '</span></button>' +
      '<div class="track-main">' +
        '<div class="track-title">' + esc(t.title) + '</div>' +
        '<div class="track-sub">' + esc(t.artist) + ' &middot; ' + esc(t.provider) +
          (t.tags && t.tags.length ? ' &middot; ' + esc(t.tags.slice(0, 2).join(', ')) : '') + '</div>' +
      '</div>' +
      '<div class="track-acts">' +
        '<span class="track-dur">' + fmt(t.duration) + '</span>' +
        '<button class="icon-btn like-btn like-btn-fire" data-key="' + esc(t.key) + '" aria-label="Like" aria-pressed="' + (isLiked(t) ? 'true' : 'false') + '" type="button">' + ICONS.heart + '</button>' +
        '<button class="icon-btn ghost add-pl" aria-label="Add to playlist" type="button">' + ICONS.plus + '</button>' +
        '<button class="icon-btn ghost queue-next" aria-label="Play next" type="button">' + ICONS.queueNext + '</button>' +
        '<button class="icon-btn ghost copy-id" aria-label="Copy track ID" type="button">' + ICONS.copy + '</button>' +
        '<button class="icon-btn ghost open-info" aria-label="Track details" type="button">' + ICONS.info + '</button>' +
      '</div>';
    el.querySelector('.track-art').onclick = function () { playList(list, idx); };
    el.querySelector('.track-title').onclick = function () { playList(list, idx); };
    el.querySelector('.track-title').style.cursor = 'pointer';
    el.querySelector('.like-btn-fire').onclick = function () { toggleLike(t); updateLikeButton(); };
    el.querySelector('.add-pl').onclick = function () { openAddToPlaylist(t); };
    el.querySelector('.queue-next').onclick = function () { playNext(t); };
    el.querySelector('.copy-id').onclick = function () { copyText(t.id); };
    el.querySelector('.open-info').onclick = function () { openTrackModal(t); };
    return el;
  }
  function copyText(v) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(v).then(function () { toast('Copied: ' + v, 'ok'); }, function () { toast('Copy failed', 'err'); });
    } else {
      toast('Copied: ' + v, 'ok');
    }
  }
  function playNext(t) {
    if (!queue.length || qi < 0) { playList([t], 0); return; }
    queue.splice(qi + 1, 0, snap(t));
    buildOrder();
    renderQueueBadge();
    renderQueueList();
    toast('Playing next: ' + t.title, 'ok');
  }
  function openAddToPlaylist(t) {
    var body = playlists.length
      ? '<div class="modal-list">' + playlists.map(function (p) {
          return '<button class="cat-chip pl-pick" data-id="' + p.id + '" type="button">' + esc(p.name) + ' <span class="muted">(' + p.tracks.length + ')</span></button>';
        }).join('') + '</div>'
      : '<p class="modal-sub">You have no playlists yet.</p>';
    openModal(
      '<h3>Add to playlist</h3><p class="modal-sub">' + esc(t.title) + ' &middot; ' + esc(t.artist) + '</p>' + body +
      '<div class="modal-acts"><button class="btn btn-dim" id="mCancel" type="button">Cancel</button>' +
      '<button class="btn" id="mNew" type="button">New playlist</button></div>'
    );
    $('#mCancel').onclick = closeModal;
    $('#mNew').onclick = function () {
      promptModal('New playlist', 'Give it a name.', 'My playlist', '', 'Create', function (name) {
        var pl = createPlaylist(name);
        addToPlaylist(pl.id, t);
        toast('Added to ' + name, 'ok');
      });
    };
    $$('.pl-pick', modalEl).forEach(function (b) {
      b.onclick = function () {
        var id = b.getAttribute('data-id');
        addToPlaylist(id, t);
        closeModal();
        toast('Added to ' + (findPlaylist(id) || {}).name, 'ok');
      };
    });
  }

  function openTrackModal(t) {
    var art = t.thumb
      ? '<img src="' + esc(t.thumb) + '" alt="' + esc(t.title) + ' artwork">'
      : '<span class="art-fallback">' + esc(initials(t.title)) + '</span>';
    var tagChips = (t.tags || []).slice(0, 5).map(function (x) {
      return '<span class="chip">' + esc(x) + '</span>';
    }).join('');
    var plays = counts[t.key] || 0;
    openModal(
      '<div class="detail">' +
        '<div class="detail-art">' + art + '</div>' +
        '<div class="detail-info">' +
          '<h3>' + esc(t.title) + '</h3>' +
          '<p class="modal-sub">' + esc(t.artist) + ' &middot; ' + esc(t.provider) +
            (t.duration ? ' &middot; ' + fmt(t.duration) : '') + '</p>' +
          '<div class="chip-row">' + (tagChips || '<span class="chip">' + esc(t.id) + '</span>') + '</div>' +
          '<p class="modal-sub">' + plays + ' play' + (plays === 1 ? '' : 's') + ' on this device &middot; ID ' + esc(t.id) + '</p>' +
        '</div>' +
      '</div>' +
      '<div class="modal-acts detail-acts">' +
        '<button class="btn dm-play" type="button">' + ICONS.play + ' Play</button>' +
        '<button class="icon-btn dm-like' + (isLiked(t) ? ' liked' : '') + '" aria-label="Like" aria-pressed="' + (isLiked(t) ? 'true' : 'false') + '" type="button">' + ICONS.heart + '</button>' +
        '<button class="icon-btn dm-queue" aria-label="Play next" type="button">' + ICONS.queueNext + '</button>' +
        '<button class="icon-btn dm-pl" aria-label="Add to playlist" type="button">' + ICONS.plus + '</button>' +
        '<button class="icon-btn dm-stream" aria-label="Copy stream link" title="Copy stream link" type="button">' + ICONS.link + '</button>' +
        '<button class="icon-btn dm-share" aria-label="Copy share link" title="Copy share link" type="button">' + ICONS.copy + '</button>' +
      '</div>'
    );
    $('.dm-play', modalEl).onclick = function () { closeModal(); playList([t], 0); };
    $('.dm-like', modalEl).onclick = function () {
      toggleLike(t);
      var on = isLiked(t);
      var b = $('.dm-like', modalEl);
      b.classList.toggle('liked', on);
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
    };
    $('.dm-queue', modalEl).onclick = function () { closeModal(); playNext(t); };
    $('.dm-pl', modalEl).onclick = function () { openAddToPlaylist(t); };
    $('.dm-stream', modalEl).onclick = function () {
      copyText(location.origin + t.url);
    };
    $('.dm-share', modalEl).onclick = function () {
      copyText(location.origin + '/#/search?q=' + encodeURIComponent(t.title + ' ' + t.artist));
    };
  }

  var sleepUntil = 0;
  var sleepMins = 0;
  var sleepTick = null;
  function sleepLabel() {
    if (!sleepUntil) return 'Playback keeps going until you stop it.';
    var mins = Math.max(0, Math.round((sleepUntil - Date.now()) / 60000));
    return mins ? 'Pauses playback in about ' + mins + ' min' : 'Pausing...';
  }
  function updateSleepLabels() {
    var el = $('#sleepLabel');
    if (el) el.textContent = sleepLabel();
    $$('#sleepSeg .seg-btn').forEach(function (b) {
      b.classList.toggle('active', parseInt(b.getAttribute('data-min'), 10) === sleepMins);
    });
  }
  function setSleep(mins) {
    sleepMins = mins;
    if (!mins) {
      sleepUntil = 0;
      clearInterval(sleepTick);
      sleepTick = null;
      toast('Sleep timer off', 'ok');
    } else {
      sleepUntil = Date.now() + mins * 60000;
      if (!sleepTick) {
        sleepTick = setInterval(function () {
          if (sleepUntil && Date.now() >= sleepUntil) {
            audio.pause();
            status('SLEEP TIMER', 'warn');
            toast('Sleep timer: playback paused', 'ok');
            setSleep(0);
          } else {
            updateSleepLabels();
          }
        }, 15000);
      }
      toast('Sleep timer: ' + mins + ' min', 'ok');
    }
    updateSleepLabels();
  }

  function sectionEl(title, linkHref, linkText) {
    var s = document.createElement('section');
    s.className = 'section';
    s.innerHTML =
      '<div class="section-head"><h2 class="section-title">' + title + '</h2>' +
      (linkHref ? '<a class="section-link" href="' + linkHref + '">' + esc(linkText || 'See all') + '</a>' : '') +
      '</div>';
    return s;
  }
  function rowScroller() {
    var d = document.createElement('div');
    d.className = 'row-scroller';
    return d;
  }
  function gridCards() {
    var d = document.createElement('div');
    d.className = 'grid-cards';
    return d;
  }
  function skeletonCards(n, grid) {
    var wrap = grid ? gridCards() : rowScroller();
    for (var i = 0; i < n; i++) {
      var c = document.createElement('div');
      c.className = 'sk-card';
      c.innerHTML = '<div class="skeleton sk-art"></div><div class="skeleton sk-line"></div><div class="skeleton sk-line sk-w60"></div>';
      wrap.appendChild(c);
    }
    return wrap;
  }
  function skeletonRows(n) {
    var wrap = document.createElement('div');
    wrap.className = 'track-list';
    for (var i = 0; i < n; i++) {
      var r = document.createElement('div');
      r.className = 'skeleton sk-row';
      wrap.appendChild(r);
    }
    return wrap;
  }
  function stateBlock(iconSvg, title, note, retryFn) {
    var d = document.createElement('div');
    d.className = 'state-block';
    d.innerHTML = (iconSvg || ICONS.music) + '<h3>' + esc(title) + '</h3><p>' + esc(note) + '</p>';
    if (retryFn) {
      var b = document.createElement('button');
      b.className = 'btn btn-dim btn-s';
      b.type = 'button';
      b.textContent = 'Retry';
      b.onclick = retryFn;
      d.appendChild(b);
    }
    return d;
  }
  function viewHead(eyebrow, title, sub) {
    var d = document.createElement('div');
    d.className = 'view-head';
    d.innerHTML =
      (eyebrow ? '<p class="eyebrow">' + esc(eyebrow) + '</p>' : '') +
      '<h1 class="view-title">' + esc(title) + '</h1>' +
      (sub ? '<p class="view-sub">' + esc(sub) + '</p>' : '');
    return d;
  }

  // ---------------- views ----------------
  var view = $('#view');

  function renderLoadingCards(n, grid) {
    view.innerHTML = '';
    var inner = document.createElement('div');
    inner.className = 'view-inner';
    inner.appendChild(skeletonCards(n || 8, grid));
    view.appendChild(inner);
  }

  var moods = [
    { name: 'Relax', q: 'relaxing music', from: '#1b2430', to: '#0f151c' },
    { name: 'Sad', q: 'sad songs', from: '#22202c', to: '#12111a' },
    { name: 'Party', q: 'party hits', from: '#2a1f18', to: '#170f0a' },
    { name: 'Romantic', q: 'romantic love songs', from: '#2a1a22', to: '#170d12' },
    { name: 'Energetic', q: 'workout energy music', from: '#16262a', to: '#0b1417' },
    { name: 'Chill', q: 'chill lofi beats', from: '#1c2026', to: '#0f1216' },
    { name: 'Focus', q: 'study focus instrumental', from: '#1a1a26', to: '#0e0e18' },
    { name: 'Devotional', q: 'devotional bhajan', from: '#2a2416', to: '#171208' }
  ];

  function homeView() {
    var inner = document.createElement('div');
    inner.className = 'view-inner';
    inner.innerHTML =
      '<div class="view-head"><p class="eyebrow">IOTA AUDIO</p>' +
      '<h1 class="view-title">Discover your next favourite</h1>' +
      '<p class="view-sub">Provider-backed streaming across YouTube, Deezer and Apple Music - plus the local catalog.</p></div>';
    view.innerHTML = '';
    view.appendChild(inner);

    var heroSlot = document.createElement('div');
    heroSlot.className = 'hero';
    heroSlot.innerHTML = '<div class="hero-stage"><div class="state-block"><div class="spinner"></div><p>Loading featured tracks...</p></div></div>';
    inner.appendChild(heroSlot);

    loadHero(heroSlot);

    var trendingSec = sectionEl('Trending now', '#/songs', 'Browse all');
    trendingSec.appendChild(skeletonCards(6));
    inner.appendChild(trendingSec);
    fillRow(trendingSec, API.trending(12), 'Trending is unavailable right now.');

    var freshSec = sectionEl('Fresh mix', null, null);
    freshSec.appendChild(skeletonCards(6));
    inner.appendChild(freshSec);
    fillRow(freshSec, API.random(12), 'Could not load the shuffle.');

    var tagSec = sectionEl('Browse by tag', '#/moods', 'All tags');
    var chips = document.createElement('div');
    chips.className = 'chip-scroller';
    chips.innerHTML = '<span class="chip">Loading tags...</span>';
    tagSec.appendChild(chips);
    inner.appendChild(tagSec);
    loadTagChips(chips);

    if (recent.length) {
      var recSec = sectionEl('Pick up where you left off', '#/recent', 'History');
      recSec.appendChild(trackListEl(recent.slice(0, 8)));
      inner.appendChild(recSec);
    }
  }

  function loadHero(slot) {
    API.random(8).then(function (data) {
      var tracks = (data.results || []).map(function (s) { return norm(s, false); });
      if (!tracks.length) throw new Error('empty');
      buildHero(slot, tracks);
    }).catch(function () {
      slot.innerHTML = '<div class="hero-stage"><div class="state-block">' + ICONS.music +
        '<h3>No featured tracks</h3><p>The catalog did not return anything for the hero row.</p></div></div>';
    });
  }

  function buildHero(slot, tracks) {
    var stage = document.createElement('div');
    stage.className = 'hero-stage';
    var slides = tracks.map(function (t, i) {
      var s = document.createElement('div');
      s.className = 'hero-slide' + (i === 0 ? ' active' : '');
      s.setAttribute('role', 'group');
      s.setAttribute('aria-roledescription', 'slide');
      s.setAttribute('aria-label', (i + 1) + ' of ' + tracks.length + ': ' + t.title);
      s.innerHTML =
        '<div class="hero-art">' + artBlock(t) + '</div>' +
        '<div class="hero-info">' +
          '<span class="hero-tag">Featured</span>' +
          '<h2 class="hero-title">' + esc(t.title) + '</h2>' +
          '<p class="hero-artist">' + esc(t.artist) + '</p>' +
          '<p class="hero-meta">' + esc(t.provider) + (t.duration ? ' &middot; ' + fmt(t.duration) : '') +
            (t.tags && t.tags.length ? ' &middot; ' + esc(t.tags.slice(0, 3).join(' / ')) : '') + '</p>' +
          '<div class="hero-actions">' +
            '<button class="btn hero-play" type="button">' + ICONS.play + ' Play</button>' +
            '<button class="icon-btn like-btn like-btn-fire" data-key="' + esc(t.key) + '" aria-label="Like" aria-pressed="' + (isLiked(t) ? 'true' : 'false') + '" type="button">' + ICONS.heart + '</button>' +
          '</div>' +
        '</div>';
      s.querySelector('.hero-play').onclick = function () { playList(tracks, i); };
      s.querySelector('.like-btn-fire').onclick = function () { toggleLike(t); updateLikeButton(); };
      return s;
    });
    slides.forEach(function (s) { stage.appendChild(s); });

    var prevB = document.createElement('button');
    prevB.className = 'hero-arrow prev';
    prevB.type = 'button';
    prevB.setAttribute('aria-label', 'Previous slide');
    prevB.innerHTML = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 6l-6 6 6 6"/></svg>';
    var nextB = document.createElement('button');
    nextB.className = 'hero-arrow next';
    nextB.type = 'button';
    nextB.setAttribute('aria-label', 'Next slide');
    nextB.innerHTML = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6l6 6-6 6"/></svg>';
    stage.appendChild(prevB);
    stage.appendChild(nextB);

    var dots = document.createElement('div');
    dots.className = 'hero-dots';
    tracks.forEach(function (_, i) {
      var d = document.createElement('button');
      d.className = 'hero-dot' + (i === 0 ? ' active' : '');
      d.type = 'button';
      d.setAttribute('aria-label', 'Go to slide ' + (i + 1));
      d.onclick = function () { go(i); };
      dots.appendChild(d);
    });
    stage.appendChild(dots);

    var cur = 0;
    var timer = null;
    function go(i) {
      cur = (i + tracks.length) % tracks.length;
      slides.forEach(function (s, j) { s.classList.toggle('active', j === cur); });
      $$('.hero-dot', dots).forEach(function (d, j) { d.classList.toggle('active', j === cur); });
    }
    function restart() {
      clearInterval(timer);
      timer = setInterval(function () { if (!document.hidden) go(cur + 1); }, 7000);
    }
    prevB.onclick = function () { go(cur - 1); restart(); };
    nextB.onclick = function () { go(cur + 1); restart(); };
    stage.addEventListener('mouseenter', function () { clearInterval(timer); });
    stage.addEventListener('focusin', function () { clearInterval(timer); });
    stage.addEventListener('mouseleave', restart);
    stage.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight') { go(cur + 1); restart(); }
      if (e.key === 'ArrowLeft') { go(cur - 1); restart(); }
    });
    restart();

    slot.innerHTML = '';
    slot.appendChild(stage);
  }

  function fillRow(section, promise, errMsg) {
    var old = section.querySelector('.row-scroller');
    promise.then(function (data) {
      var tracks = (data.results || []).map(function (s) { return norm(s, false); });
      var scroller = rowScroller();
      if (!tracks.length) {
        old.replaceWith(stateBlock(ICONS.music, 'Nothing here yet', errMsg));
        return;
      }
      tracks.forEach(function (t, i) { scroller.appendChild(cardEl(t, tracks, i)); });
      old.replaceWith(scroller);
    }).catch(function () {
      old.replaceWith(stateBlock(ICONS.music, 'Could not load', errMsg, function () { renderView(); }));
    });
  }

  function loadTagChips(container) {
    Promise.all([API.songs(1, 100), API.songs(2, 100)]).then(function (pages) {
      var counts = {};
      pages.forEach(function (p) {
        (p.results || []).forEach(function (s) {
          (s.tags || []).forEach(function (tg) { counts[tg] = (counts[tg] || 0) + 1; });
        });
      });
      var tags = Object.keys(counts).sort(function (a, b) { return counts[b] - counts[a]; }).slice(0, 14);
      container.innerHTML = '';
      if (!tags.length) {
        container.innerHTML = '<span class="chip">No tags in the catalog</span>';
        return;
      }
      tags.forEach(function (tg) {
        var b = document.createElement('a');
        b.className = 'cat-chip';
        b.href = '#/tag/' + encodeURIComponent(tg);
        b.textContent = tg;
        container.appendChild(b);
      });
    }).catch(function () {
      container.innerHTML = '<span class="chip">Tags unavailable</span>';
    });
  }

  function trackListEl(tracks) {
    var list = document.createElement('div');
    list.className = 'track-list';
    tracks.forEach(function (t, i) { list.appendChild(trackRowEl(t, tracks, i)); });
    return list;
  }

  function songsView(params) {
    var page = parseInt(params.page || '1', 10) || 1;
    renderLoadingCards(12, true);
    var inner = document.createElement('div');
    inner.className = 'view-inner';
    view.innerHTML = '';
    view.appendChild(inner);
    inner.appendChild(viewHead('Catalog', 'All Songs', 'Every track indexed in the local catalog, streamed with HTTP Range support.'));
    var holder = document.createElement('div');
    inner.appendChild(holder);
    holder.appendChild(skeletonCards(12, true));
    API.songs(page, 48).then(function (data) {
      var tracks = (data.results || []).map(function (s) { return norm(s, false); });
      holder.innerHTML = '';
      if (!tracks.length) {
        holder.appendChild(stateBlock(ICONS.music, 'Catalog is empty', 'No songs are indexed right now.'));
        return;
      }
      var grid = gridCards();
      tracks.forEach(function (t, i) { grid.appendChild(cardEl(t, tracks, i)); });
      holder.appendChild(grid);
      var pager = document.createElement('div');
      pager.className = 'pager';
      var totalPages = data.total_pages || 1;
      pager.innerHTML =
        '<button class="btn btn-dim btn-s" id="pgenPrev" type="button"' + (page <= 1 ? ' disabled' : '') + '>Prev</button>' +
        '<span class="muted">Page ' + page + ' of ' + totalPages + ' - ' + (data.total_songs || tracks.length) + ' songs</span>' +
        '<button class="btn btn-dim btn-s" id="pgenNext" type="button"' + (page >= totalPages ? ' disabled' : '') + '>Next</button>';
      holder.appendChild(pager);
      var p1 = $('#pgenPrev'), p2 = $('#pgenNext');
      if (p1) p1.onclick = function () { location.hash = '#/songs?page=' + (page - 1); };
      if (p2) p2.onclick = function () { location.hash = '#/songs?page=' + (page + 1); };
    }).catch(function () {
      holder.innerHTML = '';
      holder.appendChild(stateBlock(ICONS.music, 'Could not load the catalog', 'The catalog endpoint did not respond.', function () { songsView(params); }));
    });
  }

  function searchView(params) {
    var q = (params.q || '').trim();
    var inner = document.createElement('div');
    inner.className = 'view-inner';
    view.innerHTML = '';
    view.appendChild(inner);
    inner.appendChild(viewHead('Search', q ? 'Results for "' + q + '"' : 'Search', 'Live provider results plus local catalog matches.'));

    var tabs = document.createElement('div');
    tabs.className = 'chip-scroller';
    tabs.innerHTML =
      '<button class="cat-chip active" data-tab="live" type="button">Live providers</button>' +
      '<button class="cat-chip" data-tab="catalog" type="button">Catalog</button>';
    inner.appendChild(tabs);
    var holder = document.createElement('div');
    inner.appendChild(holder);
    var currentTab = 'live';

    function load(tab) {
      currentTab = tab;
      $$('.cat-chip', tabs).forEach(function (b) { b.classList.toggle('active', b.getAttribute('data-tab') === tab); });
      holder.innerHTML = '';
      if (!q) {
        holder.appendChild(stateBlock(ICONS.search, 'Start typing to search', 'Use the search bar above. Try Ctrl+K from anywhere.'));
        return;
      }
      holder.appendChild(skeletonRows(8));
      var promise = tab === 'live' ? API.live(q, 25) : API.catalogSearch(q, 30);
      promise.then(function (data) {
        var tracks = (data.results || []).map(function (s) { return norm(s, tab === 'live'); });
        holder.innerHTML = '';
        if (!tracks.length) {
          holder.appendChild(stateBlock(ICONS.search, 'No results',
            tab === 'live' ? 'No provider matches. Try different keywords or the Catalog tab.'
              : 'Nothing in the local catalog matched. Try the Live providers tab.'));
          return;
        }
        var meta = document.createElement('p');
        meta.className = 'view-sub';
        meta.style.margin = '4px 2px 12px';
        meta.textContent = tracks.length + ' track' + (tracks.length === 1 ? '' : 's') +
          (tab === 'live' ? ' from providers' + (data.elapsed_ms ? ' - ' + data.elapsed_ms + 'ms' : '') : ' in the catalog');
        holder.appendChild(meta);
        holder.appendChild(trackListEl(tracks));
      }).catch(function () {
        holder.innerHTML = '';
        holder.appendChild(stateBlock(ICONS.search, 'Search failed',
          tab === 'live' ? 'The live search provider did not respond.' : 'The catalog search did not respond.',
          function () { load(tab); }));
      });
    }
    $$('.cat-chip', tabs).forEach(function (b) {
      b.onclick = function () { load(b.getAttribute('data-tab')); };
    });
    load('live');
  }

  function moodsView() {
    var inner = document.createElement('div');
    inner.className = 'view-inner';
    view.innerHTML = '';
    view.appendChild(inner);
    inner.appendChild(viewHead('Browse', 'Moods & Tags', 'Mood presets run a real provider search. Tags come from the local catalog.'));

    var moodSec = sectionEl('Moods', null, null);
    var grid = document.createElement('div');
    grid.className = 'mood-grid';
    moods.forEach(function (m) {
      var b = document.createElement('button');
      b.className = 'mood-card';
      b.type = 'button';
      b.style.background = 'linear-gradient(140deg, ' + m.from + ', ' + m.to + ')';
      b.innerHTML = '<span>' + esc(m.name) + '</span>' + ICONS.music;
      b.onclick = function () { location.hash = '#/search?q=' + encodeURIComponent(m.q); };
      grid.appendChild(b);
    });
    moodSec.appendChild(grid);
    inner.appendChild(moodSec);

    var tagSec = sectionEl('Catalog tags', null, null);
    var chips = document.createElement('div');
    chips.className = 'chip-scroller';
    chips.innerHTML = '<span class="chip">Loading tags...</span>';
    tagSec.appendChild(chips);
    inner.appendChild(tagSec);
    loadTagChips(chips);
  }

  function tagView(tag) {
    var inner = document.createElement('div');
    inner.className = 'view-inner';
    view.innerHTML = '';
    view.appendChild(inner);
    inner.appendChild(viewHead('Tag', tag, 'Catalog tracks tagged "' + tag + '".'));
    var holder = document.createElement('div');
    inner.appendChild(holder);
    holder.appendChild(skeletonCards(8, true));
    Promise.all([API.songs(1, 100), API.songs(2, 100)]).then(function (pages) {
      var all = [];
      pages.forEach(function (p) {
        (p.results || []).forEach(function (s) {
          if ((s.tags || []).indexOf(tag) !== -1) all.push(norm(s, false));
        });
      });
      holder.innerHTML = '';
      if (!all.length) {
        holder.appendChild(stateBlock(ICONS.music, 'No tracks with this tag', 'Try another tag.',
          function () { location.hash = '#/moods'; }));
        return;
      }
      var playAll = document.createElement('div');
      playAll.className = 'hero-actions';
      playAll.style.margin = '0 0 16px';
      var pb = document.createElement('button');
      pb.className = 'btn';
      pb.type = 'button';
      pb.innerHTML = ICONS.play + ' Play all';
      pb.onclick = function () { playList(all, 0); };
      var sb = document.createElement('button');
      sb.className = 'btn btn-dim';
      sb.type = 'button';
      sb.textContent = 'Shuffle';
      sb.onclick = function () { shuffleOn = true; $('#shuffleBtn').setAttribute('aria-pressed', 'true'); $('#shuffleBtn').classList.add('on'); playList(all, Math.floor(Math.random() * all.length)); };
      playAll.appendChild(pb);
      playAll.appendChild(sb);
      holder.appendChild(playAll);
      holder.appendChild(trackListEl(all));
    }).catch(function () {
      holder.innerHTML = '';
      holder.appendChild(stateBlock(ICONS.music, 'Could not load tag', 'The catalog did not respond.', function () { tagView(tag); }));
    });
  }

  function likedView() {
    var tracks = likedTracks();
    var inner = document.createElement('div');
    inner.className = 'view-inner';
    view.innerHTML = '';
    view.appendChild(inner);
    inner.appendChild(viewHead('Your library', 'Liked Songs', 'Saved in this browser only - no account required.'));
    if (!tracks.length) {
      inner.appendChild(stateBlock(ICONS.heart, 'No liked songs yet', 'Tap the heart on any track to save it here.'));
      return;
    }
    var bar = document.createElement('div');
    bar.className = 'hero-actions';
    bar.style.margin = '0 0 16px';
    var pb = document.createElement('button');
    pb.className = 'btn';
    pb.type = 'button';
    pb.innerHTML = ICONS.play + ' Play all';
    pb.onclick = function () { playList(tracks, 0); };
    var sb = document.createElement('button');
    sb.className = 'btn btn-dim';
    sb.type = 'button';
    sb.innerHTML = ICONS.shuffle + ' Shuffle';
    sb.onclick = function () {
      shuffleOn = true;
      $('#shuffleBtn').setAttribute('aria-pressed', 'true');
      $('#shuffleBtn').classList.add('on');
      playList(tracks, Math.floor(Math.random() * tracks.length));
    };
    var cb = document.createElement('button');
    cb.className = 'btn btn-danger btn-s';
    cb.type = 'button';
    cb.textContent = 'Clear';
    cb.onclick = function () {
      confirmModal('Clear liked songs?', 'This removes all ' + tracks.length + ' liked tracks from this browser.', 'Clear', function () {
        liked = {};
        saveLiked();
        renderView();
        toast('Liked songs cleared', 'ok');
      });
    };
    bar.appendChild(pb);
    bar.appendChild(sb);
    bar.appendChild(cb);
    inner.appendChild(bar);
    inner.appendChild(trackListEl(tracks));
  }

  function recentView() {
    var inner = document.createElement('div');
    inner.className = 'view-inner';
    view.innerHTML = '';
    view.appendChild(inner);
    inner.appendChild(viewHead('Your library', 'Recently Played', 'Recorded on this device as you listen.'));
    if (!recent.length) {
      inner.appendChild(stateBlock(ICONS.music, 'Nothing played yet', 'Tracks you play will show up here.'));
      return;
    }
    var bar = document.createElement('div');
    bar.className = 'hero-actions';
    bar.style.margin = '0 0 16px';
    var pb = document.createElement('button');
    pb.className = 'btn';
    pb.type = 'button';
    pb.innerHTML = ICONS.play + ' Play all';
    pb.onclick = function () { playList(recent.slice(), 0); };
    var cb = document.createElement('button');
    cb.className = 'btn btn-danger btn-s';
    cb.type = 'button';
    cb.textContent = 'Clear history';
    cb.onclick = function () {
      confirmModal('Clear history?', 'This forgets your recently played tracks on this device.', 'Clear', function () {
        recent = [];
        saveRecent();
        renderView();
        toast('History cleared', 'ok');
      });
    };
    bar.appendChild(pb);
    bar.appendChild(cb);
    inner.appendChild(bar);
    inner.appendChild(trackListEl(recent));
  }

  function playlistsView() {
    var inner = document.createElement('div');
    inner.className = 'view-inner';
    view.innerHTML = '';
    view.appendChild(inner);
    var head = viewHead('Your library', 'Playlists', 'Create playlists and keep them in this browser.');
    inner.appendChild(head);
    var bar = document.createElement('div');
    bar.className = 'hero-actions';
    bar.style.margin = '0 0 16px';
    var nb = document.createElement('button');
    nb.className = 'btn';
    nb.type = 'button';
    nb.innerHTML = ICONS.plus + ' New playlist';
    nb.onclick = newPlaylistFlow;
    bar.appendChild(nb);
    inner.appendChild(bar);

    if (!playlists.length) {
      inner.appendChild(stateBlock(ICONS.music, 'No playlists yet', 'Create your first playlist and add tracks to it.'));
      return;
    }
    var grid = document.createElement('div');
    grid.className = 'grid-cards';
    playlists.forEach(function (pl) {
      grid.appendChild(playlistCardEl(pl));
    });
    inner.appendChild(grid);
  }

  function playlistCover(pl) {
    var covers = pl.tracks.slice(0, 4);
    if (!covers.length) return ICONS.music;
    var cells = covers.map(function (t) {
      return t.thumb
        ? '<img loading="lazy" src="' + esc(t.thumb) + '" alt="">'
        : '<span class="art-fallback" style="font-size:10px">' + esc(initials(t.title)) + '</span>';
    }).join('');
    return '<div class="pl-stack">' + cells + '</div>';
  }
  function playlistCardEl(pl) {
    var el = document.createElement('article');
    el.className = 'pl-card';
    el.innerHTML =
      '<div class="pl-cover" role="button" tabindex="0" aria-label="Open ' + esc(pl.name) + '">' + playlistCover(pl) + '</div>' +
      '<div class="pl-title">' + esc(pl.name) + '</div>' +
      '<div class="pl-sub">' + pl.tracks.length + ' track' + (pl.tracks.length === 1 ? '' : 's') + '</div>' +
      '<div class="pl-acts">' +
        '<button class="icon-btn pl-open" aria-label="Open playlist" type="button">' + ICONS.queueNext + '</button>' +
        '<button class="icon-btn pl-play" aria-label="Play playlist" type="button">' + ICONS.play + '</button>' +
        '<button class="icon-btn pl-edit" aria-label="Rename playlist" type="button">' + ICONS.edit + '</button>' +
        '<button class="icon-btn pl-del" aria-label="Delete playlist" type="button">' + ICONS.trash + '</button>' +
      '</div>';
    function open() { location.hash = '#/playlist/' + pl.id; }
    el.querySelector('.pl-cover').onclick = open;
    el.querySelector('.pl-cover').onkeydown = function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(); } };
    el.querySelector('.pl-open').onclick = open;
    el.querySelector('.pl-play').onclick = function () {
      if (!pl.tracks.length) { toast('Playlist is empty', 'err'); return; }
      playList(pl.tracks, 0);
    };
    el.querySelector('.pl-edit').onclick = function () {
      promptModal('Rename playlist', 'New name for this playlist.', 'Playlist name', pl.name, 'Save', function (name) {
        pl.name = name;
        pl.updated = Date.now();
        savePlaylists();
        renderView();
        renderSidePlaylists();
      });
    };
    el.querySelector('.pl-del').onclick = function () {
      confirmModal('Delete "' + pl.name + '"?', 'This removes the playlist from this browser. Tracks themselves are untouched.', 'Delete', function () {
        playlists = playlists.filter(function (p) { return p.id !== pl.id; });
        savePlaylists();
        renderView();
        renderSidePlaylists();
        toast('Playlist deleted', 'ok');
      });
    };
    return el;
  }
  function newPlaylistFlow() {
    promptModal('New playlist', 'Give your playlist a name.', 'My playlist', '', 'Create', function (name) {
      createPlaylist(name);
      renderView();
      renderSidePlaylists();
      toast('Playlist created', 'ok');
    });
  }

  function playlistView(id) {
    var pl = findPlaylist(id);
    var inner = document.createElement('div');
    inner.className = 'view-inner';
    view.innerHTML = '';
    view.appendChild(inner);
    if (!pl) {
      inner.appendChild(stateBlock(ICONS.music, 'Playlist not found', 'It may have been deleted.', function () { location.hash = '#/playlists'; }));
      return;
    }
    var head = viewHead('Playlist', pl.name, pl.tracks.length + ' track' + (pl.tracks.length === 1 ? '' : 's') + ' - stored in this browser');
    inner.appendChild(head);
    var bar = document.createElement('div');
    bar.className = 'hero-actions';
    bar.style.margin = '0 0 16px';
    var pb = document.createElement('button');
    pb.className = 'btn';
    pb.type = 'button';
    pb.innerHTML = ICONS.play + ' Play all';
    pb.onclick = function () { if (!pl.tracks.length) { toast('Playlist is empty', 'err'); return; } playList(pl.tracks, 0); };
    var sb = document.createElement('button');
    sb.className = 'btn btn-dim';
    sb.type = 'button';
    sb.innerHTML = ICONS.shuffle + ' Shuffle';
    sb.onclick = function () {
      if (!pl.tracks.length) { toast('Playlist is empty', 'err'); return; }
      shuffleOn = true;
      $('#shuffleBtn').setAttribute('aria-pressed', 'true');
      $('#shuffleBtn').classList.add('on');
      playList(pl.tracks, Math.floor(Math.random() * pl.tracks.length));
    };
    var rb = document.createElement('button');
    rb.className = 'btn btn-dim btn-s';
    rb.type = 'button';
    rb.textContent = 'Rename';
    rb.onclick = function () {
      promptModal('Rename playlist', 'New name for this playlist.', 'Playlist name', pl.name, 'Save', function (name) {
        pl.name = name;
        pl.updated = Date.now();
        savePlaylists();
        renderView();
        renderSidePlaylists();
      });
    };
    var qb = document.createElement('button');
    qb.className = 'btn btn-danger btn-s';
    qb.type = 'button';
    qb.textContent = 'Delete';
    qb.onclick = function () {
      confirmModal('Delete "' + pl.name + '"?', 'This removes the playlist from this browser.', 'Delete', function () {
        playlists = playlists.filter(function (p) { return p.id !== pl.id; });
        savePlaylists();
        location.hash = '#/playlists';
        renderSidePlaylists();
      });
    };
    bar.appendChild(pb);
    bar.appendChild(sb);
    bar.appendChild(rb);
    bar.appendChild(qb);
    inner.appendChild(bar);

    if (!pl.tracks.length) {
      inner.appendChild(stateBlock(ICONS.music, 'This playlist is empty', 'Add tracks from any card or track row using the plus button.'));
      return;
    }
    var list = document.createElement('div');
    list.className = 'track-list';
    pl.tracks.forEach(function (t, i) {
      var row = trackRowEl(t, pl.tracks, i);
      var rm = document.createElement('button');
      rm.className = 'icon-btn ghost';
      rm.type = 'button';
      rm.setAttribute('aria-label', 'Remove from playlist');
      rm.innerHTML = ICONS.trash;
      rm.onclick = function () {
        pl.tracks.splice(i, 1);
        pl.updated = Date.now();
        savePlaylists();
        renderView();
      };
      row.querySelector('.track-acts').appendChild(rm);
      list.appendChild(row);
    });
    inner.appendChild(list);
  }

  function queueView() {
    var inner = document.createElement('div');
    inner.className = 'view-inner';
    view.innerHTML = '';
    view.appendChild(inner);
    inner.appendChild(viewHead('Playback', 'Queue', 'The running order for this session.'));
    if (!queue.length) {
      inner.appendChild(stateBlock(ICONS.music, 'Queue is empty', 'Play any track to build your queue.'));
      return;
    }
    var list = document.createElement('div');
    list.className = 'track-list';
    queue.forEach(function (t, i) {
      var row = trackRowEl(t, queue, i);
      if (i === qi) {
        row.classList.add('playing');
        var note = document.createElement('span');
        note.className = 'playing-note';
        note.style.marginLeft = '8px';
        note.textContent = 'NOW';
        row.querySelector('.track-title').appendChild(note);
      }
      var upBtn = document.createElement('button');
      upBtn.className = 'icon-btn ghost';
      upBtn.type = 'button';
      upBtn.setAttribute('aria-label', 'Move up');
      upBtn.innerHTML = ICONS.up;
      upBtn.onclick = function (e) { e.stopPropagation(); moveQueue(i, i - 1); renderView(); };
      var downBtn = document.createElement('button');
      downBtn.className = 'icon-btn ghost';
      downBtn.type = 'button';
      downBtn.setAttribute('aria-label', 'Move down');
      downBtn.innerHTML = ICONS.down;
      downBtn.onclick = function (e) { e.stopPropagation(); moveQueue(i, i + 1); renderView(); };
      var rm = document.createElement('button');
      rm.className = 'icon-btn ghost';
      rm.type = 'button';
      rm.setAttribute('aria-label', 'Remove from queue');
      rm.innerHTML = ICONS.trash;
      rm.onclick = function (e) {
        e.stopPropagation();
        queue.splice(i, 1);
        if (qi > i) qi--;
        else if (qi === i) { qi = Math.min(qi, queue.length - 1); if (queue[qi]) loadTrack(queue[qi], playing); }
        buildOrder();
        renderQueueBadge();
        renderView();
      };
      var acts = row.querySelector('.track-acts');
      acts.insertBefore(upBtn, acts.firstChild);
      acts.insertBefore(downBtn, acts.firstChild);
      acts.appendChild(rm);
      list.appendChild(row);
    });
    inner.appendChild(list);
  }
  function isQueueRoute() {
    return location.hash.replace(/^#\/?/, '').split('?')[0] === 'queue';
  }
  function renderQueueViewIfActive() { if (isQueueRoute()) renderView(); }

  function settingsView() {
    var inner = document.createElement('div');
    inner.className = 'view-inner';
    view.innerHTML = '';
    view.appendChild(inner);
    inner.appendChild(viewHead('Preferences', 'Settings', 'Everything is stored locally in this browser.'));
    var grid = document.createElement('div');
    grid.className = 'settings-grid';

    grid.appendChild(settingRow('Autoplay next track', 'Continue to the next queued track when one finishes.', settings.autoplayNext, function (on) {
      settings.autoplayNext = on;
      saveSettings();
    }));

    grid.appendChild(settingRow('Reduce motion', 'Disable card animations and transitions.', settings.reduceMotion, function (on) {
      settings.reduceMotion = on;
      saveSettings();
      applySettings();
    }));

    var volRow = document.createElement('div');
    volRow.className = 'set-row';
    volRow.innerHTML =
      '<div class="set-info"><h3>Default volume</h3><p>Starting volume for new sessions.</p></div>' +
      '<input id="setVol" class="vol-range" type="range" min="0" max="1" step="0.01" value="' + settings.volume + '" aria-label="Default volume">';
    grid.appendChild(volRow);

    var sleepRow = document.createElement('div');
    sleepRow.className = 'set-row';
    sleepRow.innerHTML =
      '<div class="set-info"><h3>Sleep timer</h3><p id="sleepLabel">' + esc(sleepLabel()) + '</p></div>' +
      '<div class="seg" id="sleepSeg" role="group" aria-label="Sleep timer minutes">' +
        '<button class="seg-btn cat-chip" data-min="0" type="button">Off</button>' +
        '<button class="seg-btn cat-chip" data-min="15" type="button">15m</button>' +
        '<button class="seg-btn cat-chip" data-min="30" type="button">30m</button>' +
        '<button class="seg-btn cat-chip" data-min="60" type="button">60m</button>' +
      '</div>';
    grid.appendChild(sleepRow);
    $$('#sleepSeg .seg-btn').forEach(function (b) {
      b.onclick = function () { setSleep(parseInt(b.getAttribute('data-min'), 10) || 0); };
    });
    updateSleepLabels();

    var danger = document.createElement('div');
    danger.className = 'set-row';
    danger.innerHTML =
      '<div class="set-info"><h3>Clear library data</h3><p>Removes liked songs, recent history and playlists from this browser.</p></div>' +
      '<button class="btn btn-danger btn-s" id="clearLib" type="button">Clear data</button>';
    grid.appendChild(danger);
    inner.appendChild(grid);

    var shortcutSec = sectionEl('Keyboard shortcuts', null, null);
    var table = document.createElement('table');
    table.className = 'shortcut-table';
    table.innerHTML =
      '<tbody>' +
      '<tr><td>Focus search</td><td><kbd>Ctrl</kbd> + <kbd>K</kbd> / <kbd>/</kbd></td></tr>' +
      '<tr><td>Play / pause</td><td><kbd>Space</kbd></td></tr>' +
      '<tr><td>Next track</td><td><kbd>Shift</kbd> + <kbd>Right</kbd></td></tr>' +
      '<tr><td>Previous track</td><td><kbd>Shift</kbd> + <kbd>Left</kbd></td></tr>' +
      '<tr><td>Mute</td><td><kbd>M</kbd></td></tr>' +
      '<tr><td>Close overlays</td><td><kbd>Esc</kbd></td></tr>' +
      '</tbody>';
    shortcutSec.appendChild(table);
    inner.appendChild(shortcutSec);

    var aboutSec = sectionEl('About', null, null);
    var ap = document.createElement('p');
    ap.className = 'view-sub';
    ap.innerHTML = 'IOTA AUDIO streams provider-backed audio with HTTP Range support. ' +
      'Library data never leaves this browser. Developer tools: ' +
      '<a href="/dev" style="color:var(--iota-accent)">console</a>, ' +
      '<a href="/docs" style="color:var(--iota-accent)">API docs</a>, ' +
      '<a href="/status" style="color:var(--iota-accent)">live stats</a>.';
    aboutSec.appendChild(ap);
    inner.appendChild(aboutSec);

    var sv = $('#setVol');
    sv.addEventListener('input', function () {
      settings.volume = parseFloat(sv.value);
      audio.volume = settings.volume;
      setRangeFill(sv, settings.volume * 100);
      $('#vol').value = String(settings.volume);
      setRangeFill($('#vol'), settings.volume * 100);
      saveSettings();
    });
    setRangeFill(sv, settings.volume * 100);
    $('#clearLib').onclick = function () {
      confirmModal('Clear all library data?', 'Liked songs, history and playlists will be permanently removed from this browser.', 'Clear everything', function () {
        liked = {};
        recent = [];
        playlists = [];
        saveLiked();
        saveRecent();
        savePlaylists();
        renderSidePlaylists();
        renderView();
        toast('Library data cleared', 'ok');
      });
    };
  }
  function settingRow(title, sub, on, onChange) {
    var row = document.createElement('div');
    row.className = 'set-row';
    row.innerHTML =
      '<div class="set-info"><h3>' + esc(title) + '</h3><p>' + esc(sub) + '</p></div>' +
      '<button class="switch" type="button" role="switch" aria-pressed="' + (on ? 'true' : 'false') + '" aria-label="' + esc(title) + '"></button>';
    var sw = row.querySelector('.switch');
    sw.onclick = function () {
      var v = sw.getAttribute('aria-pressed') !== 'true';
      sw.setAttribute('aria-pressed', v ? 'true' : 'false');
      onChange(v);
    };
    return row;
  }

  // ---------------- sidebar playlists ----------------
  function renderSidePlaylists() {
    var box = $('#sidePlaylists');
    if (!box) return;
    box.innerHTML = '';
    if (!playlists.length) {
      box.innerHTML = '<p class="side-empty">No playlists yet.</p>';
      return;
    }
    playlists.slice(0, 8).forEach(function (pl) {
      var a = document.createElement('a');
      a.className = 'nav-item';
      a.href = '#/playlist/' + pl.id;
      a.innerHTML = '<span>' + esc(pl.name) + '</span>';
      box.appendChild(a);
    });
  }

  // ---------------- router ----------------
  function parseHash() {
    var raw = location.hash.replace(/^#/, '');
    if (!raw || raw === '/') return { path: 'home', params: {} };
    var parts = raw.split('?');
    var segs = parts[0].split('/').filter(Boolean);
    var params = {};
    if (parts[1]) {
      parts[1].split('&').forEach(function (kv) {
        var p = kv.split('=');
        params[decodeURIComponent(p[0])] = decodeURIComponent(p[1] || '');
      });
    }
    return { path: segs, params: params };
  }

  function renderView() {
    var r = parseHash();
    var segs = r.path;
    var name = segs === 'home' ? 'home' : segs[0];
    if (name === 'home') homeView();
    else if (name === 'search') searchView(r.params);
    else if (name === 'songs') songsView(r.params);
    else if (name === 'moods') moodsView();
    else if (name === 'tag') tagView(decodeURIComponent(segs[1] || ''));
    else if (name === 'liked') likedView();
    else if (name === 'recent') recentView();
    else if (name === 'playlists') playlistsView();
    else if (name === 'playlist') playlistView(segs[1] || '');
    else if (name === 'queue') queueView();
    else if (name === 'settings') settingsView();
    else homeView();
    setActiveNav(name);
    view.scrollTop = 0;
    closeSidebar();
    var titles = {
      home: 'IOTA AUDIO', search: 'Search', songs: 'All Songs', moods: 'Moods & Tags',
      liked: 'Liked Songs', recent: 'Recently Played', playlists: 'Playlists',
      playlist: 'Playlist', queue: 'Queue', settings: 'Settings', tag: 'Tag'
    };
    document.title = (titles[name] || 'IOTA AUDIO') + ' - IOTA AUDIO';
  }
  function setActiveNav(name) {
    var map = { home: 'home', search: 'search', songs: 'songs', moods: 'moods', tag: 'moods', liked: 'liked', recent: 'recent', playlists: 'playlists', playlist: 'playlists', queue: 'queue', settings: 'settings' };
    var active = map[name];
    $$('.side-nav .nav-item').forEach(function (a) {
      a.classList.toggle('active', a.getAttribute('data-route') === active);
    });
  }
  window.addEventListener('hashchange', renderView);

  // ---------------- search bar ----------------
  var searchForm = $('#searchForm');
  var searchInput = $('#searchInput');
  var suggestBox = $('#suggestBox');
  var searchClear = $('#searchClear');
  var sugSeq = 0;
  var sugItems = [];
  var sugActive = -1;

  function focusSearch() { searchInput.focus(); searchInput.select(); }

  var runSuggest = debounce(function () {
    var q = searchInput.value.trim();
    if (q.length < 2) { closeSuggest(); return; }
    var seq = ++sugSeq;
    API.suggest(q).then(function (data) {
      if (seq !== sugSeq) return;
      renderSuggest(data.suggestions || []);
    }).catch(function () {
      if (seq !== sugSeq) return;
      closeSuggest();
    });
  }, 320);

  function renderSuggest(items) {
    sugItems = items.slice(0, 8);
    sugActive = -1;
    if (!sugItems.length) { closeSuggest(); return; }
    suggestBox.innerHTML = '';
    sugItems.forEach(function (s, i) {
      var b = document.createElement('button');
      b.className = 'suggest-item';
      b.type = 'button';
      b.setAttribute('role', 'option');
      b.innerHTML = ICONS.search + '<span>' + esc(s) + '</span>';
      b.onmousedown = function (e) { e.preventDefault(); commitSearch(s); };
      suggestBox.appendChild(b);
    });
    suggestBox.hidden = false;
  }
  function closeSuggest() {
    suggestBox.hidden = true;
    suggestBox.innerHTML = '';
    sugItems = [];
    sugActive = -1;
  }
  function highlightSuggest(dir) {
    if (!sugItems.length) return;
    sugActive = (sugActive + dir + sugItems.length) % sugItems.length;
    $$('.suggest-item', suggestBox).forEach(function (b, i) {
      b.classList.toggle('active', i === sugActive);
    });
  }
  function commitSearch(q) {
    q = (q || '').trim();
    if (!q) return;
    closeSuggest();
    searchInput.value = q;
    if (location.hash === '#/search?q=' + encodeURIComponent(q)) searchView({ q: q });
    else location.hash = '#/search?q=' + encodeURIComponent(q);
  }

  searchForm.addEventListener('submit', function (e) {
    e.preventDefault();
    commitSearch(searchInput.value);
  });
  searchInput.addEventListener('input', function () {
    searchClear.hidden = !searchInput.value;
    runSuggest();
  });
  searchInput.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowDown') { e.preventDefault(); highlightSuggest(1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); highlightSuggest(-1); }
    else if (e.key === 'Enter') {
      if (sugActive >= 0 && sugItems[sugActive]) { e.preventDefault(); commitSearch(sugItems[sugActive]); }
    } else if (e.key === 'Escape') { closeSuggest(); }
  });
  searchInput.addEventListener('focus', function () {
    if (searchInput.value.trim().length >= 2 && sugItems.length) suggestBox.hidden = false;
  });
  searchClear.onclick = function () {
    searchInput.value = '';
    searchClear.hidden = true;
    closeSuggest();
    searchInput.focus();
  };
  document.addEventListener('click', function (e) {
    if (!e.target.closest('.search-wrap')) closeSuggest();
  });
  document.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      focusSearch();
    }
  });

  // ---------------- mobile sidebar ----------------
  var sidebar = $('#sidebar');
  var backdrop = $('#backdrop');
  var navToggle = $('#navToggle');
  function openSidebar() {
    sidebar.classList.add('open');
    backdrop.hidden = false;
    requestAnimationFrame(function () { backdrop.classList.add('show'); });
    navToggle.setAttribute('aria-expanded', 'true');
  }
  function closeSidebar() {
    sidebar.classList.remove('open');
    backdrop.classList.remove('show');
    setTimeout(function () { backdrop.hidden = true; }, 250);
    navToggle.setAttribute('aria-expanded', 'false');
  }
  navToggle.onclick = function () {
    if (sidebar.classList.contains('open')) closeSidebar(); else openSidebar();
  };
  backdrop.onclick = closeSidebar;

  // ---------------- api status pill ----------------
  function pollApi() {
    apiGet('/health', 6000).then(function () {
      var pill = $('#apiPill');
      pill.classList.add('ok');
      pill.classList.remove('bad');
      $('#apiPillText').textContent = 'ONLINE';
    }).catch(function () {
      var pill = $('#apiPill');
      pill.classList.remove('ok');
      pill.classList.add('bad');
      $('#apiPillText').textContent = 'OFFLINE';
    });
  }

  // ---------------- boot ----------------
  function boot() {
    applySettings();
    $('#vol').value = String(settings.volume);
    setRangeFill($('#vol'), settings.volume * 100);
    updateMuteIcon();
    renderSidePlaylists();
    renderQueueBadge();
    renderQueueList();

    var startVol = LS.get('iota-vol', null);
    if (startVol != null && settings.volume === 1) {
      settings.volume = parseFloat(startVol) || 1;
      $('#vol').value = String(settings.volume);
      setRangeFill($('#vol'), settings.volume * 100);
    }
    audio.volume = settings.volume;

    if (!location.hash) location.hash = '#/';
    renderView();
    pollApi();
    setInterval(pollApi, 45000);
    setInterval(function () {
      if (sleepUntil) updateSleepLabels();
    }, 30000);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
