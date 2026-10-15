import type { Config } from "tailwindcss";

/**
 * BacaLaras Design Tokens — Tailwind Config
 * Sumber: design-system.md (v2.2)
 */
const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Latar hangat seperti kertas (bukan putih-biru dingin) — identitas BacaLaras.
        paper: {
          DEFAULT: "#FAF7F0",
          50: "#FDFCF8",
          100: "#F4EFE4",
          200: "#E9E1D2",
        },
        brand: {
          50: "#EFF6FF",
          100: "#DBEAFE",
          200: "#BFDBFE",
          300: "#93C5FD",
          400: "#60A5FA",
          500: "#3B82F6",
          600: "#2563EB",
          700: "#1D4ED8",
          800: "#1E40AF",
          900: "#1E3A8A",
        },
        accent: {
          400: "#FBBF24",
          500: "#F59E0B",
          600: "#D97706",
        },
        status: {
          intervene: "#E11D48", // rose-600
          stay: "#F59E0B",      // amber-500
          candidate: "#7C3AED", // violet-600
          promote: "#059669",   // emerald-600
        },
        competency: {
          retrieve: "#0EA5E9",  // sky-500
          interpret: "#8B5CF6", // violet-500
          reflect: "#14B8A6",   // teal-500
        },
        word: {
          correct: "#059669",   // emerald-600
          incorrect: "#D97706", // amber-600 (netral, bukan merah)
          neutral: "#64748B",   // slate-500
          active: "#3B82F6",    // blue-500
        },
      },
      fontFamily: {
        display: ["Nunito", "ui-rounded", "system-ui", "sans-serif"],
        // Judul halaman & teks bacaan memakai serif/semi-serif (identitas editorial).
        serif: ["Lora", "Georgia", "ui-serif", "serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
        reading: ["Andika", "Lexend", "sans-serif"],
      },
      fontSize: {
        metric: ["2.25rem", { lineHeight: "1.1", fontWeight: "700" }],
        display: ["2.5rem", { lineHeight: "1.15", fontWeight: "700" }],
        h1: ["2rem", { lineHeight: "1.2", fontWeight: "700" }],
        h2: ["1.5rem", { lineHeight: "1.25", fontWeight: "600" }],
        h3: ["1.25rem", { lineHeight: "1.35", fontWeight: "600" }],
        "reading-1": ["2rem", { lineHeight: "1.9", fontWeight: "500" }],
        "reading-2": ["1.75rem", { lineHeight: "1.9", fontWeight: "500" }],
        "reading-3": ["1.5rem", { lineHeight: "1.9", fontWeight: "500" }],
      },
      borderRadius: {
        sm: "6px",
        md: "10px",
        lg: "16px",
        xl: "24px",
      },
      boxShadow: {
        xs: "0 1px 2px rgba(15,23,42,.05)",
        sm: "0 1px 2px rgba(15,23,42,.05)",
        md: "0 2px 8px rgba(15,23,42,.07)",
        lg: "0 12px 32px rgba(15,23,42,.10)",
        focus: "0 0 0 3px rgba(59,130,246,.35)",
      },
      transitionTimingFunction: {
        base: "cubic-bezier(.2,.8,.2,1)",
      },
      zIndex: {
        sticky: "10",
        dropdown: "20",
        overlay: "40",
        modal: "50",
        toast: "60",
        recording: "70",
      },
    },
  },
  plugins: [],
};

export default config;
