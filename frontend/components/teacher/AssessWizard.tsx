"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Stepper } from "@/components/ui/Stepper";
import { StudentPicker, type PickableStudent } from "@/components/teacher/StudentPicker";
import { ReadingCard } from "@/components/teacher/ReadingCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/icons";
import { createAssessment, ApiError } from "@/lib/api";
import {
  isLocked,
  lockedReason,
  type StudentProgression,
} from "@/lib/progression";
import type { ReadingText } from "@/lib/types";

const STEPS = [
  { id: "student", label: "Pilih Siswa" },
  { id: "reading", label: "Pilih Bacaan" },
  { id: "handover", label: "Serahkan ke Siswa" },
];

/**
 * Cadangan bila server tidak mengirim progresi untuk seorang siswa: tangga
 * selalu mulai di Level 1, jadi ini aman — bukan "semua terbuka".
 */
const FALLBACK_PROGRESSION: StudentProgression = {
  unlockedLevel: 1,
  pendingTitles: [],
};

/**
 * AssessWizard — alur "Mulai Asesmen" guru (T-08) dalam 3 langkah:
 * 1. Pilih Siswa → 2. Pilih Bacaan (level disarankan disorot) → 3. Serahkan ke Siswa.
 *
 * Sesuai F2 (user-flow): profil siswa → pilih bacaan → serahkan perangkat.
 * Tombol "Mulai Asesmen" nonaktif sampai siswa DAN bacaan dipilih.
 *
 * Gerbang naik level: bacaan di atas level terbuka siswa tidak bisa dipilih dan
 * diurutkan paling bawah. Ini hanya cermin tampilan — penegaknya backend
 * (`POST /assessments` → 409), yang pesannya tetap ditampilkan lewat `startError`.
 */
export function AssessWizard({
  students,
  readings,
  initialStudentId,
  initialReadingId,
  recommendedLevels = {},
  progressionByStudent = {},
}: {
  students: PickableStudent[];
  readings: ReadingText[];
  initialStudentId?: string;
  /** Bacaan yang sudah dipilih (mis. dari tombol "Pakai untuk asesmen" di katalog). */
  initialReadingId?: string;
  /** Level bacaan yang disarankan per siswa (dihitung server dari riwayat asesmen). */
  recommendedLevels?: Record<string, 1 | 2 | 3>;
  /** Level terbuka + sisa bacaan per siswa (dihitung server, lihat lib/progression.ts). */
  progressionByStudent?: Record<string, StudentProgression>;
}) {
  const router = useRouter();
  const [step, setStep] = React.useState(
    initialStudentId ? (initialReadingId ? 2 : 1) : 0
  );
  const [studentId, setStudentId] = React.useState<string | undefined>(initialStudentId);
  const [readingId, setReadingId] = React.useState<string | undefined>(initialReadingId);
  const [levelFilter, setLevelFilter] = React.useState<"all" | 1 | 2 | 3>("all");
  const [themeFilter, setThemeFilter] = React.useState<string>("all");
  const [starting, setStarting] = React.useState(false);
  const [startError, setStartError] = React.useState("");

  const student = students.find((s) => s.id === studentId);
  const recommendedLevel = student ? recommendedLevels[student.id] : undefined;
  const progression = student
    ? progressionByStudent[student.id] ?? FALLBACK_PROGRESSION
    : FALLBACK_PROGRESSION;

  /** Bacaan di atas level terbuka siswa → tidak bisa dipilih. */
  const lockedIds = React.useMemo(() => {
    const ids = new Set<string>();
    for (const r of readings) if (isLocked(progression, r)) ids.add(r.id);
    return ids;
  }, [readings, progression]);

  const themes = React.useMemo(
    () => Array.from(new Set(readings.map((r) => r.theme))).sort(),
    [readings]
  );

  const visibleReadings = readings.filter((r) => {
    const byLevel = levelFilter === "all" || r.level === levelFilter;
    const byTheme = themeFilter === "all" || r.theme === themeFilter;
    return byLevel && byTheme;
  });

  // Urutkan: level disarankan dulu, lalu level terbuka, terakhir yang terkunci.
  const sortedReadings = [...visibleReadings].sort((a, b) => {
    const rank = (r: ReadingText) =>
      r.level === recommendedLevel ? 0 : lockedIds.has(r.id) ? 2 : 1;
    return rank(a) - rank(b) || a.level - b.level;
  });

  const selectedReading = readings.find((r) => r.id === readingId);
  const canStart = Boolean(
    student && selectedReading && !lockedIds.has(selectedReading.id)
  );

  function pickStudent(id: string) {
    setStudentId(id);
    // Bacaan yang dipilih dari katalog tetap dipertahankan; selain itu reset
    // agar guru memilih ulang sesuai level siswa. Pilihan juga dibatalkan bila
    // bacaan itu terkunci untuk siswa yang baru dipilih — level terbuka bisa
    // lebih rendah dari siswa sebelumnya.
    const next = progressionByStudent[id] ?? FALLBACK_PROGRESSION;
    const chosen = readings.find((r) => r.id === readingId);
    if (!initialReadingId || (chosen && isLocked(next, chosen))) {
      setReadingId(undefined);
      setStep((s) => (s === 2 ? 1 : s));
    }
  }

  /** Buat sesi asesmen di backend, lalu buka layar siswa (S-01/S-02). */
  async function startAssessment() {
    if (!student || !selectedReading) return;
    setStarting(true);
    setStartError("");
    try {
      const created = await createAssessment(student.id, selectedReading.id);
      const qs = new URLSearchParams();
      qs.set("assessment", created.id);
      qs.set("reading", selectedReading.id);
      qs.set("student", student.id);
      router.push(`/assess/start?${qs.toString()}`);
    } catch (e) {
      setStarting(false);
      setStartError(
        e instanceof ApiError
          ? `Gagal memulai asesmen: ${e.detail}`
          : "Gagal memulai asesmen. Periksa koneksi lalu coba lagi."
      );
    }
  }

  return (
    <div className="space-y-6">
      <Stepper steps={STEPS} current={step} />

      {/* Langkah 1 — Pilih Siswa */}
      {step === 0 && (
        <section className="space-y-4">
          <div>
            <h2 className="font-serif text-h3 font-semibold text-slate-900">Pilih siswa</h2>
            <p className="text-sm text-slate-500">
              Siapa yang akan melakukan asesmen membaca hari ini?
            </p>
          </div>
          <StudentPicker students={students} selectedId={studentId} onSelect={pickStudent} />
          <div className="flex justify-end">
            <Button
              variant="primary"
              size="md"
              disabled={!student}
              onClick={() => setStep(1)}
            >
              Lanjut Pilih Bacaan
              <Icon name="arrow-right" size={18} />
            </Button>
          </div>
        </section>
      )}

      {/* Langkah 2 — Pilih Bacaan */}
      {step === 1 && student && (
        <section className="space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="font-serif text-h3 font-semibold text-slate-900">
                Pilih bacaan
              </h2>
              <p className="text-sm text-slate-500">
                {recommendedLevel
                  ? `Level ${recommendedLevel} disarankan untuk ${student.name}.`
                  : "Pilih bacaan yang sesuai."}
              </p>
              {lockedIds.size > 0 && (
                <p className="mt-1 flex items-start gap-1.5 text-sm text-slate-500">
                  <Icon name="lock" size={15} className="mt-0.5 shrink-0 text-slate-400" />
                  <span>
                    {student.name.split(" ")[0]} masih di Level {progression.unlockedLevel}.
                    Level {progression.unlockedLevel + 1} ke atas terkunci — tuntaskan dulu{" "}
                    {progression.pendingTitles.length > 0
                      ? `bacaan Level ${progression.unlockedLevel} yang belum selesai: ${progression.pendingTitles
                          .map((t) => `«${t}»`)
                          .join(", ")}.`
                      : `seluruh bacaan Level ${progression.unlockedLevel}.`}
                  </span>
                </p>
              )}
            </div>

            {/* Filter level & tema */}
            <div className="flex flex-wrap items-center gap-2">
              <label htmlFor="level-filter" className="text-xs font-medium text-slate-500">
                Level
              </label>
              <select
                id="level-filter"
                value={levelFilter}
                onChange={(e) =>
                  setLevelFilter(e.target.value === "all" ? "all" : (Number(e.target.value) as 1 | 2 | 3))
                }
                className="h-11 rounded-md border border-slate-200 bg-white px-3 text-sm focus-visible:outline-none"
              >
                <option value="all">Semua</option>
                <option value="1">Level 1</option>
                <option value="2">Level 2</option>
                <option value="3">Level 3</option>
              </select>

              <label htmlFor="theme-filter" className="text-xs font-medium text-slate-500">
                Tema
              </label>
              <select
                id="theme-filter"
                value={themeFilter}
                onChange={(e) => setThemeFilter(e.target.value)}
                className="h-11 rounded-md border border-slate-200 bg-white px-3 text-sm focus-visible:outline-none"
              >
                <option value="all">Semua</option>
                {themes.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div role="radiogroup" aria-label="Pilih bacaan" className="grid gap-3">
            {sortedReadings.length === 0 ? (
              <p className="rounded-md bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
                Tidak ada bacaan yang cocok dengan filter ini.
              </p>
            ) : (
              sortedReadings.map((r) => {
                const locked = lockedIds.has(r.id);
                return (
                  <ReadingCard
                    key={r.id}
                    reading={r}
                    selected={r.id === readingId}
                    recommended={recommendedLevel === r.level}
                    recommendedFor={student.name.split(" ")[0]}
                    locked={locked}
                    lockedReason={lockedReason(progression, r, student.name) ?? undefined}
                    onSelect={() => setReadingId(r.id)}
                  />
                );
              })
            )}
          </div>

          <div className="flex flex-wrap justify-between gap-2">
            <Button variant="ghost" size="md" onClick={() => setStep(0)}>
              <Icon name="arrow-left" size={18} />
              Kembali
            </Button>
            <Button
              variant="primary"
              size="md"
              disabled={!selectedReading}
              onClick={() => setStep(2)}
            >
              Lanjut
              <Icon name="arrow-right" size={18} />
            </Button>
          </div>
        </section>
      )}

      {/* Langkah 3 — Serahkan ke Siswa */}
      {step === 2 && student && selectedReading && (
        <section className="space-y-5">
          <div>
            <h2 className="font-serif text-h3 font-semibold text-slate-900">
              Serahkan perangkat ke siswa
            </h2>
            <p className="text-sm text-slate-500">
              Periksa ringkasan di bawah, lalu tekan tombol untuk membuka layar siswa.
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-lg border border-paper-200 bg-white p-5">
              <p className="text-xs font-semibold text-slate-500">
                Siswa
              </p>
              <p className="mt-1 font-serif text-h3 font-semibold text-slate-900">
                {student.name}
              </p>
              <p className="text-sm text-slate-500">
                {student.classLabel} · Tingkat {student.grade}
              </p>
              <div className="mt-3">
                <StatusBadge status={student.status} />
              </div>
            </div>

            <div className="rounded-lg border border-paper-200 bg-white p-5">
              <p className="text-xs font-semibold text-slate-500">
                Bacaan
              </p>
              <p className="mt-1 font-serif text-h3 font-semibold text-slate-900">
                {selectedReading.title}
              </p>
              <p className="text-sm text-slate-500">
                Level {selectedReading.level} · {selectedReading.wordCount} kata · Tema:{" "}
                {selectedReading.theme}
              </p>
            </div>
          </div>

          <div className="rounded-lg border border-brand-200 bg-brand-50 p-4 text-sm text-brand-800">
            <p className="flex items-start gap-2">
              <Icon name="volume-2" size={18} className="mt-0.5 shrink-0" />
              <span>
                Ajak siswa duduk tenang, lalu tekan <strong>Mulai Asesmen</strong>. Layar siswa
                akan menampilkan bacaan dan tombol rekam.
              </span>
            </p>
          </div>

          {startError && (
            <p className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {startError}
            </p>
          )}

          <div className="flex flex-wrap justify-between gap-2">
            <Button variant="ghost" size="md" onClick={() => setStep(1)} disabled={starting}>
              <Icon name="arrow-left" size={18} />
              Kembali
            </Button>
            <Button
              variant="primary"
              size="lg"
              loading={starting}
              disabled={!canStart || starting}
              onClick={startAssessment}
            >
              <Icon name="mic" size={20} />
              Mulai Asesmen
            </Button>
          </div>
        </section>
      )}

      {/* Ringkasan siswa terpilih (sticky di langkah 1–2) */}
      {student && step < 2 && (
        <div className="flex items-center gap-3 rounded-lg border border-paper-200 bg-white p-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-100 text-sm font-bold text-brand-700">
            {student.name.split(" ").map((w) => w[0]).slice(0, 2).join("")}
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-xs text-slate-500">Siswa terpilih</p>
            <p className="truncate text-sm font-semibold text-slate-800">
              {student.name} · {student.classLabel}
            </p>
          </div>
          <Button variant="ghost" size="sm" onClick={() => setStep(0)}>
            Ganti
          </Button>
        </div>
      )}

      <div className="flex justify-start">
        <Link href="/dashboard" className="text-sm font-medium text-slate-500 hover:text-slate-700">
          ← Batal dan kembali ke dashboard
        </Link>
      </div>
    </div>
  );
}
