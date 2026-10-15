import type { Metadata } from "next";
import "./globals.css";

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
    <html lang="id">
      <body className="min-h-screen bg-paper font-sans text-slate-800 antialiased">
        {children}
      </body>
    </html>
  );
}
