"use client";

/* Hallmark · macrostructure: Narrative Workflow · genre: editorial · designed-as-app */

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { DisclaimerBanner } from "@/components/ui/DisclaimerBanner";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Icon, type IconName } from "@/components/ui/icons";
import type { AdaptiveStatus } from "@/lib/tokens";
import { cn } from "@/lib/utils";

/**
 * F-00 — Landing page publik (sebelum login).
 *
 * Makrostruktur: **Narrative Workflow** — lima tahap bernomor menceritakan
 * siklus guru dari waktu ke waktu (NILAI → ANALISIS → PUTUSKAN → LATIH →
 * NILAI ULANG), bukan "hero tengah → 3 fitur → CTA".
 *
 * Aturan penting:
 * - Rute `/` publik, TANPA panggilan API backend/database (halaman statis).
 * - **Mode siswa dihapus** (keputusan disetujui): tidak ada toggle persona dan
 *   tidak ada panel konten anak. Diganti dua CTA: "Masuk" dan "Daftar".
 * - Bila guru sudah login, CTA berubah menjadi "Ke Dashboard".
 * - Tiga DisclaimerBanner dipertahankan (teks persis).
 * - Teks bebas kode PRD (tanpa BR-xx/§/nama engine).
 */

interface Stage {
  no: string;
  name: string;
  title: string;
  body: string;
  icon: IconName;
  /** Anotasi ringkas: apa yang terlihat guru di tahap ini (bahasa pengguna). */
  note: string;
}

const STAGES: Stage[] = [
  {
    no: "01",
    name: "NILAI",
    title: "Siswa membaca, BacaLaras mendengarkan",
    body: "Siswa membaca teks bergambar dengan suara nyaring. Rekaman diubah menjadi dua ukuran yang mudah dipahami: kelancaran (WCPM) dan akurasi membaca.",
    icon: "mic",
    note: "WCPM · Akurasi",
  },
  {
    no: "02",
    name: "ANALISIS",
    title: "Jawaban dinilai dari tiga sisi",
    body: "Pertanyaan pemahaman menilai apakah siswa menemukan informasi, memahami isi, dan bisa menilai isi bacaan — bukan sekadar menjawab benar atau salah.",
    icon: "book-open",
    note: "Menemukan · Memahami · Menilai",
  },
  {
    no: "03",
    name: "PUTUSKAN",
    title: "Status yang jelas, bukan kotak hitam",
    body: "Aturan yang transparan menentukan langkah tiap siswa: perlu pendampingan, tetap di level yang sama, atau siap naik ke bacaan berikutnya.",
    icon: "sparkles",
    note: "Rekomendasi per siswa",
  },
  {
    no: "04",
    name: "LATIH",
    title: "Guru langsung tahu harus apa",
    body: "Bukan sekadar angka. Guru melihat siapa yang perlu perhatian lebih dulu dan latihan seperti apa yang cocok untuknya.",
    icon: "lifebuoy",
    note: "Daftar prioritas",
  },
  {
    no: "05",
    name: "NILAI ULANG",
    title: "Perkembangan terlihat dari waktu ke waktu",
    body: "Satu asesmen hanyalah potret sesaat. Dengan mengulang siklus ini sepanjang tahun, guru bisa melihat kemajuan tiap siswa.",
    icon: "arrow-up-circle",
    note: "Grafik perkembangan",
  },
];

/** Status yang mungkin muncul — label Indonesia, tanpa jargon engine. */
const SAMPLE_STATUSES: (AdaptiveStatus | null)[] = [
  "INTERVENE",
  "STAY",
  "PROMOTION_CANDIDATE",
  "PROMOTE",
  null,
];

/** Disclaimer wajib F-00 (teks persis). */
const DISCLAIMER_TEXT = {
  medical: "BacaLaras bukan alat diagnosis klinis atau gangguan bicara.",
  threshold:
    "Ambang status (mis. 90%, 95%, 80%) adalah aturan desain MVP, bukan standar nasional Indonesia.",
  hasbrouck:
    "Referensi Hasbrouck–Tindal bukan benchmark normatif nasional Indonesia.",
} as const;

/** Gaya CTA utama (selaras <Button variant="primary">) untuk <Link>. */
const CTA_PRIMARY =
  "inline-flex h-12 items-center justify-center gap-2 rounded-md bg-brand-600 px-6 text-base font-semibold text-white transition-colors hover:bg-brand-700 active:bg-brand-800 focus-visible:outline-none";

/** Gaya CTA sekunder (garis + tinta). */
const CTA_SECONDARY =
  "inline-flex h-12 items-center justify-center gap-2 rounded-md border border-slate-200 bg-paper px-6 text-base font-semibold text-brand-700 transition-colors hover:border-brand-200 hover:bg-brand-50 focus-visible:outline-none";

export function LandingPage({ isLoggedIn }: { isLoggedIn: boolean }) {
  return (
    <div className="min-h-screen bg-paper">
      <Masthead isLoggedIn={isLoggedIn} />
      <Opening isLoggedIn={isLoggedIn} />
      <Workflow />
      <Closer isLoggedIn={isLoggedIn} />
      <Footer />
    </div>
  );
}

/* ───────────────────────────── Masthead ───────────────────────────── */

function Masthead({ isLoggedIn }: { isLoggedIn: boolean }) {
  return (
    <header className="border-b border-paper-200">
      <div className="mx-auto flex w-full max-w-5xl items-center justify-between gap-4 px-5 py-4 sm:px-8">
        <Link
          href="/"
          className="flex items-center gap-2.5 rounded-md focus-visible:outline-none"
          aria-label="BacaLaras — beranda"
        >
          <span className="flex h-9 w-9 items-center justify-center rounded-md bg-slate-900 text-paper">
            <Icon name="book-open" size={20} />
          </span>
          <span className="font-serif text-2xl font-semibold tracking-tight text-slate-900">
            BacaLaras
          </span>
        </Link>

        <nav className="flex items-center gap-2" aria-label="Navigasi utama">
          {isLoggedIn ? (
            <Link href="/dashboard" className={cn(CTA_SECONDARY, "h-11 px-4 text-sm")}>
              <Icon name="layout-dashboard" size={18} />
              Ke Dashboard
            </Link>
          ) : (
            <>
              <Link
                href="/login"
                className="inline-flex h-11 items-center rounded-md px-3 text-sm font-semibold text-slate-700 transition-colors hover:text-brand-700 focus-visible:outline-none"
              >
                Masuk
              </Link>
              <Link href="/signup" className={cn(CTA_PRIMARY, "h-11 px-4 text-sm")}>
                Daftar
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}

/* ─────────────────────────── Opening statement ─────────────────────────── */

function Opening({ isLoggedIn }: { isLoggedIn: boolean }) {
  const reduce = useReducedMotion();
  const rise = reduce
    ? { initial: { opacity: 0 }, animate: { opacity: 1 } }
    : { initial: { opacity: 0, y: 16 }, animate: { opacity: 1, y: 0 } };

  return (
    <section className="mx-auto w-full max-w-5xl px-5 pb-14 pt-14 sm:px-8 sm:pb-20 sm:pt-24">
      <div className="max-w-3xl">
        <motion.p
          {...rise}
          transition={{ duration: 0.36, ease: [0.22, 1, 0.36, 1] }}
          className="flex items-center gap-3 text-sm font-medium text-slate-500"
        >
          <span aria-hidden className="h-px w-8 bg-brand-500" />
          Asesmen membaca untuk SD kelas 1–3
        </motion.p>

        <motion.h1
          {...rise}
          transition={{ duration: 0.36, delay: 0.06, ease: [0.22, 1, 0.36, 1] }}
          className="mt-6 font-serif text-4xl font-semibold leading-[1.08] tracking-tight text-slate-900 sm:text-5xl md:text-6xl"
        >
          Anak membaca. BacaLaras mendengarkan.
          <span className="block text-brand-700">Guru memutuskan.</span>
        </motion.h1>

        <motion.p
          {...rise}
          transition={{ duration: 0.36, delay: 0.12, ease: [0.22, 1, 0.36, 1] }}
          className="mt-6 max-w-2xl text-lg leading-relaxed text-slate-600"
        >
          Menilai kelancaran membaca satu per satu itu berat. BacaLaras mengubah
          satu sesi membaca singkat menjadi gambaran yang rapi dan terukur —
          lengkap dengan langkah berikutnya untuk tiap siswa.
        </motion.p>

        <motion.div
          {...rise}
          transition={{ duration: 0.36, delay: 0.18, ease: [0.22, 1, 0.36, 1] }}
          className="mt-9 flex flex-wrap items-center gap-3"
        >
          {isLoggedIn ? (
            <Link href="/dashboard" className={CTA_PRIMARY}>
              <Icon name="layout-dashboard" size={20} />
              Ke Dashboard
            </Link>
          ) : (
            <>
              <Link href="/login" className={CTA_PRIMARY}>
                <Icon name="graduation-cap" size={20} />
                Masuk
              </Link>
              <Link href="/signup" className={CTA_SECONDARY}>
                Daftar
              </Link>
            </>
          )}
        </motion.div>

        <p className="mt-6 text-sm italic text-slate-500">Baca. Didengar. Dipahami.</p>
      </div>
    </section>
  );
}

/* ────────────────────────────── Workflow ────────────────────────────── */

function Workflow() {
  const reduce = useReducedMotion();

  return (
    <section aria-labelledby="workflow-heading" className="border-t border-paper-200 bg-paper-100/50">
      <div className="mx-auto w-full max-w-5xl px-5 py-16 sm:px-8 sm:py-24">
        <div className="max-w-2xl">
          <h2
            id="workflow-heading"
            className="font-serif text-h1 font-semibold tracking-tight text-slate-900"
          >
            Bagaimana BacaLaras bekerja
          </h2>
          <p className="mt-3 text-lg leading-relaxed text-slate-600">
            Lima tahap yang berulang sepanjang tahun. Bukan sekali pakai — makin
            sering dijalankan, makin jelas perkembangan tiap siswa.
          </p>
        </div>

        <ol className="mt-12">
          {STAGES.map((stage, i) => (
            <motion.li
              key={stage.no}
              initial={reduce ? { opacity: 0 } : { opacity: 0, x: -24 }}
              whileInView={reduce ? { opacity: 1 } : { opacity: 1, x: 0 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.36, delay: i * 0.04, ease: [0.22, 1, 0.36, 1] }}
              className={cn(
                "grid gap-4 py-8 sm:grid-cols-[9rem_1fr] sm:gap-10 sm:py-10",
                i > 0 && "border-t border-paper-200"
              )}
            >
              <div className="flex items-baseline gap-3 sm:flex-col sm:gap-1">
                <span className="font-serif text-3xl font-semibold tabular text-brand-600">
                  {stage.no}
                </span>
                <span className="text-sm font-semibold tracking-[0.18em] text-slate-500">
                  {stage.name}
                </span>
              </div>

              <div className="max-w-2xl">
                <div className="flex items-start gap-3">
                  <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-paper-200 bg-paper text-brand-600">
                    <Icon name={stage.icon} size={18} />
                  </span>
                  <h3 className="font-serif text-h3 font-semibold text-slate-800">
                    {stage.title}
                  </h3>
                </div>
                <p className="mt-3 text-base leading-relaxed text-slate-600">
                  {stage.body}
                </p>
                <p className="mt-3 text-sm text-slate-500">
                  <span className="font-medium text-slate-600">Yang terlihat: </span>
                  {stage.note}
                </p>
              </div>
            </motion.li>
          ))}
        </ol>

        {/* Hasil yang mungkin muncul — label Indonesia, tanpa jargon */}
        <div className="mt-4 border-t border-paper-200 pt-8">
          <p className="text-sm font-medium text-slate-600">
            Rekomendasi yang mungkin muncul:
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {SAMPLE_STATUSES.map((s, i) => (
              <StatusBadge key={s ?? `unassessed-${i}`} status={s} />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

/* ─────────────────────────────── Closer ─────────────────────────────── */

function Closer({ isLoggedIn }: { isLoggedIn: boolean }) {
  return (
    <section className="border-t border-paper-200">
      <div className="mx-auto w-full max-w-5xl px-5 py-14 sm:px-8 sm:py-20">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div className="max-w-xl">
            <h2 className="font-serif text-h2 font-semibold tracking-tight text-slate-900">
              Mulai dari satu kelas
            </h2>
            <p className="mt-2 text-base leading-relaxed text-slate-600">
              Coba dengan beberapa siswa dulu. Tidak perlu menyiapkan apa pun —
              cukup bacaan dan waktu beberapa menit per anak.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {isLoggedIn ? (
              <Link href="/dashboard" className={CTA_PRIMARY}>
                <Icon name="layout-dashboard" size={20} />
                Ke Dashboard
              </Link>
            ) : (
              <>
                <Link href="/login" className={CTA_PRIMARY}>
                  <Icon name="graduation-cap" size={20} />
                  Masuk
                </Link>
                <Link href="/signup" className={CTA_SECONDARY}>
                  Daftar
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

/* ─────────────────────────────── Footer ─────────────────────────────── */

function Footer() {
  return (
    <footer className="border-t border-paper-200 bg-paper-100/50">
      <div className="mx-auto w-full max-w-5xl px-5 py-12 sm:px-8">
        <h2 className="font-serif text-h3 font-semibold text-slate-700">
          Hal yang perlu diketahui
        </h2>
        <div className="mt-4 grid gap-3">
          <DisclaimerBanner kind="medical" text={DISCLAIMER_TEXT.medical} />
          <DisclaimerBanner kind="threshold" text={DISCLAIMER_TEXT.threshold} />
          <DisclaimerBanner kind="hasbrouck" text={DISCLAIMER_TEXT.hasbrouck} />
        </div>
        <p className="mt-8 text-xs text-slate-400">
          BacaLaras · Asesmen membaca adaptif untuk SD kelas 1–3
        </p>
      </div>
    </footer>
  );
}
