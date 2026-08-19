import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas: '#f4f7fc',
        ink: {
          900: '#0f172a',
          700: '#334155',
          500: '#64748b',
          400: '#94a3b8',
        },
        line: '#e6ebf4',
        brand: {
          50: '#eef4ff',
          100: '#dce7ff',
          200: '#bed3ff',
          300: '#92b4ff',
          400: '#5f8bfa',
          500: '#3b66ef',
          600: '#2a4ddb',
          700: '#243db1',
          800: '#23368c',
          900: '#22326f',
        },
        accent: {
          50: '#fff5ed',
          200: '#fed7aa',
          400: '#fb923c',
          500: '#ef7c33',
          600: '#d9601c',
        },
        ok: { 50: '#ecfdf5', 200: '#a7f3d0', 500: '#10b981', 600: '#059669' },
        warn: { 50: '#fffbeb', 200: '#fde68a', 500: '#f59e0b', 600: '#d97706' },
        danger: { 50: '#fef2f2', 200: '#fecaca', 500: '#ef4444', 600: '#dc2626' },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
      },
      borderRadius: {
        card: '16px',
      },
      boxShadow: {
        card: '0 1px 2px rgba(15, 23, 42, 0.04), 0 4px 16px rgba(15, 23, 42, 0.04)',
        lift: '0 2px 4px rgba(15, 23, 42, 0.05), 0 12px 32px rgba(15, 23, 42, 0.08)',
      },
      keyframes: {
        'fade-up': {
          from: { opacity: '0', transform: 'translateY(6px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        'fade-up': 'fade-up 0.25s ease-out both',
      },
    },
  },
  plugins: [],
} satisfies Config;
