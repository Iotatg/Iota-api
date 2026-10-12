// Iota UI helpers — retro-computing edition
(function () {
  'use strict';

  // Toast notification
  function showToast(message, type) {
    type = type || 'info';
    var toast = document.getElementById('toast');
    if (!toast) return;
    toast.className = 'toast toast-' + type + ' visible';
    toast.innerHTML =
      '<span class="toast-dot"></span>' +
      '<span class="mono">' + message + '</span>';
    if (window.__iotaToastTimer) clearTimeout(window.__iotaToastTimer);
    window.__iotaToastTimer = setTimeout(function () {
      toast.classList.remove('visible');
    }, 3000);
  }
  window.showToast = showToast;

  // Scroll reveal with technical line drawing effect
  function initReveal() {
    if (typeof IntersectionObserver === 'undefined') return;

    var sections = document.querySelectorAll('section');
    var markers = [];

    sections.forEach(function (sec) {
      sec.style.opacity = '0';
      sec.style.transform = 'translateY(24px)';
      sec.style.transition = 'opacity 0.5s cubic-bezier(0.2, 0, 0.2, 1), transform 0.5s cubic-bezier(0.2, 0, 0.2, 1)';

      var marker = document.createElement('div');
      marker.style.cssText = 'position:absolute;top:0;left:0;right:0;height:1px;background:transparent;';
      sec.style.position = 'relative';
      sec.appendChild(marker);
      markers.push({ sec: sec, marker: marker });
    });

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        var m = markers.find(function (m) { return m.sec === entry.target; });
        if (m && entry.isIntersecting) {
          var mWidth = 0;
          var w = entry.target.offsetWidth;
          var id = setInterval(function () {
            mWidth += Math.min(12, w * 0.1);
            m.marker.style.width = mWidth + 'px';
            if (mWidth >= w) {
              m.marker.style.background = '#d97706';
              entry.target.style.opacity = '1';
              entry.target.style.transform = 'translateY(0)';
              clearInterval(id);
            }
          }, 16);
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.05, rootMargin: '0px 0px -40px 0px' });

    sections.forEach(function (sec) {
      observer.observe(sec);
    });
  }

  // Card stagger reveal
  function initCardStagger() {
    if (typeof IntersectionObserver === 'undefined') return;

    var cards = document.querySelectorAll('.card, .panel, .panel-dark, .stat-number');
    if (!cards.length) return;

    cards.forEach(function (el) {
      el.style.opacity = '0';
      el.style.transform = 'translateY(16px)';
      el.style.transition =
        'opacity 0.4s cubic-bezier(0.2, 0, 0.2, 1) ' + (el.getAttribute('data-reveal-delay') || 0) + 'ms, ' +
        'transform 0.4s cubic-bezier(0.2, 0, 0.2, 1) ' + (el.getAttribute('data-reveal-delay') || 0) + 'ms';
    });

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0)';
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -30px 0px' });

    cards.forEach(function (el) {
      observer.observe(el);
    });
  }

  // Status dot pulse animation
  function initPulse() {
    // Applied via CSS; nothing JS needed here
  }

  // Keyboard shortcuts
  function initKeyboard() {
    document.addEventListener('keydown', function (e) {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

      if (e.key === '/' || (e.key === 'k' && e.ctrlKey)) {
        e.preventDefault();
        var q = document.getElementById('q');
        if (q) q.focus();
      }

      if (e.key.toLowerCase() === 'g' && e.ctrlKey) {
        e.preventDefault();
        var go = document.getElementById('go');
        if (go) go.click();
      }
    });
  }

  // Copy to clipboard helper (with insecure-context fallback)
  window.copyToClipboard = function (text) {
    function fallback() {
      try {
        var ta = document.createElement('textarea');
        ta.value = text;
        ta.setAttribute('readonly', '');
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        var ok = document.execCommand('copy');
        document.body.removeChild(ta);
        showToast(ok ? 'Copied: ' + text : 'Copy failed', ok ? 'success' : 'error');
      } catch (e) {
        showToast('Copy failed', 'error');
      }
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () {
        showToast('Copied: ' + text, 'success');
      }, fallback);
    } else {
      fallback();
    }
  };

  // Initialize
  function init() {
    initReveal();
    initCardStagger();
    initKeyboard();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
