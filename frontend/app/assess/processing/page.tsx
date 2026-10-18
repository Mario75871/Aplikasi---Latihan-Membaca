"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { StudentShell } from "@/components/student/StudentShell";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/icons";
import { uploadAssessmentAudio, ApiError } from "@/lib/api";
import { makeSilentWavBlob } from "@/lib/audio-wav";
import { getPendingRecording, clearPendingRecording } from "@/lib/recording-store";

const MESSAGES = [
  "Sedang mendengarkan bacaanmu…",
  "Sedang menilai bacaanmu…",
  "Sebentar lagi selesai…",
];

type Phase = "uploading" | "error";

/**
 * S-05 Memproses — meng-upload rekaman ke backend (Model #1 + Model #2),
 * lalu lanjut ke pertanyaan pemahaman. Menampilkan pesan hangat bergilir.
 *
 * NFR-03: bila proses speech gagal (HTTP 503) → tampilkan error + tombol Coba Lagi.
 * Bila backend menjalankan mode demo, tandai jelas "Mode demo".
 */
function ProcessingScreen() {
  const router = useRouter();
  const params = useSearchParams();
  const assessmentId = params.get("assessment");
  const readingId = params.get("reading");

  const [phase, setPhase] = useState<Phase>("uploading");
  const [msgIndex, setMsgIndex] = useState(0);
  const [errorMsg, setErrorMsg] = useState("");
  const [demoMode, setDemoMode] = useState(false);
  const startedRef = useRef(false);

  // Pesan bergilir selama menunggu.
  useEffect(() => {
    if (phase !== "uploading") return;
    const cycle = setInterval(
      () => setMsgIndex((i) => Math.min(i + 1, MESSAGES.length - 1)),
      2200
    );
    return () => clearInterval(cycle);
  }, [phase]);

  const upload = useCallback(async () => {
    setPhase("uploading");
    setMsgIndex(0);
    setErrorMsg("");

    if (!assessmentId) {
      setPhase("error");
      setErrorMsg(
        "Sesi asesmen tidak ditemukan. Minta Ibu/Bapak guru memulai asesmen lagi ya."
      );
      return;
    }

    const rec = getPendingRecording();
    // Bila tidak ada rekaman (mis. tombol "Pakai Audio Contoh"), kirim WAV kecil
    // yang VALID agar lolos validasi magic bytes (backend hanya menerima WAV/MP3)
    // sekaligus backend mode demo dapat memutar ulang hasil contoh.
    const blob = rec?.blob ?? makeSilentWavBlob();
    const filename = rec ? "rekaman.wav" : "audio-contoh.wav";

    try {
      const result = await uploadAssessmentAudio(assessmentId, blob, filename);
      setDemoMode(result.isDemoFallback);
      clearPendingRecording();
      const qs = new URLSearchParams();
      qs.set("assessment", assessmentId);
      if (readingId) qs.set("reading", readingId);
      router.replace(`/assess/answer?${qs.toString()}`);
    } catch (e) {
      setPhase("error");
      if (e instanceof ApiError && e.status === 503) {
        setErrorMsg(
          "Suara belum bisa diproses. Coba tekan Coba Lagi, atau minta bantuan Ibu/Bapak guru ya."
        );
      } else if (e instanceof ApiError && e.status === 422) {
        // Audio terlalu panjang (> MAX_AUDIO_DURATION_SEC).
        setErrorMsg(
          "Rekaman terlalu panjang untuk diproses. Coba rekam ulang dengan durasi lebih singkat ya."
        );
      } else if (e instanceof ApiError && (e.status === 413 || e.status === 415)) {
        setErrorMsg(
          "Rekaman tidak didukung (harus WAV/MP3 dan maks 10 MB). Coba rekam ulang ya."
        );
      } else if (e instanceof ApiError) {
        setErrorMsg(e.detail);
      } else {
        setErrorMsg("Terjadi masalah saat memproses. Coba lagi ya.");
      }
    }
  }, [assessmentId, readingId, router]);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    void upload();
  }, [upload]);

  return (
    <StudentShell step={2}>
      <div className="flex flex-1 flex-col items-center justify-center gap-8 px-6 pb-16 text-center">
        {phase === "uploading" && (
          <>
            <span className="relative flex h-24 w-24 items-center justify-center rounded-full bg-brand-100 text-brand-600">
              <Icon name="mic" size={48} strokeWidth={2.5} />
              <span className="absolute inset-0 animate-ping rounded-full bg-brand-200/60" />
            </span>

            <p className="font-serif text-2xl font-semibold text-slate-700 sm:text-3xl">
              {MESSAGES[msgIndex]}
            </p>
            <p className="text-base text-slate-500">
              Tunggu sebentar ya, tidak perlu menekan apa pun.
            </p>
            {demoMode && (
              <p className="rounded-full bg-amber-100 px-3 py-1 text-sm font-semibold text-amber-700">
                Mode demo
              </p>
            )}
          </>
        )}

        {phase === "error" && (
          <>
            <span className="flex h-24 w-24 items-center justify-center rounded-full bg-amber-100 text-amber-600">
              <Icon name="alert-triangle" size={48} strokeWidth={2.5} />
            </span>
            <div className="space-y-2">
              <h1 className="font-serif text-2xl font-semibold text-slate-800 sm:text-3xl">
                Belum berhasil, ayo coba lagi
              </h1>
              <p className="mx-auto max-w-md text-base text-slate-600">{errorMsg}</p>
            </div>
            <div className="flex w-full max-w-sm flex-col gap-3">
              <Button variant="primary" size="xl" onClick={() => void upload()}>
                <Icon name="rotate-ccw" size={22} />
                Coba Lagi
              </Button>
              <Button
                variant="secondary"
                size="lg"
                onClick={() => router.push(`/assess/record?${params.toString()}`)}
              >
                <Icon name="mic" size={20} />
                Rekam Ulang
              </Button>
            </div>
          </>
        )}
      </div>
    </StudentShell>
  );
}

export default function StudentProcessingPage() {
  return (
    <Suspense
      fallback={
        <StudentShell step={2}>
          <div className="flex flex-1 items-center justify-center px-6 pb-16">
            <p className="text-lg text-slate-500">Menyiapkan…</p>
          </div>
        </StudentShell>
      }
    >
      <ProcessingScreen />
    </Suspense>
  );
}
