"use client";

import { useState, type ReactNode } from "react";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { DisclaimerBanner } from "@/components/ui/DisclaimerBanner";
import { Icon, type IconName } from "@/components/ui/icons";
import { STATUS_META } from "@/lib/tokens";
import { cn } from "@/lib/utils";

/**
 * F-00 — Landing page publik (sebelum login).
 *
 * Aturan penting:
 * - Rute `/` publik, TANPA panggilan API backend/database (halaman statis).
 * - Toggle persona "Saya Guru" | "Saya Siswa"; default **Guru** (SSR), sehingga
 *   konten Guru tetap terbaca bila JavaScript lambat/gagal dimuat.
 * - Konten Siswa memakai bahasa ramah anak 6–9 tahun, tanpa istilah teknis.
 * - Tidak ada tombol/form login untuk Siswa (siswa tidak punya akun di MVP).
 * - Memakai token desain yang sudah ada (Button-style, Card, DisclaimerBanner,
 *   ikon, warna brand/paper) — tanpa sistem desain baru.
 */

type Persona = "guru" | "siswa";

interface Step {
  icon: IconName;
  title: string;
  body: string;
}

const GURU_STEPS: Step[] = [
  {
    icon: "book-open",
    title: "1. Siswa membaca teks",
    body: "Bacaan tersedia untuk Level 1–3 sesuai jenjang kelas 1–3.",
  },
  {
    icon: "mic",
    title: "2. BacaLaras mendengarkan",
    body: "Suara siswa direkam, lalu dihitung WCPM dan Akurasi secara otomatis.",
  },
  {
    icon: "check-circle",
    title: "3. Siswa menjawab pertanyaan",
    body: "Pertanyaan pemahaman mencakup Retrieve, Interpret, dan Reflect.",
  },
  {
    icon: "sparkles",
    title: "4. Guru menerima rekomendasi",
    body: "Langkah berikutnya disarankan berdasarkan hasil asesmen.",
  },
];

const SISWA_STEPS: Step[] = [
  {
    icon: "book-open",
    title: "Baca",
    body: "Baca teksnya dengan suara nyaring.",
  },
  {
    icon: "mic",
    title: "Rekam",
    body: "Tekan tombol rekam, lalu baca lagi dengan tenang.",
  },
  {
    icon: "check-circle",
    title: "Jawab",
    body: "Jawab pertanyaan tentang ceritanya.",
  },
];

/** Alur berulang ASSESS → ANALYZE → DECIDE → PRACTICE → REASSESS (F-00). */
const GURU_FLOW = ["ASSESS", "ANALYZE", "DECIDE", "PRACTICE", "REASSESS"];

/** Disclaimer wajib F-00 (teks persis PRD Bagian 6). */
const DISCLAIMER_TEXT = {
  medical: "BacaLaras bukan alat diagnosis klinis atau gangguan bicara.",
  threshold:
    "Ambang status (mis. 90%, 95%, 80%) adalah aturan desain MVP, bukan standar nasional Indonesia.",
  hasbrouck:
    "Referensi Hasbrouck–Tindal bukan benchmark normatif nasional Indonesia.",
} as const;

/** Gaya tombol utama (sama dengan <Button variant="primary" size="lg">),
 *  dipakai pada <Link> agar CTA tetap berfungsi tanpa JavaScript. */
const CTA_CLASS =
  "inline-flex h-12 items-center justify-center gap-2 rounded-md bg-brand-500 px-6 text-base font-semibold text-white transition-colors hover:bg-brand-600 active:bg-brand-700 focus-visible:outline-none";

export function LandingPage({ isLoggedIn }: { isLoggedIn: boolean }) {
  const [persona, setPersona] = useState<Persona>("guru");

  return (
    <div className="flex min-h-screen flex-col bg-paper">
      {/* ---------------- Hero (semua persona) ---------------- */}
      <header className="border-b border-paper-200 bg-paper-50">
        <div className="mx-auto w-full max-w-5xl px-4 py-12 sm:px-6 sm:py-16">
          <div className="flex flex-col items-center text-center">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-brand-500 text-white">
              <Icon name="book-open" size={30} />
            </div>
            <h1 className="font-display text-4xl font-extrabold tracking-tight text-slate-800 sm:text-5xl">
              BacaLaras
            </h1>
            <p className="mt-2 text-sm font-medium uppercase tracking-widest text-brand-600">
              Baca. Didengar. Dipahami.
            </p>
            <p className="mt-5 max-w-2xl text-lg leading-relaxed text-slate-600">
              Anak membaca, BacaLaras mendengarkan, guru mendapatkan gambaran
              kemampuan literasi dan rekomendasi latihan.
            </p>

            {/* Toggle persona — konten berganti tanpa reload. */}
            <div
              role="tablist"
              aria-label="Pilih persona"
              className="mt-8 inline-flex rounded-lg border border-paper-200 bg-white p-1 shadow-xs"
            >
              <PersonaTab
                id="tab-guru"
                selected={persona === "guru"}
                onSelect={() => setPersona("guru")}
              >
                Saya Guru
              </PersonaTab>
              <PersonaTab
                id="tab-siswa"
                selected={persona === "siswa"}
                onSelect={() => setPersona("siswa")}
              >
                Saya Siswa
              </PersonaTab>
            </div>
          </div>
        </div>
      </header>

      {/* ---------------- Konten persona ---------------- */}
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-12 sm:px-6 sm:py-16">
        {persona === "guru" ? (
          <section
            id="panel-guru"
            role="tabpanel"
            aria-labelledby="tab-guru"
            className="space-y-12"
          >
            {/* Masalah */}
            <Card>
              <h2 className="font-serif text-h2 font-semibold text-slate-800">
                Menilai membaca satu per satu itu berat
              </h2>
              <p className="mt-2 max-w-3xl text-base leading-relaxed text-slate-600">
                Asesmen membaca manual memakan waktu, sulit konsisten, dan terasa
                subjektif ketika siswanya banyak. BacaLaras membantu guru
                mendapatkan gambaran awal yang lebih rapi dan terukur.
              </p>
            </Card>

            {/* Cara kerja */}
            <div>
              <h2 className="font-serif text-h2 font-semibold text-slate-800">
                Cara kerja
              </h2>
              <p className="mt-1 text-sm text-slate-500">Empat langkah sederhana.</p>
              <ol className="mt-6 grid gap-5 sm:grid-cols-2">
                {GURU_STEPS.map((s) => (
                  <li key={s.title} className="flex gap-3">
                    <span className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-50 text-brand-600">
                      <Icon name={s.icon} size={20} />
                    </span>
                    <div>
                      <p className="font-semibold text-slate-800">{s.title}</p>
                      <p className="mt-0.5 text-sm leading-relaxed text-slate-600">
                        {s.body}
                      </p>
                    </div>
                  </li>
                ))}
              </ol>
            </div>

            {/* Yang Anda dapatkan */}
            <Card>
              <h2 className="font-serif text-h2 font-semibold text-slate-800">
                Yang Anda dapatkan
              </h2>
              <ul className="mt-4 grid gap-x-8 gap-y-2 text-sm text-slate-700 sm:grid-cols-2">
                <Benefit text="WCPM (kata benar per menit)" />
                <Benefit text="Akurasi membaca" />
                <Benefit text="Pemahaman: Retrieve, Interpret, Reflect" />
                <Benefit text="Grafik perkembangan dari waktu ke waktu" />
                <Benefit text="Referensi Hasbrouck–Tindal (P25/P50)" />
                <Benefit text="Rekomendasi tindakan berikutnya" />
              </ul>

              <p className="mt-6 text-sm font-medium text-slate-600">
                Rekomendasi yang mungkin muncul:
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {Object.values(STATUS_META).map((meta) => (
                  <span
                    key={meta.engine}
                    className={cn(
                      "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm font-medium",
                      meta.bg,
                      meta.text,
                      meta.border
                    )}
                  >
                    <Icon name={meta.icon} size={15} />
                    {meta.label}
                  </span>
                ))}
              </div>
            </Card>

            {/* Alur berulang */}
            <div>
              <h2 className="font-serif text-h2 font-semibold text-slate-800">
                Asesmen bisa diulang sepanjang tahun
              </h2>
              <p className="mt-1 max-w-3xl text-sm leading-relaxed text-slate-600">
                Satu asesmen hanyalah potret sesaat. Dengan mengulang alur di bawah
                ini berkali-kali dalam setahun, guru bisa melihat perkembangan
                siswa dari waktu ke waktu.
              </p>
              <ol className="mt-5 flex flex-wrap items-center gap-2">
                {GURU_FLOW.map((label, i) => (
                  <li key={label} className="flex items-center gap-2">
                    <span className="rounded-md border border-paper-200 bg-white px-3 py-1.5 text-xs font-semibold tracking-wide text-slate-700">
                      {label}
                    </span>
                    {i < GURU_FLOW.length - 1 && (
                      <Icon name="arrow-right" size={16} className="text-slate-400" />
                    )}
                  </li>
                ))}
              </ol>
            </div>

            {/* CTA */}
            <div className="rounded-lg border border-brand-100 bg-brand-50 p-6 text-center">
              <p className="text-base font-medium text-slate-700">
                Siap mencoba BacaLaras bersama kelas Anda?
              </p>
              <Link
                href={isLoggedIn ? "/dashboard" : "/login"}
                className={cn(CTA_CLASS, "mt-4")}
              >
                <Icon name={isLoggedIn ? "layout-dashboard" : "graduation-cap"} size={20} />
                {isLoggedIn ? "Ke Dashboard" : "Masuk sebagai Guru"}
              </Link>
            </div>
          </section>
        ) : (
          <section
            id="panel-siswa"
            role="tabpanel"
            aria-labelledby="tab-siswa"
            className="space-y-10"
          >
            {/* Sapaan */}
            <Card className="text-center">
              <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-accent-400/20 text-accent-600">
                <Icon name="sparkles" size={28} />
              </div>
              <h2 className="font-display text-h2 font-bold text-slate-800">
                Halo, teman!
              </h2>
              <p className="mx-auto mt-2 max-w-xl text-base leading-relaxed text-slate-600">
                Di sini kamu bisa membaca cerita. BacaLaras akan mendengarkan
                suaramu. Santai saja, ya.
              </p>
            </Card>

            {/* 3 langkah bergambar */}
            <div>
              <h2 className="text-center font-serif text-h2 font-semibold text-slate-800">
                Caranya mudah
              </h2>
              <ul className="mt-6 grid gap-5 sm:grid-cols-3">
                {SISWA_STEPS.map((s) => (
                  <li
                    key={s.title}
                    className="flex flex-col items-center rounded-lg border border-paper-200 bg-white p-6 text-center"
                  >
                    <span className="flex h-14 w-14 items-center justify-center rounded-full bg-brand-50 text-brand-600">
                      <Icon name={s.icon} size={28} />
                    </span>
                    <p className="mt-3 font-display text-lg font-bold text-slate-800">
                      {s.title}
                    </p>
                    <p className="mt-1 text-sm leading-relaxed text-slate-600">
                      {s.body}
                    </p>
                  </li>
                ))}
              </ul>
            </div>

            {/* Tenang saja */}
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-6 text-center">
              <div className="mx-auto mb-2 flex h-11 w-11 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
                <Icon name="check-circle" size={24} />
              </div>
              <p className="mx-auto max-w-xl text-base leading-relaxed text-emerald-900">
                Ini bukan ujian yang menakutkan. Kalau perlu, kamu boleh membaca
                sekali lagi nanti. Gurumu akan membantu.
              </p>
            </div>

            {/* CTA siswa — pesan, bukan tombol login */}
            <div className="rounded-lg border border-paper-200 bg-white p-6 text-center">
              <p className="font-display text-lg font-bold text-slate-800">
                Minta gurumu membuka bacaan untukmu ya.
              </p>
            </div>
          </section>
        )}
      </main>

      {/* ---------------- Footer (semua persona) ---------------- */}
      <footer className="border-t border-paper-200 bg-paper-50">
        <div className="mx-auto w-full max-w-5xl px-4 py-10 sm:px-6">
          <h2 className="font-serif text-h3 font-semibold text-slate-700">
            Hal yang perlu diketahui
          </h2>
          <div className="mt-4 grid gap-3">
            <DisclaimerBanner kind="medical" text={DISCLAIMER_TEXT.medical} />
            <DisclaimerBanner kind="threshold" text={DISCLAIMER_TEXT.threshold} />
            <DisclaimerBanner kind="hasbrouck" text={DISCLAIMER_TEXT.hasbrouck} />
          </div>
          <p className="mt-8 text-center text-xs text-slate-400">
            BacaLaras · Asesmen membaca adaptif untuk SD kelas 1–3
          </p>
        </div>
      </footer>
    </div>
  );
}

/** Tab persona dengan aksesibilitas `tablist`/`tab`. */
function PersonaTab({
  id,
  selected,
  onSelect,
  children,
}: {
  id: string;
  selected: boolean;
  onSelect: () => void;
  children: ReactNode;
}) {
  return (
    <button
      id={id}
      type="button"
      role="tab"
      aria-selected={selected}
      aria-controls={id === "tab-guru" ? "panel-guru" : "panel-siswa"}
      onClick={onSelect}
      className={cn(
        "inline-flex h-11 items-center justify-center gap-2 rounded-md px-5 text-sm font-semibold transition-colors focus-visible:outline-none",
        selected
          ? "bg-brand-500 text-white"
          : "bg-transparent text-slate-600 hover:bg-paper-100"
      )}
    >
      {children}
    </button>
  );
}

/** Baris daftar "Yang Anda dapatkan". */
function Benefit({ text }: { text: string }) {
  return (
    <li className="flex items-start gap-2">
      <Icon name="check-circle" size={18} className="mt-0.5 shrink-0 text-emerald-600" />
      <span>{text}</span>
    </li>
  );
}
