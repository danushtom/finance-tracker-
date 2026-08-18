import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-inter)", "sans-serif"],
      },
      colors: {
        background: "#F9FAFB", // light gray background
        surface: "#FFFFFF",    // white for cards
        primary: {
          DEFAULT: "#1E5FF5",  // bright blue
          hover: "#154BD5",
        },
        accent: {
          DEFAULT: "#FF6B4A",  // soft orange/coral
          hover: "#E55333",
        },
        muted: {
          DEFAULT: "#F3F4F6",  // light background for elements
          foreground: "#6B7280", // gray text
        },
        border: "#E5E7EB",
        card: {
          DEFAULT: "#FFFFFF",
          foreground: "#111827",
        },
      },
      borderRadius: {
        xl: "1rem",
        "2xl": "1.5rem",
        "3xl": "2rem",
      },
      boxShadow: {
        soft: "0 4px 20px rgba(0, 0, 0, 0.05)",
      },
    },
  },
  plugins: [],
};

export default config;
