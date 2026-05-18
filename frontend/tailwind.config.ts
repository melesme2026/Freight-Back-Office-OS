import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
    "./src/hooks/**/*.{ts,tsx}",
    "./src/lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#edf7ff",
          100: "#d7edff",
          200: "#b8ddff",
          300: "#88c7ff",
          400: "#56a6f7",
          500: "#2f80ed",
          600: "#1f66cf",
          700: "#1d54a7",
          800: "#1d477f",
          900: "#183a66",
          950: "#10233f",
        },
        route: {
          50: "#effdfa",
          100: "#cbf7ef",
          200: "#99eee1",
          300: "#5fdfcf",
          400: "#31c4b3",
          500: "#1aa596",
          600: "#128579",
          700: "#126a62",
          800: "#12554f",
          900: "#124741",
        },
        ops: {
          ink: "#111827",
          muted: "#64748b",
          line: "#d8e2ee",
          canvas: "#f6f8fb",
          panel: "#ffffff",
          success: "#147d64",
          warning: "#b7791f",
          danger: "#c2413d",
        },
      },
      boxShadow: {
        soft: "0 14px 40px rgba(16, 35, 63, 0.10)",
        operational: "0 18px 60px rgba(16, 35, 63, 0.14)",
        glow: "0 0 0 1px rgba(49, 196, 179, 0.18), 0 24px 70px rgba(47, 128, 237, 0.20)",
      },
      borderRadius: {
        xl2: "1rem",
        "2.5xl": "1.25rem",
        "3xl": "1.5rem",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
        mono: ["SFMono-Regular", "Roboto Mono", "Consolas", "Liberation Mono", "monospace"],
      },
      backgroundImage: {
        "ops-grid": "linear-gradient(rgba(16,35,63,.05) 1px, transparent 1px), linear-gradient(90deg, rgba(16,35,63,.05) 1px, transparent 1px)",
        "brand-radial": "radial-gradient(circle at 20% 0%, rgba(49,196,179,.22), transparent 32%), radial-gradient(circle at 80% 0%, rgba(47,128,237,.20), transparent 28%)",
      },
    },
  },
  plugins: [],
};

export default config;
