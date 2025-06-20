/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'ballistic': {
          50: '#faf5ff',
          100: '#f3e8ff',
          200: '#e9d5ff',
          300: '#d8b4fe',
          400: '#c084fc',
          500: '#a855f7',
          600: '#9333ea',
          700: '#7c3aed',
          800: '#6b21a8',
          900: '#581c87',
          950: '#3b0764',
        },
        'dark': {
          50: '#f6f6f7',
          100: '#f1f1f3',
          200: '#e6e6ea',
          300: '#d1d1d8',
          400: '#adadb8',
          500: '#8e8e9a',
          600: '#757582',
          700: '#62626c',
          800: '#4f4f56',
          900: '#3a3a3f',
          950: '#1a1a1e',
        }
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-conic': 'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
        'arena-gradient': 'linear-gradient(135deg, #370b6a 0%, #651cbf 50%, #7724e3 100%)',
      },
    },
  },
  plugins: [],
} 