/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './templates/**/*.html',
    './apps/**/templates/**/*.html',
    './frontend/src/**/*.{js,svelte}',
  ],
  safelist: [
    // Dynamic colour classes used via style= or data attributes
    { pattern: /^bg-(red|green|yellow|blue|indigo|purple|gray)-(100|200|500|600|700)$/ },
  ],
  theme: {
    extend: {
      colors: {
        'dashboard-bg': '#E5E7EB',
        'card-shadow': 'rgba(0, 0, 0, 0.1)',
      },
    },
  },
  plugins: [],
};
