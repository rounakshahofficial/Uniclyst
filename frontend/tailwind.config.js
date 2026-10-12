/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: "#0f1c33",
          soft: "#31415c",
          faint: "#64748b",
        },
        accent: {
          DEFAULT: "#4f46e5",
          hover: "#4338ca",
          soft: "#eef2ff",
          faint: "#e0e7ff",
        },
        surface: {
          DEFAULT: "#f7f8fc",
          card: "#ffffff",
          line: "#e6e9f2",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(15, 28, 51, 0.05), 0 4px 16px rgba(15, 28, 51, 0.06)",
        pop: "0 8px 30px rgba(15, 28, 51, 0.12)",
      },
    },
  },
  plugins: [],
};
