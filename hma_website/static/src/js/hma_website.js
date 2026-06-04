/* ================================================================
   HMA WEBSITE JS — Odoo Frontend Module
   Syncs data-ar/data-en copy with Odoo language + UI helpers
   ================================================================ */

'use strict';

(function () {

  /* ─── Language (follow Odoo html[lang], not a custom toggle) ─── */
  function detectLang() {
    const htmlLang = (document.documentElement.lang || 'ar').toLowerCase();
    if (htmlLang.startsWith('en')) {
      return 'en';
    }
    return 'ar';
  }

  function applyLang(lang) {
    window.HMA_LANG = lang;
    document.querySelectorAll('[data-ar]').forEach(el => {
      const val = el.getAttribute('data-' + lang);
      if (val === null) {
        return;
      }
      if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
        el.placeholder = val;
      } else {
        el.textContent = val;
      }
    });

    document.querySelectorAll('[data-ph-ar]').forEach(el => {
      el.placeholder = el.getAttribute('data-ph-' + lang) || '';
    });

    document.querySelectorAll('[data-title-ar]').forEach(el => {
      el.title = el.getAttribute('data-title-' + lang) || '';
    });
  }

  /* ─── Mobile Nav ──────────────────────────────────────────────── */
  function toggleMobileNav() {
    const mn = document.getElementById('hma-mobile-nav');
    if (mn) {
      mn.classList.toggle('open');
    }
  }
  window.hmaToggleMobileNav = toggleMobileNav;

  /* ─── Scroll-reveal (IntersectionObserver) ────────────────────── */
  function initScrollReveal() {
    const els = document.querySelectorAll('.fade-in');
    if (!els.length) {
      return;
    }

    const reveal = (el) => el.classList.add('visible');

    const obs = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          reveal(e.target);
          obs.unobserve(e.target);
        }
      });
    }, { threshold: 0.07, rootMargin: '0px 0px 80px 0px' });

    els.forEach(el => {
      obs.observe(el);
      const rect = el.getBoundingClientRect();
      if (rect.top < window.innerHeight && rect.bottom > 0) {
        reveal(el);
      }
    });

    // Never leave product/category blocks invisible
    setTimeout(() => els.forEach(reveal), 600);
  }

  /* ─── Active nav link ─────────────────────────────────────────── */
  function markActiveNav() {
    const path = window.location.pathname.replace(/\/$/, '') || '/';
    document.querySelectorAll('.hma-nav-links a, #hma-mobile-nav a:not(.js_change_lang)').forEach(a => {
      const href = a.getAttribute('href') || '';
      const normalized = href.replace(/\/$/, '') || '/';
      if (normalized === path || (path.startsWith(normalized) && normalized !== '/')) {
        a.classList.add('active');
      }
    });
  }

  /* ─── Category filter (products page) ────────────────────────── */
  function initCategoryFilter() {
    const tabs = document.querySelectorAll('.cat-tab[data-cat]');
    const cards = document.querySelectorAll('.prod-card[data-cat]');
    if (!tabs.length) {
      return;
    }

    tabs.forEach(tab => {
      tab.addEventListener('click', function (e) {
        e.preventDefault();
        const cat = this.dataset.cat;

        tabs.forEach(t => t.classList.remove('active'));
        this.classList.add('active');

        cards.forEach(card => {
          if (cat === 'all' || card.dataset.cat === cat) {
            card.style.display = '';
          } else {
            card.style.display = 'none';
          }
        });
      });
    });
  }

  /* ─── Init on DOM ready ───────────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', function () {
    document.documentElement.classList.add('js-hma');
    applyLang(detectLang());
    initScrollReveal();
    markActiveNav();
    initCategoryFilter();
  });

})();
