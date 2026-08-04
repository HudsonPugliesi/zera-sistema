/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./templates/**/*.html"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        zera: {
          50: '#eefdf5', 100: '#d6fae6', 200: '#aef2ce', 300: '#7ce6b1',
          400: '#45d190', 500: '#1fb676', 600: '#14935f', 700: '#13744d',
          800: '#135c40', 900: '#124b36', 950: '#062a1e'
        }
      }
    }
  },
  plugins: [],
};
