/* ================================================================
   HMA WEBSITE JS — Odoo Frontend Module
   Bilingual toggle (AR/EN) + scroll animations + mobile nav
   Works alongside Odoo's own language system
   ================================================================ */

'use strict';

(function () {

  /* ─── Language Engine ─────────────────────────────────────────── */
  window.HMA_LANG = 'ar';

  function applyLang(lang) {
    window.HMA_LANG = lang;
    const html = document.documentElement;
    html.lang = lang;
    html.dir  = lang === 'ar' ? 'rtl' : 'ltr';

    // Update all data-ar / data-en text nodes
    document.querySelectorAll('[data-ar]').forEach(el => {
      const val = el.getAttribute('data-' + lang);
      if (val !== null) {
        if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
          el.placeholder = val;
        } else {
          el.textContent = val;
        }
      }
    });

    // Placeholder attributes
    document.querySelectorAll('[data-ph-ar]').forEach(el => {
      el.placeholder = el.getAttribute('data-ph-' + lang) || '';
    });

    // title attributes
    document.querySelectorAll('[data-title-ar]').forEach(el => {
      el.title = el.getAttribute('data-title-' + lang) || '';
    });

    // Language button label
    document.querySelectorAll('.hma-lang-btn').forEach(btn => {
      btn.textContent = lang === 'ar' ? 'EN' : 'عر';
    });

    // Persist preference
    try { localStorage.setItem('hma_lang', lang); } catch (e) {}
  }

  function toggleLang() {
    applyLang(window.HMA_LANG === 'ar' ? 'en' : 'ar');
  }

  // Expose globally so inline onclick handlers work
  window.hmaToggleLang  = toggleLang;
  window.hmaApplyLang   = applyLang;

  /* ─── Mobile Nav ──────────────────────────────────────────────── */
  function toggleMobileNav() {
    const mn = document.getElementById('hma-mobile-nav');
    if (mn) mn.classList.toggle('open');
  }
  window.hmaToggleMobileNav = toggleMobileNav;

  /* ─── Scroll-reveal (IntersectionObserver) ────────────────────── */
  function initScrollReveal() {
    const obs = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          e.target.classList.add('visible');
          obs.unobserve(e.target);
        }
      });
    }, { threshold: 0.07 });

    document.querySelectorAll('.fade-in').forEach(el => obs.observe(el));
  }

  /* ─── Active nav link ─────────────────────────────────────────── */
  function markActiveNav() {
    const path = window.location.pathname.replace(/\/$/, '') || '/';
    document.querySelectorAll('.hma-nav-links a, #hma-mobile-nav a').forEach(a => {
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
    if (!tabs.length) return;

    tabs.forEach(tab => {
      tab.addEventListener('click', function (e) {
        e.preventDefault();
        const cat = this.dataset.cat;

        // Update active tab
        tabs.forEach(t => t.classList.remove('active'));
        this.classList.add('active');

        // Show / hide product cards
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
    // Restore language preference (default Arabic)
    let saved = 'ar';
    try { saved = localStorage.getItem('hma_lang') || 'ar'; } catch (e) {}
    applyLang(saved);

    initScrollReveal();
    markActiveNav();
    initCategoryFilter();
  });

})();
