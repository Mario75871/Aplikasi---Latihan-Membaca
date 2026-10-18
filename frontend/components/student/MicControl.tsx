"use client";

import * as React from "react";
import { formatDuration, cn } from "@/lib/utils";
import { Icon } from "@/components/ui/icons";

export type MicState = "idle" | "recording" | "paused" | "processing" | "done" | "error";

/** Tinggi bar waveform mini (placeholder — mencegah rekam hening). Maks 28px. */
const BARS = [6, 12, 20, 26, 18, 10, 22, 16, 8, 14, 24, 12];

/**
 * MicControl — BAR kontrol rekam ringkas untuk Student Mode (design-system §7.2).
 *
 * Satu baris horizontal (≥640px), dua baris di layar sempit, tinggi tetap
 * ~72–88px. Bukan kartu besar: hanya garis pemisah atas tipis, tanpa bayangan.
 *
 * Non-punitif: saat merekam memakai warna hangat (amber), BUKAN merah menyala.
 * Timer = durasi audio AKTUAL → Reading Time WCPM (§14) — tidak diubah.
 * Selalu sediakan Rekam Ulang (NFR-03).
 *
 * Prop S-03:
 * - `disabled`  : tombol rekam nonaktif sampai teks bacaan berhasil dimuat.
 * - `showTimer` : Level 1 (varian Sari) menyembunyikan timer agar tanpa tekanan.
 * - `onNext`    : aksi utama setelah selesai ("Lanjut") — tampil di bar yang sama.
 */
export function MicControl({
  state,
  durationSec = 0,
  disabled = false,
  showTimer = true,
  onStart,
  onStop,
  onRetry,
  onPlay,
  onNext,
  nextDisabled = false,
}: {
  state: MicState;
  durationSec?: number;
  /** Nonaktifkan tombol utama (mis. saat bacaan belum selesai dimuat). */
  disabled?: boolean;
  /** Sembunyikan timer untuk Level 1 (tanpa tekanan waktu). */
  showTimer?: boolean;
  onStart?: () => void;
  onStop?: () => void;
  onRetry?: () => void;
  onPlay?: () => void;
  /** Aksi utama setelah selesai ("Lanjut"). Ditampilkan di bar yang sama. */
  onNext?: () => void;
  nextDisabled?: boolean;
}) {
  const isRecording = state === "recording";
  const isBusy = state === "processing";
  const isDone = state === "done";

  /** Pesan status (di-umumkan lewat aria-live). */
  const STATUS: Record<MicState, string> = {
    idle: disabled ? "Menyiapkan bacaan…" : "Tekan untuk mulai membaca",
    recording: "Sedang merekam",
    paused: "Dijeda",
    processing: "Sedang menyiapkan…",
    done: "Rekamanmu sudah siap",
    error: "Rekaman belum terbaca. Coba lagi ya.",
  };

  return (
    <div className="w-full border-t border-slate-200 bg-white">
      <div className="mx-auto flex max-w-3xl flex-col gap-3 px-4 py-3 sm:h-20 sm:flex-row sm:items-center sm:gap-5 sm:px-6 sm:py-0">
        {/* Kiri: tombol rekam/stop bulat (56–64px) + status (mobile) */}
        <div className="flex min-w-0 flex-1 items-center gap-3 sm:gap-4">
          {isDone ? (
            <span
              aria-hidden
              className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-600"
            >
              <Icon name="check-circle" size={30} strokeWidth={2.5} />
            </span>
          ) : (
            <button
              type="button"
              aria-label={isRecording ? "Berhenti merekam" : "Mulai merekam"}
              onClick={isRecording ? onStop : onStart}
              disabled={disabled || isBusy}
              className={cn(
                "relative flex h-16 w-16 shrink-0 items-center justify-center rounded-full text-white",
                "transition-transform focus-visible:outline-none active:scale-95",
                "disabled:cursor-not-allowed disabled:opacity-50 disabled:active:scale-100",
                isRecording
                  ? "bg-accent-500 hover:bg-accent-600"
                  : "bg-brand-500 hover:bg-brand-600"
              )}
            >
              {isRecording && (
                <span
                  aria-hidden
                  className="absolute inset-0 animate-ping rounded-full bg-accent-400/40"
                />
              )}
              <span className="relative">
                <Icon name={isRecording ? "square" : "mic"} size={28} strokeWidth={2.5} />
              </span>
            </button>
          )}

          {/* Status — diumumkan ke pembaca layar. */}
          <div className="min-w-0 flex-1">
            <p aria-live="polite" className="truncate text-base font-semibold text-slate-700">
              {STATUS[state]}
            </p>
            {isRecording && (
              <p className="truncate text-sm font-medium text-accent-600">
                Bagus, teruskan! 👏
              </p>
            )}
          </div>

          {/* Waveform mini (≤32px) — dekoratif, hanya di layar lebar. */}
          <div aria-hidden className="hidden h-7 shrink-0 items-end gap-0.5 sm:flex">
            {BARS.map((h, i) => (
              <span
                key={i}
                className={cn("w-1 rounded-full", isRecording ? "bg-brand-400" : "bg-slate-200")}
                style={{ height: `${isRecording ? h : 6}px` }}
              />
            ))}
          </div>
        </div>

        {/* Kanan: timer + aksi (Rekam Ulang / Lanjut). */}
        <div className="flex shrink-0 items-center justify-end gap-2">
          {showTimer && (isRecording || isDone) && (
            <p className="tabular text-xl font-semibold text-slate-600">
              {formatDuration(durationSec)}
            </p>
          )}

          {isDone && onPlay && (
            <button
              type="button"
              onClick={onPlay}
              aria-label="Putar rekaman"
              className="flex h-14 w-14 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100 focus-visible:outline-none"
            >
              <Icon name="play" size={22} />
            </button>
          )}

          {(isRecording || isDone || state === "error") && onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="flex h-14 items-center gap-2 rounded-lg border border-slate-300 px-4 text-sm font-semibold text-slate-600 hover:bg-slate-50 focus-visible:outline-none"
            >
              <Icon name="rotate-ccw" size={18} />
              Rekam Ulang
            </button>
          )}

          {isDone && onNext && (
            <button
              type="button"
              onClick={onNext}
              disabled={nextDisabled}
              className="flex h-14 items-center gap-2 rounded-lg bg-brand-500 px-5 text-sm font-semibold text-white transition-colors hover:bg-brand-600 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50"
            >
              Lanjut
              <Icon name="arrow-right" size={18} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
