import type { Config } from "tailwindcss";

/**
 * BacaLaras Design Tokens — Tailwind Config
 *
 * Arah visual (Fase 2): "kertas hangat, tinta hangat, satu aksen terakota".
 * Palet OKLCH → hex, anchor hue 80 (oat hangat). Satu aksen (terakota).
 *
 * CATATAN: skala bawaan Tailwind (slate/rose/amber/violet/emerald/sky/teal/red/white)
 * sengaja DITIMPA dengan padanan hangat-tanah. Kelas lama (mis. `bg-rose-50`)
 * otomatis menjadi hangat tanpa mengubah nama kelas — termasuk di Mode Siswa.
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
        // Permukaan hangat seperti kertas (bukan putih dingin) — identitas BacaLaras.
        paper: {
          50: "#FDFAF4",
          100: "#F3EDE3",
          200: "#E7E0D3",
          300: "#DAD3C9",
          400: "#C5BCB1",
          500: "#A69D91",
          600: "#82796E",
          700: "#5F564D",
          800: "#3E372F",
          900: "#241E18",
          DEFAULT: "#F9F4EE",
        },
        // Netral hangat (tinta) — menggantikan slate dingin.
        slate: {
          50: "#FBF8F4",
          100: "#F2EEE7",
          200: "#E3DDD4",
          300: "#CAC3B9",
          400: "#9F978C",
          500: "#766D62",
          600: "#5A5147",
          700: "#413931",
          800: "#2C251E",
          900: "#1B1510",
          950: "#0D0805",
        },
        // Permukaan kartu: paper bertint, bukan #ffffff murni.
        white: "#FDFAF4",
        // Satu aksen: terakota.
        brand: {
          50: "#FEEEE6",
          100: "#FADED1",
          200: "#F2C2AB",
          300: "#E69D7D",
          400: "#D47A51",
          500: "#BD582E",
          600: "#A14118",
          700: "#833314",
          800: "#662610",
          900: "#4A1A0A",
        },
        accent: {
          400: "#F37D65",
          500: "#DE5E4A",
          600: "#BB4536",
        },
        // Keluarga status — hue hangat-tanah, tetap terbedakan (ikon + label tetap).
        rose: {
          50: "#FCEEED",
          100: "#FCE1DE",
          200: "#F7C7C4",
          300: "#E9A2A0",
          400: "#CD7576",
          500: "#B45055",
          600: "#973A42",
          700: "#762B33",
          800: "#591F26",
          900: "#3E141A",
        },
        amber: {
          50: "#FCF4E6",
          100: "#FCE8CA",
          200: "#F6D19C",
          300: "#EAB771",
          400: "#D99E4D",
          500: "#C2832D",
          600: "#A3691B",
          700: "#835010",
          800: "#623A0D",
          900: "#46290B",
        },
        violet: {
          50: "#F6EFF9",
          100: "#EFE2F7",
          200: "#DFCBED",
          300: "#C6ABDA",
          400: "#A383BC",
          500: "#8663A0",
          600: "#6B4B82",
          700: "#523865",
          800: "#3D294B",
          900: "#291A33",
        },
        emerald: {
          50: "#EAF5ED",
          100: "#DAEEDF",
          200: "#BDDEC4",
          300: "#97C5A1",
          400: "#6CA177",
          500: "#4B8358",
          600: "#346841",
          700: "#255030",
          800: "#1B3B23",
          900: "#102816",
        },
        sky: {
          50: "#EBF3F9",
          100: "#D9EBF6",
          200: "#BCD9EB",
          300: "#94BED6",
          400: "#669AB5",
          500: "#457C98",
          600: "#2C627B",
          700: "#1E4B60",
          800: "#163747",
          900: "#0C2531",
        },
        teal: {
          50: "#E9F5F1",
          100: "#D6EEE5",
          200: "#B8DED0",
          300: "#90C5B1",
          400: "#61A18B",
          500: "#3D846D",
          600: "#266854",
          700: "#195040",
          800: "#113B2F",
          900: "#09281F",
        },
        red: {
          50: "#FEEEEB",
          100: "#FFE0DB",
          200: "#FAC6C0",
          300: "#ECA19A",
          400: "#D2736E",
          500: "#C04C4C",
          600: "#A43237",
          700: "#82232A",
          800: "#631A20",
          900: "#461116",
        },
        // Token semantik domain (presentasi) — dipetakan ke keluarga hangat.
        status: {
          intervene: "#973A42",
          stay: "#C2832D",
          candidate: "#6B4B82",
          promote: "#346841",
        },
        competency: {
          retrieve: "#2C627B",
          interpret: "#6B4B82",
          reflect: "#266854",
        },
        word: {
          correct: "#346841",
          incorrect: "#A3691B", // netral-hangat, bukan merah
          neutral: "#5A5147",
          active: "#BD582E",
        },
      },
      fontFamily: {
        // Pasangan 2 famili: Newsreader (display + bacaan) · Geist (UI/angka).
        display: ["var(--font-newsreader)", "Newsreader", "ui-serif", "Georgia", "serif"],
        serif: ["var(--font-newsreader)", "Newsreader", "ui-serif", "Georgia", "serif"],
        sans: ["var(--font-geist)", "Geist", "ui-sans-serif", "system-ui", "sans-serif"],
        reading: ["var(--font-newsreader)", "Newsreader", "ui-serif", "Georgia", "serif"],
      },
      fontSize: {
        // Ukuran bacaan siswa TIDAK diubah (dipakai Mode Siswa).
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
        // Radius bervariasi per peran (bukan satu radius seragam).
        sm: "4px",
        DEFAULT: "6px",
        md: "6px",
        lg: "10px",
        xl: "14px",
      },
      boxShadow: {
        // Satu bahasa elevasi "bisikan" — kedalaman utama dari hairline & permukaan.
        xs: "0 1px 2px rgba(44,37,30,.06)",
        sm: "0 1px 2px rgba(44,37,30,.06)",
        md: "0 2px 6px rgba(44,37,30,.07)",
        lg: "0 8px 24px rgba(44,37,30,.10)",
        focus: "0 0 0 3px rgba(189,88,46,.35)",
      },
      transitionTimingFunction: {
        base: "cubic-bezier(.2,.8,.2,1)",
        out: "cubic-bezier(.22,1,.36,1)",
        in: "cubic-bezier(.55,0,1,.45)",
      },
      transitionDuration: {
        micro: "120ms",
        minor: "220ms",
        major: "360ms",
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
