import type { Metadata } from "next";
import { Newsreader, Geist } from "next/font/google";
import "./globals.css";

/**
 * Tipografi — pasangan 2 famili (arah Fase 2).
 * - Newsreader: judul & teks bacaan (serif reading-first, optical-size).
 * - Geist: UI, tabel, dan angka (angka tabular).
 * Dimuat lewat next/font (self-host, non-blocking) — menggantikan @import Google Fonts.
 */
// Keduanya variabel — tanpa daftar weight, sehingga semua bobot (termasuk
// font-extrabold di Mode Siswa) tersedia tanpa file tambahan.
const newsreader = Newsreader({
  subsets: ["latin"],
  style: ["normal", "italic"],
  variable: "--font-newsreader",
  display: "swap",
});

const geist = Geist({
  subsets: ["latin"],
  variable: "--font-geist",
  display: "swap",
});

export const metadata: Metadata = {
  title: "BacaLaras",
  description:
    "Adaptive Oral Reading Fluency & Literacy Assessment — anak membaca, BacaLaras mendengarkan.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="id" className={`${newsreader.variable} ${geist.variable}`}>
      <body className="min-h-screen bg-paper font-sans text-slate-800 antialiased">
        {children}
      </body>
    </html>
  );
}
