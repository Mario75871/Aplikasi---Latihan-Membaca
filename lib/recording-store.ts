/**
 * recording-store — penyimpanan sementara rekaman siswa di sisi klien.
 *
 * Mengapa ada file ini?
 * Blob audio hasil MediaRecorder tidak bisa dikirim lewat query param. Agar
 * alur S-03 (Rekam) → S-04 (Review & Kirim) sesuai wireframe tetap bisa
 * memutar ulang rekaman TANPA mengubah logika MediaRecorder/upload audio dan
 * tanpa menambah state manager baru, kita simpan referensi blob di variabel
 * modul. Variabel modul hidup selama sesi tab (navigasi antar-route), dan
 * otomatis kosong saat halaman dimuat ulang — halaman S-04 menanganinya
 * dengan empty state yang ramah.
 *
 * Catatan: TIDAK ada logika penilaian di sini. Hanya meneruskan hasil rekaman.
 */

export interface PendingRecording {
  /** Object URL untuk memutar ulang (URL.createObjectURL). */
  url: string;
  /** Blob audio (WAV 16 kHz mono setelah konversi) — siap dikirim ke backend. */
  blob: Blob;
  /** Durasi audio AKTUAL (detik) → Reading Time WCPM. Tidak diubah. */
  durationSec: number;
  readingId?: string;
  studentId?: string;
  /** ID sesi asesmen (dibuat di backend sebelum merekam). */
  assessmentId?: string;
}

let pending: PendingRecording | null = null;

/** Simpan rekaman terbaru; melepas URL lama agar tidak bocor memori. */
export function setPendingRecording(rec: PendingRecording): void {
  if (pending?.url) URL.revokeObjectURL(pending.url);
  pending = rec;
}

export function getPendingRecording(): PendingRecording | null {
  return pending;
}

/** Bersihkan rekaman (mis. setelah dikirim). */
export function clearPendingRecording(): void {
  if (pending?.url) URL.revokeObjectURL(pending.url);
  pending = null;
}
