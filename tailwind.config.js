/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./docs/**/*.html",
    "./docs/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        forest: '#1C2B1A',
        sage:   '#4A6741',
        ivory:  '#F5F2EE',
        sand:   '#E8E3DC',
        earth:  '#8B7355',
      },
      fontFamily: {
        display: ['"DM Serif Display"', 'Georgia', 'serif'],
        body:    ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
