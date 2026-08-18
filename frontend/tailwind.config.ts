import type { Config } from "tailwindcss";

// Deliberately minimal — layout utilities only. Visual design (palette,
// type scale, components) is not built out yet; the user will provide
// example designs to implement later.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {},
  },
  plugins: [],
};

export default config;
