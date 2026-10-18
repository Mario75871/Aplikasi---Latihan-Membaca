"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { StudentShell } from "@/components/student/StudentShell";
import { ReadingPassage } from "@/components/student/ReadingPassage";
import { MicControl, type MicState } from "@/components/student/MicControl";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/States";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/icons";
import { getReading } from "@/lib/api";
import {
  blobToWav,
  MAX_AUDIO_BYTES,
  MAX_AUDIO_DURATION_SEC,
} from "@/lib/audio-wav";
import type { ReadingText } from "@/lib/types";
import { setPendingRecording } from "@/lib/recording-store";

type LoadState = "loading" | "ready" | "empty" | "error";

/** Skeleton kartu bacaan saat teks sedang diambil. */
function ReadingSkeleton() {
  return (
    <div
      className="rounded-xl border border-paper-200 bg-white p-5 sm:p-6"
      role="status"
      aria-label="Memuat bacaan"
    >
      <Skeleton className="mx-auto h-5 w-40" />
      <div className="mt-5 space-y-3">
        <Skeleton className="h-6 w-full" />
        <Skeleton className="h-6 w-11/12" />
        <Skeleton className="h-6 w-full" />
        <Skeleton className="h-6 w-4/5" />
      </div>
    </div>
  );
}

/**
 * S-03 Rekam Suara — merekam audio nyata via MediaRecorder.
 *
 * Tata letak: tinggi penuh layar (h-dvh), kolom flex vertikal.
 * Header tetap, KARTU BACAAN mengisi ruang sisa (scroll di dalam), dan
 * BAR KONTROL RINGKAS menempel di bawah (tinggi tetap, bukan kartu besar).
 * Halaman tidak menggulir sendiri — hanya teks bacaan yang menggulir.
 *
 * Teks bacaan dari sumber data yang sama dengan S-02 lewat query `?reading=`.
 * Non-punitif: tanpa merah, tanpa nilai, tanpa status INTERVENE.
 * Timer = durasi audio AKTUAL → Reading Time WCPM. Tidak diubah.
 *
 * Batas durasi diterima dari server (`maxDurationSec`, dari `GET /config/audio`);
 * fallback konstanta cermin backend bila tak tersedia.
 */
function RecordScreen({ maxDurationSec }: { maxDurationSec: number }) {
  const router = useRouter();
  const params = useSearchParams();
  const readingId = params.get("reading");
  const studentId = params.get("student") ?? undefined;
  const assessmentId = params.get("assessment") ?? undefined;

  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [reading, setReading] = useState<ReadingText | null>(null);

  const [state, setState] = useState<MicState>("idle");
  const [duration, setDuration] = useState(0);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [blob, setBlob] = useState<Blob | null>(null);
  const [micError, setMicError] = useState(false);
  const [sizeError, setSizeError] = useState(false);
  const [durationError, setDurationError] = useState(false);

  // Batas durasi efektif: prop server (sumber runtime) atau fallback konstanta.
  // null-safe: nilai non-positif/NaN → fallback (konsisten keputusan di backend).
  const effectiveMaxDurationSec =
    Number.isFinite(maxDurationSec) && maxDurationSec > 0
      ? maxDurationSec
      : MAX_AUDIO_DURATION_SEC;

  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Ambil bacaan terpilih dari backend (query param, bukan hardcode) ──
  useEffect(() => {
    let active = true;
    setLoadState("loading");
    getReading(readingId)
      .then((r) => {
        if (!active) return;
        if (!r) {
          setReading(null);
          // Tanpa parameter → "belum dipilih"; ada parameter tapi tidak ketemu → error.
          setLoadState(readingId ? "error" : "empty");
          return;
        }
        setReading(r);
        setLoadState("ready");
      })
      .catch(() => {
        if (active) setLoadState("error");
      });
    return () => {
      active = false;
    };
  }, [readingId]);

  // Bersihkan resource saat keluar halaman.
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      recorderRef.current?.stream.getTracks().forEach((t) => t.stop());
    };
  }, []);

  // ── MediaRecorder (logika inti TIDAK diubah) ──
  async function start() {
    setMicError(false);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      chunksRef.current = [];
      rec.ondataavailable = (e) => e.data.size > 0 && chunksRef.current.push(e.data);
      rec.onstop = () => {
        const raw = new Blob(chunksRef.current, { type: "audio/webm" });
        // Backend hanya menerima WAV/MP3 → konversi ke WAV.
        // Bila konversi gagal (mis. browser tak mendukung decode), fallback ke raw
        // agar pengguna tetap dapat melihat pratinjau; backend akan menolak dgn 415
        // dan UI menampilkan pesan yang jelas.
        const finish = (b: Blob) => {
          setBlob(b);
          setAudioUrl(URL.createObjectURL(b));
          stream.getTracks().forEach((t) => t.stop());
          setState("done");
        };
        blobToWav(raw)
          .then(finish)
          .catch(() => finish(raw));
      };
      rec.start();
      recorderRef.current = rec;
      setState("recording");
      setDuration(0);
      timerRef.current = setInterval(() => setDuration((d) => d + 1), 1000);
    } catch {
      setMicError(true);
      setState("error");
    }
  }

  function stop() {
    if (timerRef.current) clearInterval(timerRef.current);
    recorderRef.current?.stop();
  }

  function retry() {
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    setAudioUrl(null);
    setBlob(null);
    setDuration(0);
    setMicError(false);
    setSizeError(false);
    setDurationError(false);
    setState("idle");
  }

  /** Teruskan rekaman ke S-04 (Review & Kirim) — TIDAK langsung mengirim. */
  function goReview() {
    if (!blob || !audioUrl) return;
    // Cegah 413 di UI — validasi ukuran sebelum lanjut.
    if (blob.size > MAX_AUDIO_BYTES) {
      setSizeError(true);
      return;
    }
    // Cegah 422 di UI — validasi durasi, bukan hanya ukuran.
    if (duration > effectiveMaxDurationSec) {
      setSizeError(false);
      setDurationError(true);
      return;
    }
    setSizeError(false);
    setDurationError(false);
    setPendingRecording({
      url: audioUrl,
      blob,
      durationSec: duration,
      readingId: reading?.id,
      studentId,
      assessmentId,
    });
    const qs = new URLSearchParams();
    if (reading?.id) qs.set("reading", reading.id);
    if (studentId) qs.set("student", studentId);
    if (assessmentId) qs.set("assessment", assessmentId);
    router.push(`/assess/review?${qs.toString()}`);
  }

  const isReady = loadState === "ready" && reading !== null;
  // Level 1 (varian Sari): tanpa tekanan waktu → timer kecil/tidak menonjol.
  const showTimer = reading ? reading.level > 1 : true;
  // Peringatan (bukan auto-stop) mendekati batas durasi.
  const nearLimit =
    state === "recording" && duration >= effectiveMaxDurationSec - 30;
  const remainingSec = Math.max(effectiveMaxDurationSec - duration, 0);

  return (
    <StudentShell step={1} fullHeight>
      <div className="flex min-h-0 flex-1 flex-col">
        {/* ── Kartu bacaan — mengisi ruang sisa, menggulir di dalam ── */}
        <div className="min-h-0 flex-1 overflow-y-auto px-4 pt-2 sm:px-6">
          <div className="mx-auto max-w-3xl pb-4">
            {loadState === "loading" && <ReadingSkeleton />}

            {loadState === "empty" && (
              <EmptyState
                icon="book-x"
                title="Bacaan belum dipilih"
                description="Minta Ibu/Bapak guru memilih bacaan dulu ya, lalu kembali ke sini."
                action={
                  <Button
                    variant="primary"
                    size="lg"
                    onClick={() => router.push("/assess")}
                  >
                    <Icon name="arrow-left" size={20} />
                    Pilih Bacaan
                  </Button>
                }
              />
            )}

            {loadState === "error" && (
              <ErrorState
                title="Bacaan belum bisa dibuka"
                description="Jaringan mungkin sedang sibuk. Coba muat ulang bacaan ya."
                onRetry={() => {
                  setLoadState("loading");
                  getReading(readingId)
                    .then((r) => {
                      if (r) {
                        setReading(r);
                        setLoadState("ready");
                      } else {
                        setLoadState("error");
                      }
                    })
                    .catch(() => setLoadState("error"));
                }}
                fallbackAction={
                  <Button
                    variant="secondary"
                    size="lg"
                    onClick={() => router.push("/assess")}
                  >
                    <Icon name="arrow-left" size={20} />
                    Pilih Bacaan
                  </Button>
                }
              />
            )}

            {isReady && (
              <div className="rounded-xl border border-paper-200 bg-white p-5 sm:p-6">
                <ReadingPassage
                  title={reading!.title}
                  content={reading!.content}
                  level={reading!.level}
                  size="record"
                  titleVariant="small"
                />
              </div>
            )}
          </div>
        </div>

        {/* ── Bar kontrol rekam — tinggi tetap, menempel di bawah ── */}
        <div className="shrink-0">
          {loadState === "loading" && <MicControl state="idle" disabled showTimer={showTimer} />}

          {isReady && !micError && !durationError && !sizeError && (
            <>
              {nearLimit && (
                <p className="bg-amber-50 py-1.5 text-center text-xs font-medium text-amber-700">
                  Sisa {remainingSec} detik lagi ya, segera selesaikan bacaanmu.
                </p>
              )}
              <MicControl
                state={state}
                durationSec={duration}
                showTimer={showTimer}
                onStart={start}
                onStop={stop}
                onRetry={retry}
                onPlay={() => audioUrl && new Audio(audioUrl).play()}
                onNext={goReview}
                nextDisabled={!blob}
              />
            </>
          )}

          {isReady && micError && (
            <div className="border-t border-slate-200 bg-white">
              <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6">
                <ErrorState
                  className="p-6"
                  title="Mikrofon belum menyala"
                  description="Minta bantuan Ibu/Bapak guru untuk mengizinkan mikrofon, lalu coba lagi ya."
                  onRetry={retry}
                  fallbackAction={
                    <Button
                      variant="secondary"
                      size="lg"
                      onClick={() => {
                        const qs = new URLSearchParams();
                        if (readingId) qs.set("reading", readingId);
                        if (studentId) qs.set("student", studentId);
                        if (assessmentId) qs.set("assessment", assessmentId);
                        router.push(`/assess/processing?${qs.toString()}`);
                      }}
                    >
                      Pakai Audio Contoh
                    </Button>
                  }
                />
              </div>
            </div>
          )}

          {/* Rekaman terlalu besar → jangan kirim (cegah 413). */}
          {isReady && !micError && sizeError && (
            <div className="border-t border-slate-200 bg-white">
              <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6">
                <ErrorState
                  className="p-6"
                  title="Rekaman terlalu besar"
                  description="Rekaman melebihi batas 10 MB. Coba rekam ulang dengan durasi lebih singkat ya."
                  onRetry={retry}
                />
              </div>
            </div>
          )}

          {/* Melebihi batas durasi → cegah 422 di klien. */}
          {isReady && !micError && durationError && (
            <div className="border-t border-slate-200 bg-white">
              <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6">
                <ErrorState
                  className="p-6"
                  title="Rekaman terlalu panjang"
                  description={`Rekaman melebihi batas ${Math.round(
                    effectiveMaxDurationSec / 60
                  )} menit. Coba rekam ulang dengan durasi lebih singkat ya.`}
                  onRetry={retry}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </StudentShell>
  );
}

/** Fallback saat useSearchParams menangguhkan render (Next.js). */
function RecordFallback() {
  return (
    <StudentShell step={1} fullHeight>
      <div className="flex min-h-0 flex-1 flex-col">
        <div className="min-h-0 flex-1 overflow-y-auto px-4 pt-2 sm:px-6">
          <div className="mx-auto max-w-3xl pb-4">
            <ReadingSkeleton />
          </div>
        </div>
        <div className="shrink-0">
          <MicControl state="idle" disabled />
        </div>
      </div>
    </StudentShell>
  );
}

/**
 * Client wrapper: menerima `maxDurationSec` dari server component (page.tsx) dan
 * membungkus `RecordScreen` dalam Suspense (dibutuhkan `useSearchParams`).
 */
export default function RecordScreenLoader({
  maxDurationSec,
}: {
  maxDurationSec: number;
}) {
  return (
    <Suspense fallback={<RecordFallback />}>
      <RecordScreen maxDurationSec={maxDurationSec} />
    </Suspense>
  );
}
