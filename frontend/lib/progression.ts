/**
 * Progresi bacaan per siswa — **cermin tampilan** dari gerbang naik level.
 *
 * ⚠️ SUMBER KEBENARAN ada di backend: `backend/services/progression.py`.
 * Berkas ini hanya mengulang aturan yang sama supaya kartu bacaan bisa dikunci
 * sebelum guru menekan "Mulai Asesmen". Backend tetap menegakkannya
 * (`POST /assessments` → 409) karena `/assess/read?reading=<id>` menerima id
 * bacaan apa pun, jadi UI saja bisa ditembus. Bila aturan di backend berubah,
 * ubah juga di sini — kalau tidak, guru akan melihat kartu yang tampak bisa
 * diklik lalu gagal saat memulai.
 *
 * Aturannya: tangga mulai Level 1 untuk SEMUA siswa (tidak melihat tingkat
 * kelas); level berikutnya terbuka setelah **seluruh** bacaan pada level
 * berjalan tuntas. Tuntas = asesmen dengan `sessionState === "COMPLETED"`.
 */
import type { AssessmentResult, ReadingText } from "./types";

/** Level yang dikenal — selaras dengan backend `progression.LEVELS`. */
export const LEVELS = [1, 2, 3] as const;

export type Level = (typeof LEVELS)[number];

/** Ringkasan progresi satu siswa, siap dipakai UI. */
export interface StudentProgression {
  /** Level tertinggi yang boleh diases siswa ini. */
  unlockedLevel: Level;
  /** Judul bacaan pada level berjalan yang belum tuntas (urut katalog). */
  pendingTitles: string[];
}

/** Bacaan yang sudah tuntas untuk satu siswa. */
export function completedReadingIds(
  assessments: AssessmentResult[],
  studentId: string
): Set<string> {
  const ids = new Set<string>();
  for (const a of assessments) {
    if (a.studentId === studentId && a.sessionState === "COMPLETED" && a.readingId) {
      ids.add(a.readingId);
    }
  }
  return ids;
}

function readingsAtLevel(readings: ReadingText[], level: Level): ReadingText[] {
  return readings.filter((r) => r.level === level);
}

/**
 * Level tertinggi yang boleh diakses siswa ini.
 *
 * Naik satu tingkat selama seluruh bacaan pada level berjalan sudah tuntas.
 * Level tanpa bacaan dianggap tuntas (tidak ada yang perlu diselesaikan),
 * sehingga katalog yang tidak lengkap tidak mengunci tangga selamanya.
 */
export function unlockedLevel(
  readings: ReadingText[],
  completedIds: Set<string>
): Level {
  let level: Level = LEVELS[0];
  for (const lvl of LEVELS.slice(0, -1)) {
    const atLevel = readingsAtLevel(readings, lvl);
    if (atLevel.length > 0 && !atLevel.every((r) => completedIds.has(r.id))) break;
    level = (lvl + 1) as Level;
  }
  return level;
}

/** Hitung ringkasan progresi satu siswa dari riwayat asesmennya. */
export function studentProgression(
  readings: ReadingText[],
  assessments: AssessmentResult[],
  studentId: string
): StudentProgression {
  const done = completedReadingIds(assessments, studentId);
  const unlocked = unlockedLevel(readings, done);
  return {
    unlockedLevel: unlocked,
    pendingTitles: readingsAtLevel(readings, unlocked)
      .filter((r) => !done.has(r.id))
      .map((r) => r.title),
  };
}

/** Apakah bacaan ini boleh diases oleh siswa dengan progresi tersebut. */
export function isLocked(progression: StudentProgression, reading: ReadingText): boolean {
  return reading.level > progression.unlockedLevel;
}

/**
 * Alasan bacaan ini terkunci, atau `null` bila boleh diases.
 *
 * Kalimatnya sengaja dibuat sama dengan pesan `409` backend supaya guru melihat
 * penjelasan yang sama, baik dari UI maupun saat backend menolak.
 */
export function lockedReason(
  progression: StudentProgression,
  reading: ReadingText,
  studentName?: string
): string | null {
  if (!isLocked(progression, reading)) return null;

  const { unlockedLevel: unlocked, pendingTitles } = progression;
  const who = studentName ? `${studentName} ` : "";
  if (pendingTitles.length > 0) {
    const judul = pendingTitles.map((t) => `«${t}»`).join(", ");
    return (
      `${who}masih di Level ${unlocked}. Selesaikan dulu ${pendingTitles.length} bacaan ` +
      `Level ${unlocked} yang belum tuntas: ${judul}. ` +
      `Level ${reading.level} terbuka setelah semuanya tuntas.`
    );
  }
  return (
    `${who}masih di Level ${unlocked}. Level ${reading.level} terbuka setelah seluruh ` +
    `bacaan Level ${unlocked} tuntas.`
  );
}
