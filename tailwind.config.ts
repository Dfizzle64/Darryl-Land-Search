import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0c1218",
          900: "#121a22",
          800: "#1a2430",
          700: "#243140",
          500: "#6b7c8d",
          300: "#c5d0da",
          100: "#eef3f7",
        },
        clay: {
          400: "#d7a36a",
          500: "#c8894a",
        },
        moss: {
          400: "#6fbf9a",
          500: "#3f9d74",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "ui-serif", "Georgia", "serif"],
      },
    },
  },
  plugins: [],
};

export default config;
