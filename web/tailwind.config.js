/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      colors: {
        brand: {
          indigo: "#4f46e5",
          violet: "#7c3aed",
          cyan: "#06b6d4",
        },
      },
      boxShadow: {
        soft: "0 10px 30px -18px rgba(15,23,42,0.25)",
        glow: "0 14px 34px -14px rgba(79,70,229,0.55)",
      },
    },
  },
  plugins: [],
};
