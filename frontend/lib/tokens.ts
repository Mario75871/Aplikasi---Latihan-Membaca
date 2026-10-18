/**
 * BacaLaras — Token & Konstanta domain (presentasi).
 *
 * PENTING: file ini hanya berisi presentasi (label, warna, ikon, tooltip).
 * Tidak ada logika Adaptive Engine di sini — engine tetap di backend.
 *
 * Bahasa: label status & tooltip memakai **bahasa pengguna** (tanpa kode PRD
 * seperti BR-xx / §nn / nama engine). Jejak aturan cukup di kode/backend.
 */

export type AdaptiveStatus =
  | "INTERVENE"
  | "STAY"
  | "PROMOTION_CANDIDATE"
  | "PROMOTE";

/** Status tampilan: 4 status engine + 1 state netral "belum pernah diases". */
export type DisplayStatus = AdaptiveStatus | "UNASSESSED";

export type Competency = "retrieve" | "interpret" | "reflect";

/** Nama ikon status — dipetakan ke komponen <Icon/> di components/ui/icons.tsx. */
export type StatusIconName =
  | "lifebuoy"
  | "pause"
  | "arrow-up-circle"
  | "check-circle"
  | "circle-dashed";

export interface StatusMeta {
  /** Label Bahasa Indonesia untuk guru (satu kosakata di seluruh UI). */
  label: string;
  /** Istilah teknis engine — disimpan untuk jejak, TIDAK ditampilkan ke pengguna. */
  engine: string;
  icon: StatusIconName;
  /** Penjelasan singkat dalam bahasa pengguna (tanpa kode PRD). */
  tooltip: string;
  bg: string;
  text: string;
  border: string;
  dot: string;
}

/**
 * Satu mapping status → label Indonesia, warna, ikon, tooltip.
 * Dipakai oleh StatusBadge, ClassKpiRow, dan filter dashboard.
 */
export const STATUS_META: Record<AdaptiveStatus, StatusMeta> = {
  INTERVENE: {
    label: "Perlu Intervensi",
    engine: "INTERVENE",
    icon: "lifebuoy",
    tooltip:
      "Akurasi di bawah 90%, atau salah satu aspek pemahaman di bawah 80%. Siswa ini perlu latihan tambahan dengan pendampingan.",
    bg: "bg-rose-50",
    text: "text-rose-700",
    border: "border-rose-200",
    dot: "bg-rose-600",
  },
  STAY: {
    label: "Pertahankan",
    engine: "STAY",
    icon: "pause",
    tooltip:
      "Siswa melanjutkan di level bacaan yang sama, dengan latihan sesuai rekomendasi.",
    bg: "bg-amber-50",
    text: "text-amber-700",
    border: "border-amber-200",
    dot: "bg-amber-500",
  },
  PROMOTION_CANDIDATE: {
    label: "Kandidat Naik",
    engine: "PROMOTION CANDIDATE",
    icon: "arrow-up-circle",
    tooltip:
      "Semua kriteria naik level sudah terpenuhi. Perlu satu asesmen lagi untuk memastikan sebelum naik.",
    bg: "bg-violet-50",
    text: "text-violet-700",
    border: "border-violet-200",
    dot: "bg-violet-600",
  },
  PROMOTE: {
    label: "Naik Level",
    engine: "PROMOTE",
    icon: "check-circle",
    tooltip:
      "Kriteria terpenuhi pada dua asesmen berturut-turut. Siswa siap naik ke bacaan level berikutnya.",
    bg: "bg-emerald-50",
    text: "text-emerald-700",
    border: "border-emerald-200",
    dot: "bg-emerald-600",
  },
};

/** State netral untuk siswa yang belum pernah diases — tanpa warna merah, tanpa angka 0. */
export const UNASSESSED_META: StatusMeta = {
  label: "Belum Diases",
  engine: "NO ASSESSMENT",
  icon: "circle-dashed",
  tooltip:
    "Siswa ini belum pernah menjalani asesmen membaca. Mulai asesmen untuk mendapatkan hasil.",
  bg: "bg-slate-100",
  text: "text-slate-600",
  border: "border-slate-200",
  dot: "bg-slate-400",
};

/** Ambil meta status dengan aman; null/undefined → state "Belum Diases". */
export function statusMeta(status: AdaptiveStatus | null | undefined): StatusMeta {
  if (!status) return UNASSESSED_META;
  return STATUS_META[status];
}

/** Urutan prioritas aksi untuk guru: yang butuh tindakan lebih dulu. */
export const STATUS_PRIORITY: Record<DisplayStatus, number> = {
  INTERVENE: 0,
  UNASSESSED: 1,
  STAY: 2,
  PROMOTION_CANDIDATE: 3,
  PROMOTE: 4,
};

/** Warna per kompetensi literasi. Label = bahasa pengguna (Indonesia). */
export const COMPETENCY_META: Record<
  Competency,
  { label: string; short: string; description: string; color: string; bar: string }
> = {
  retrieve: {
    label: "Menemukan informasi",
    short: "Menemukan info",
    description: "Menemukan informasi yang tertulis langsung di bacaan.",
    color: "text-sky-600",
    bar: "bg-sky-500",
  },
  interpret: {
    label: "Memahami isi",
    short: "Memahami isi",
    description: "Menghubungkan dan memahami maksud isi bacaan.",
    color: "text-violet-600",
    bar: "bg-violet-500",
  },
  reflect: {
    label: "Menilai isi",
    short: "Menilai isi",
    description: "Menilai dan merenungkan isi bacaan.",
    color: "text-teal-600",
    bar: "bg-teal-500",
  },
};

/** Ambang batas MVP. BUKAN standar nasional.
 *
 * CATATAN (integrasi): nilai ini HANYA untuk tampilan (warna/label presentasi).
 * Perhitungan keputusan (WCPM, Accuracy, status) sepenuhnya dilakukan di backend
 * (`services/assessment.py`, `rules/adaptive_rules.py`) — frontend TIDAK
 * menghitung ulang. Ini menjaga "satu sumber kebenaran per konsep".
 *
 * SUMBER KEBENARAN (integrasi #3, aturan #9): nilai di bawah HARUS mencerminkan
 * konstanta backend. Tersedia endpoint `GET /config/thresholds` (auth) yang
 * mengembalikan nilai resmi ini; frontend boleh memakainya untuk presentasi.
 * Bila salah satu berubah, ubah keduanya bersamaan:
 *   - accuracy.low  ←→ backend/rules/adaptive_rules.py  ACCURACY_LOW   (90.0)
 *   - accuracy.high ←→ backend/rules/adaptive_rules.py  ACCURACY_HIGH  (95.0)
 *   - comprehension ←→ backend/rules/adaptive_rules.py  COMPREHENSION_MIN (80.0)
 * Ada test backend yang memverifikasi nilai ini tetap sinkron (anti-drift).
 * Frontend hanya menyajikan; backend tetap pemutus keputusan.
 *
 * STATUS RUNTIME (integrasi #6, D2a): konstanta ini adalah **FALLBACK** untuk
 * render server / saat permintaan gagal. **Sumber runtime = `GET /config/thresholds`**
 * (dikonsumsi via `getThresholds()` di `lib/api.ts`). Jangan menambah logika
 * keputusan di sini — hanya presentasi & nilai cadangan.
 */
export const THRESHOLDS = {
  accuracy: { low: 90, high: 95 }, // <90 perlu intervensi; >=95 baik
  comprehension: 80, // <80 → intervensi kompetensi
} as const;

/** Klasifikasi akurasi untuk pewarnaan. Presentasi saja. */
export function accuracyLevel(accuracy: number): "low" | "mid" | "high" {
  if (accuracy < THRESHOLDS.accuracy.low) return "low";
  if (accuracy < THRESHOLDS.accuracy.high) return "mid";
  return "high";
}

/**
 * Level bacaan yang disarankan bila siswa belum punya riwayat asesmen.
 * Default: tingkat kelas 1–3 dipetakan langsung ke Level 1–3.
 */
export function suggestedLevelForGrade(grade: 1 | 2 | 3): 1 | 2 | 3 {
  return grade;
}

/** Rata-rata tiga kompetensi pemahaman (Retrieve/Interpret/Reflect). */
export function averageComprehension(c: {
  retrieve: number;
  interpret: number;
  reflect: number;
}): number {
  return Math.round((c.retrieve + c.interpret + c.reflect) / 3);
}

/** Disclaimer wajib untuk klaim eksternal. */
export const DISCLAIMERS = {
  hasbrouck:
    "Reference based on Hasbrouck & Tindal ORF norms. This is not an Indonesian national normative benchmark.",
  threshold:
    "Ambang batas ini adalah aturan MVP, bukan standar nasional Indonesia.",
  medical: "BacaLaras membantu asesmen, bukan alat diagnosis medis.",
} as const;
