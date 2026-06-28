/** @type {import('tailwindcss').Config} */
module.exports = {
  // ── Content: dove Tailwind cerca le classi usate ──────────────
  // La CLI scansiona questi file per il tree-shaking.
  // Deve corrispondere al --content del workflow.
  content: [
    "./docs/**/*.html",
  ],

  theme: {
    extend: {
      // ── Palette HiKingsRome ─────────────────────────────────
      colors: {
        forest: '#1C2B1A',
        sage:   '#4A6741',
        ivory:  '#F5F2EE',
        sand:   '#E8E3DC',
        earth:  '#8B7355',
      },
      // ── Tipografia ──────────────────────────────────────────
      fontFamily: {
        display: ['"DM Serif Display"', 'Georgia', 'serif'],
        body:    ['Inter', 'system-ui', 'sans-serif'],
      },
      // ── Aspect ratio (usato nel hero) ───────────────────────
      aspectRatio: {
        'video': '16 / 9',
      },
    },
  },

  plugins: [],
}
