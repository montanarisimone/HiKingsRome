/**
 * HiKingsRome — main.js
 * ─────────────────────────────────────────────────────────────
 * Script vanilla puro. Nessuna dipendenza esterna.
 * Caricato con <script src="assets/js/main.js" defer></script>
 * → il defer garantisce che il DOM sia pronto prima dell'esecuzione.
 *
 * Conforme a CSP: script-src 'self'
 * (file locale, nessun inline script nel documento HTML)
 * ─────────────────────────────────────────────────────────────
 */

(function () {
  'use strict';

  /* ── Anno dinamico nel footer ─────────────────────────── */
  const yearEl = document.getElementById('footer-year');
  if (yearEl) {
    yearEl.textContent = new Date().getFullYear();
  }

  /* ── Navbar shadow allo scroll ────────────────────────── */
  const siteHeader = document.getElementById('site-header');
  if (siteHeader) {
    window.addEventListener(
      'scroll',
      function () {
        siteHeader.classList.toggle('nav-scrolled', window.scrollY > 10);
      },
      { passive: true }
    );
  }

  /* ── Mobile menu toggle ───────────────────────────────── */
  const menuBtn   = document.getElementById('mobile-menu-btn');
  const mobileNav = document.getElementById('mobile-menu');
  const iconMenu  = document.getElementById('icon-menu');
  const iconClose = document.getElementById('icon-close');

  if (menuBtn && mobileNav && iconMenu && iconClose) {

    menuBtn.addEventListener('click', function () {
      var isOpen = mobileNav.classList.toggle('hidden') === false;
      menuBtn.setAttribute('aria-expanded', String(isOpen));
      iconMenu.classList.toggle('hidden', isOpen);
      iconClose.classList.toggle('hidden', !isOpen);
    });

    /* Chiudi il menu al click su qualsiasi link interno */
    mobileNav.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () {
        mobileNav.classList.add('hidden');
        menuBtn.setAttribute('aria-expanded', 'false');
        iconMenu.classList.remove('hidden');
        iconClose.classList.add('hidden');
      });
    });

  }

})();
