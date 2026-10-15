"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { StudentShell } from "@/components/student/StudentShell";
import { EmptyState } from "@/components/ui/States";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/icons";
import { formatDuration } from "@/lib/utils";
import { getPendingRecording } from "@/lib/recording-store";

const BARS = [6, 14, 22, 30, 20, 12, 26, 18, 10, 24, 16, 28, 12, 20, 8];

/** S-04 Review & Kirim — dengar ulang sebelum mengirim. Non-punitif, tanpa nilai. */
function ReviewScreen() {
  const router = useRouter();
  const params = useSearchParams();
  const [rec, setRec] = useState<ReturnType<typeof getPendingRecording>>(null);
  const [playing, setPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    setRec(getPendingRecording());
  }, []);

  // Rekaman hilang saat halaman di-refresh / diakses langsung.
  if (!rec) {
    return (
      <StudentShell step={2}>
        <div className="flex flex-1 items-center justify-center px-6 pb-16">
          <div className="w-full max-w-md">
            <EmptyState
              icon="mic"
              title="Rekaman belum ada"
              description="Ayo rekam bacaanmu dulu ya. Tekan tombol di bawah untuk mulai merekam."
              action={
                <Button
                  variant="primary"
                  size="lg"
                  onClick={() => router.push(`/assess/record?${params.toString()}`)}
                >
                  <Icon name="mic" size={20} />
                  Mulai Rekam
                </Button>
              }
            />
          </div>
        </div>
      </StudentShell>
    );
  }

  function play() {
    const el = audioRef.current;
    if (!el) return;
    setPlaying(true);
    el.currentTime = 0;
    void el.play();
  }

  function send() {
    // JANGAN bersihkan rekaman di sini: halaman processing yang akan
    // meng-upload blob ke backend, lalu membersihkannya setelah sukses.
    const qs = new URLSearchParams();
    if (rec?.readingId) qs.set("reading", rec.readingId);
    if (rec?.studentId) qs.set("student", rec.studentId);
    if (rec?.assessmentId) qs.set("assessment", rec.assessmentId);
    router.push(`/assess/processing?${qs.toString()}`);
  }

  return (
    <StudentShell step={2}>
      <div className="flex flex-1 flex-col items-center justify-center gap-8 px-6 pb-16 text-center">
        <h1 className="font-serif text-2xl font-semibold text-slate-800 sm:text-3xl">
          Rekamanmu sudah siap! 🎉
        </h1>

        {/* Kartu pemutar rekaman */}
        <div className="w-full max-w-md rounded-2xl border border-paper-200 bg-white p-6">
          <p className="mb-4 text-sm font-semibold text-slate-500">Dengarkan lagi ya</p>

          <div className="flex items-center justify-center gap-4">
            <button
              type="button"
              onClick={play}
              aria-label="Putar rekaman"
              className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-brand-500 text-white shadow-md transition-colors hover:bg-brand-600 focus-visible:outline-none"
            >
              <Icon name="play" size={26} strokeWidth={2.5} />
            </button>

            <div aria-hidden className="flex h-12 flex-1 items-end justify-center gap-1">
              {BARS.map((h, i) => (
                <span
                  key={i}
                  className={playing ? "w-1.5 rounded-full bg-brand-400" : "w-1.5 rounded-full bg-slate-200"}
                  style={{ height: `${h}px` }}
                />
              ))}
            </div>

            <span className="tabular shrink-0 text-lg font-semibold text-slate-600">
              {formatDuration(rec.durationSec)}
            </span>
          </div>

          <audio
            ref={audioRef}
            src={rec.url}
            onEnded={() => setPlaying(false)}
            className="sr-only"
          />
        </div>

        <p className="text-lg text-slate-600">Sudah terdengar jelas?</p>

        <div className="flex w-full max-w-sm flex-col gap-3">
          <button
            type="button"
            onClick={send}
            className="flex h-16 w-full items-center justify-center gap-2 rounded-2xl bg-brand-500 text-xl font-bold text-white transition-colors hover:bg-brand-600 focus-visible:outline-none"
          >
            Kirim
            <Icon name="arrow-right" size={24} />
          </button>
          <button
            type="button"
            onClick={() => router.push(`/assess/record?${params.toString()}`)}
            className="flex h-14 w-full items-center justify-center gap-2 rounded-2xl bg-white text-lg font-semibold text-slate-600 shadow-sm ring-1 ring-slate-200 transition-colors hover:bg-slate-50 focus-visible:outline-none"
          >
            <Icon name="rotate-ccw" size={20} />
            Rekam Ulang
          </button>
        </div>
      </div>
    </StudentShell>
  );
}

export default function StudentReviewPage() {
  return (
    <Suspense
      fallback={
        <StudentShell step={2}>
          <div className="flex flex-1 items-center justify-center px-6 pb-16">
            <p className="text-lg text-slate-500">Menyiapkan rekamanmu…</p>
          </div>
        </StudentShell>
      }
    >
      <ReviewScreen />
    </Suspense>
  );
}
