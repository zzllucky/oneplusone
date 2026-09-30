/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,ts}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eef6ff',
          100: '#d9eaff',
          500: '#2f6fed',
          600: '#2559c9',
          700: '#1d459c',
        },
      },
    },
  },
  plugins: [],
}
