/**
 * HiKingsRome — main.js
 * Vanilla JS, no dependencies. Loaded with <script defer>.
 * Compliant with CSP: script-src 'self'
 */
(function () {
  'use strict';

  /* ── Anno dinamico nel footer ─────────────────────────── */
  var yearEl = document.getElementById('footer-year');
  if (yearEl) yearEl.textContent = new Date().getFullYear();

  /* ── Navbar shadow on scroll ──────────────────────────── */
  var siteHeader = document.getElementById('site-header');
  if (siteHeader) {
    window.addEventListener('scroll', function () {
      siteHeader.classList.toggle('nav-scrolled', window.scrollY > 10);
    }, { passive: true });
  }

  /* ── Mobile menu toggle ───────────────────────────────── */
  var menuBtn   = document.getElementById('mobile-menu-btn');
  var mobileNav = document.getElementById('mobile-menu');
  var iconMenu  = document.getElementById('icon-menu');
  var iconClose = document.getElementById('icon-close');

  if (menuBtn && mobileNav && iconMenu && iconClose) {
    menuBtn.addEventListener('click', function () {
      var isOpen = mobileNav.classList.toggle('hidden') === false;
      menuBtn.setAttribute('aria-expanded', String(isOpen));
      iconMenu.classList.toggle('hidden', isOpen);
      iconClose.classList.toggle('hidden', !isOpen);
    });
    mobileNav.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () {
        mobileNav.classList.add('hidden');
        menuBtn.setAttribute('aria-expanded', 'false');
        iconMenu.classList.remove('hidden');
        iconClose.classList.add('hidden');
      });
    });
  }

  /* ── FAQ Accordion ────────────────────────────────────── */
  var faqButtons = document.querySelectorAll('.faq-question');

  faqButtons.forEach(function (btn) {
    btn.addEventListener('click', function () {
      var item     = btn.closest('.faq-item');
      var isOpen   = item.classList.contains('open');
      var answerId = btn.getAttribute('aria-controls');
      var answer   = document.getElementById(answerId);

      // Chiudi tutti gli altri
      document.querySelectorAll('.faq-item.open').forEach(function (openItem) {
        if (openItem !== item) {
          openItem.classList.remove('open');
          openItem.querySelector('.faq-question').setAttribute('aria-expanded', 'false');
        }
      });

      // Apri / chiudi quello corrente
      item.classList.toggle('open', !isOpen);
      btn.setAttribute('aria-expanded', String(!isOpen));

      // Focus management: scroll smooth in view se aperto
      if (!isOpen && answer) {
        setTimeout(function () {
          answer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }, 50);
      }
    });
  });

  /* ── Deep-link: apre la FAQ corretta se c'è hash nell'URL ── */
  function openFaqFromHash() {
    var hash = window.location.hash;
    if (!hash) return;
    var item = document.querySelector(hash + '.faq-item');
    if (!item) return;
    item.classList.add('open');
    var btn = item.querySelector('.faq-question');
    if (btn) btn.setAttribute('aria-expanded', 'true');
  }
  openFaqFromHash();
  window.addEventListener('hashchange', openFaqFromHash);

})();
