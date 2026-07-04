import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#172033",
        line: "#d8dee8",
        mist: "#f5f7fa",
        primary: "#2563eb",
        success: "#15803d",
        warning: "#b7791f",
        issue: "#b91c1c",
      },
      boxShadow: {
        panel: "0 1px 2px rgba(16, 24, 40, 0.06)",
      },
    },
  },
  plugins: [],
};

export default config;
