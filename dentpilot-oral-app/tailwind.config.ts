import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        navy: "#071426",
        ink: "#0f172a",
        cyan: "#22d3ee",
        clinical: "#e6f7fb"
      },
      boxShadow: {
        glow: "0 24px 80px rgba(34, 211, 238, 0.18)"
      }
    }
  },
  plugins: []
};

export default config;
