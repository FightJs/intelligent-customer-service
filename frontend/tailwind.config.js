/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        base: '#0f172a',
        surface: '#1e293b',
        'active-surface': '#172554',
        primary: '#e2e8f0',
        secondary: '#94a3b8',
        muted: '#64748b',
        accent: '#2563eb',
        done: '#34d399',
        idle: '#475569',
      },
      borderRadius: {
        card: '8px',
        bubble: '14px',
        pill: '18px',
      },
    },
  },
  plugins: [],
}
