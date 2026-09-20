/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        base: 'rgb(var(--color-base) / <alpha-value>)',
        surface: 'rgb(var(--color-surface) / <alpha-value>)',
        'active-surface': 'rgb(var(--color-active-surface) / <alpha-value>)',
        primary: 'rgb(var(--color-primary) / <alpha-value>)',
        secondary: 'rgb(var(--color-secondary) / <alpha-value>)',
        muted: 'rgb(var(--color-muted) / <alpha-value>)',
        accent: 'rgb(var(--color-accent) / <alpha-value>)',
        'accent-strong': 'rgb(var(--color-accent-strong) / <alpha-value>)',
        done: 'rgb(var(--color-done) / <alpha-value>)',
        warning: 'rgb(var(--color-warning) / <alpha-value>)',
        danger: 'rgb(var(--color-danger) / <alpha-value>)',
        'brand-soft': 'rgb(var(--color-brand-soft) / <alpha-value>)',
        idle: 'rgb(var(--color-idle) / <alpha-value>)',
        outline: 'rgb(var(--color-outline) / <alpha-value>)',
        recess: 'rgb(var(--color-recess) / <alpha-value>)',
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
