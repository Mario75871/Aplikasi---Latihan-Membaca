import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Gabungkan class Tailwind dengan aman. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Format angka dengan pemisah ribuan (locale id-ID). */
export function formatNumber(n: number): string {
  return new Intl.NumberFormat("id-ID").format(n);
}

/** Format durasi detik → mm:ss */
export function formatDuration(totalSeconds: number): string {
  const m = Math.floor(totalSeconds / 60);
  const s = Math.floor(totalSeconds % 60);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

/** Estimasi durasi baca (detik) → "≈ 1 menit" / "≈ 40 detik". */
export function formatEstimate(seconds: number): string {
  if (seconds < 60) return `≈ ${seconds} detik`;
  const minutes = Math.round(seconds / 60);
  return `≈ ${minutes} menit`;
}

/** Hitung jumlah kata (dipakai untuk metadata bacaan bila backend tidak menyediakannya). */
export function countWords(text: string): number {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

/**
 * Format tanggal/tanggal-waktu ISO → "12 Mei 2026" (locale id-ID).
 * Menerima "2026-05-12" maupun "2026-05-12T08:30:00+00:00".
 */
export function formatDateID(iso: string): string {
  const d = new Date(iso.length <= 10 ? `${iso}T00:00:00` : iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("id-ID", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}
