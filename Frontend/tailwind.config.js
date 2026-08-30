/** @type {import('tailwindcss').Config} */
export default {
    content: ['./index.html', './src/**/*.{js,jsx}'],
    theme: {
      extend: {
        colors: {
          navy: '#0B2A4A',
          primary: '#1D4ED8',
          bg: '#F5F7FA',
          border: '#D1D5DB',
          text: {
            primary: '#111827',
            secondary: '#6B7280',
          },
          success: '#15803D',
          warning: '#D97706',
          danger: '#DC2626',
        },
        fontFamily: {
          sans: ['Inter', 'system-ui', 'sans-serif'],
        },
      },
    },
    plugins: [],
  }