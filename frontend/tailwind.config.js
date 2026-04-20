/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#58a6ff',
        secondary: '#7c3aed',
        accent: '#ec4899',
        dark: '#0a0a0a',
        'dark-gray': '#161b22',
        'light-gray': '#c9d1d9',
      },
      fontFamily: {
        mono: ['Courier New', 'monospace'],
      },
    },
  },
  plugins: [],
}