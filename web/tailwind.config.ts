import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        sage: {
          50: "#f4f7f2",
          100: "#e8efe4",
          200: "#d4e2cd",
          300: "#b4ceaa",
          400: "#8fb580",
          500: "#6a9b5a",
          600: "#507a42",
          700: "#3d5e33",
          800: "#2c4425",
          900: "#1e2f1a",
          950: "#111d0f",
        },
        paper: "#f5f7f2",
        "paper-2": "#eaefe4",
        ink: "#1e3320",
        "ink-2": "#2d4a30",
        muted: "#5a7a5e",
        "muted-2": "#92b096",
        rule: "#d4e2cd",
        "rule-2": "#b4ceaa",
        accent: "#507a42",
        "accent-deep": "#3d5e33",
        live: "#d94040",
        detect: "#6a9b5a",
      },
      fontFamily: {
        serif: ['"Source Serif 4"', '"Source Serif Pro"', "Georgia", "serif"],
        sans: ['"DM Sans"', "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
      maxWidth: {
        page: "1320px",
      },
    },
  },
  plugins: [],
};

export default config;
