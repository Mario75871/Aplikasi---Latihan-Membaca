/**
 * BacaLaras — Token & Konstanta domain
 * Sumber: design-system.md, PRD v2.2 (§13.2, §15, §19, §20–§26)
 *
 * PENTING: file ini hanya berisi presentasi (label, warna, ikon, tooltip).
 * Tidak ada logika Adaptive Engine di sini — engine tetap di backend (§38.2).
 */

export type AdaptiveStatus =
  | "INTERVENE"
  | "STAY"
  | "PROMOTION_CANDIDATE"
  | "PROMOTE";

/** Status tampilan: 4 status engine + 1 state netral "belum pernah diases". */
export type DisplayStatus = AdaptiveStatus | "UNASSESSED";

export type Competency = "retrieve" | "interpret" | "reflect";

export type WordDecision = "correct" | "incorrect" | "neutral";

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
  /** Istilah teknis engine — hanya muncul di tooltip. */
  engine: string;
  icon: StatusIconName;
  /** Penjelasan singkat + rujukan aturan (BR-xx). */
  tooltip: string;
  bg: string;
  text: string;
  border: string;
  dot: string;
  /** Warna aksen batang atas kartu KPI. */
  accent: string;
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
      "Akurasi < 90% atau salah satu pemahaman (Retrieve/Interpret/Reflect) < 80%. Siswa perlu latihan tambahan. Aturan BR-01/BR-02.",
    bg: "bg-rose-50",
    text: "text-rose-700",
    border: "border-rose-200",
    dot: "bg-rose-600",
    accent: "bg-rose-500",
  },
  STAY: {
    label: "Pertahankan",
    engine: "STAY",
    icon: "pause",
    tooltip:
      "Lanjut di level bacaan yang sama, fokus latihan sesuai rekomendasi. Aturan BR-05/BR-07.",
    bg: "bg-amber-50",
    text: "text-amber-700",
    border: "border-amber-200",
    dot: "bg-amber-500",
    accent: "bg-amber-500",
  },
  PROMOTION_CANDIDATE: {
    label: "Kandidat Naik",
    engine: "PROMOTION CANDIDATE",
    icon: "arrow-up-circle",
    tooltip:
      "Semua kriteria terpenuhi. Perlu asesmen sekali lagi untuk memastikan sebelum naik level. Aturan BR-03/BR-04.",
    bg: "bg-violet-50",
    text: "text-violet-700",
    border: "border-violet-200",
    dot: "bg-violet-600",
    accent: "bg-violet-500",
  },
  PROMOTE: {
    label: "Naik Level",
    engine: "PROMOTE",
    icon: "check-circle",
    tooltip:
      "Kriteria terpenuhi pada dua asesmen berturut-turut. Siswa siap naik ke bacaan level berikutnya. Aturan BR-04.",
    bg: "bg-emerald-50",
    text: "text-emerald-700",
    border: "border-emerald-200",
    dot: "bg-emerald-600",
    accent: "bg-emerald-500",
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
  accent: "bg-slate-300",
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

/** Warna per kompetensi literasi (§17). Label = istilah baku + penjelasan Indonesia. */
export const COMPETENCY_META: Record<
  Competency,
  { label: string; short: string; description: string; color: string; bar: string }
> = {
  retrieve: {
    label: "Retrieve",
    short: "Menemukan info",
    description: "Menemukan informasi yang tertulis langsung di bacaan.",
    color: "text-sky-600",
    bar: "bg-sky-500",
  },
  interpret: {
    label: "Interpret",
    short: "Memahami isi",
    description: "Menghubungkan dan memahami maksud isi bacaan.",
    color: "text-violet-600",
    bar: "bg-violet-500",
  },
  reflect: {
    label: "Reflect",
    short: "Menilai isi",
    description: "Menilai dan merenungkan isi bacaan.",
    color: "text-teal-600",
    bar: "bg-teal-500",
  },
};

/** Ambang batas MVP (§15, BR-02). BUKAN standar nasional. */
export const THRESHOLDS = {
  accuracy: { low: 90, high: 95 }, // <90 perlu intervensi; >=95 baik
  comprehension: 80, // <80 → intervensi kompetensi
} as const;

/** Klasifikasi akurasi untuk pewarnaan (§15). */
export function accuracyLevel(accuracy: number): "low" | "mid" | "high" {
  if (accuracy < THRESHOLDS.accuracy.low) return "low";
  if (accuracy < THRESHOLDS.accuracy.high) return "mid";
  return "high";
}

/** Aturan penilaian kata (§13.2). */
export function decideWord(confidence: number, isProperNoun = false): WordDecision {
  if (isProperNoun) return "correct";
  return confidence > 0.5 ? "correct" : "incorrect";
}

/** WCPM (§14): Correct Words / Reading Time (detik) × 60. */
export function computeWCPM(correctWords: number, readingTimeSec: number): number {
  if (readingTimeSec <= 0) return 0;
  return Math.round((correctWords / readingTimeSec) * 60);
}

/** Accuracy (§15): Correct Words / Total Words Read × 100%. */
export function computeAccuracy(correctWords: number, totalWordsRead: number): number {
  if (totalWordsRead <= 0) return 0;
  return Math.round((correctWords / totalWordsRead) * 100);
}

/** Rata-rata tiga kompetensi pemahaman (Retrieve/Interpret/Reflect). */
export function averageComprehension(c: {
  retrieve: number;
  interpret: number;
  reflect: number;
}): number {
  return Math.round((c.retrieve + c.interpret + c.reflect) / 3);
}

/**
 * Level bacaan yang disarankan bila siswa belum punya riwayat asesmen (§29).
 * Default: tingkat kelas 1–3 dipetakan langsung ke Level 1–3.
 */
export function suggestedLevelForGrade(grade: 1 | 2 | 3): 1 | 2 | 3 {
  return grade;
}

/** Disclaimer wajib (design-system.md §7.16). */
export const DISCLAIMERS = {
  hasbrouck:
    "Reference based on Hasbrouck & Tindal ORF norms. This is not an Indonesian national normative benchmark.",
  threshold:
    "Ambang batas ini adalah aturan MVP, bukan standar nasional Indonesia.",
  medical: "BacaLaras membantu asesmen, bukan alat diagnosis medis.",
} as const;
