/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'forex': {
          'bg': '#0a0e17',
          'card': '#111827',
          'border': '#1f2937',
          'green': '#10b981',
          'red': '#ef4444',
          'blue': '#3b82f6',
          'yellow': '#f59e0b',
          'purple': '#8b5cf6',
        }
      }
    },
  },
  plugins: [],
}
