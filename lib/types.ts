/**
 * BacaLaras — Tipe domain frontend.
 *
 * Tipe di sini adalah "view model" yang dipakai komponen UI. Pemetaan dari
 * respons API backend (snake_case) ke bentuk ini dilakukan di `lib/api.ts`.
 * Tidak ada logika Adaptive Engine di sini — engine tetap di backend.
 */
import type { AdaptiveStatus, Competency } from "./tokens";

export interface Teacher {
  id: string;
  name: string;
  email: string;
}

export interface ClassRoom {
  id: string;
  name: string;
  grade: 1 | 2 | 3;
  studentCount: number;
}

export interface Student {
  id: string;
  name: string;
  grade: 1 | 2 | 3;
  classId: string;
  classLabel: string;
  assessmentCount: number;
}

export interface ComprehensionScore {
  retrieve: number;
  interpret: number;
  reflect: number;
}

/** Keputusan kata untuk traceability (P1) — tanpa label jenis kesalahan. */
export interface WordScoreView {
  position: number;
  /** Kata pada teks acuan (bacaan). */
  word: string;
  /** Kata hasil transkrip ASR (bisa null bila kata terlewat). */
  transcriptWord: string | null;
  confidence: number | null;
  /** D1: kata dicoba dibaca (match/substitution). */
  attempted: boolean;
  isCorrect: boolean;
  isProperNoun: boolean;
  reason: string;
  /** Sinyal "perlu diperiksa" dari framework (review flags), bukan vonis. */
  reviewReasons: string[];
}

export interface AssessmentResult {
  id: string;
  studentId: string;
  readingId: string;
  /** ISO date-time. */
  date: string;
  readingTitle: string;
  readingLevel: 1 | 2 | 3;
  wcpm: number | null;
  accuracy: number | null;
  correctWords: number;
  incorrectWords: number;
  totalWordsRead: number;
  readingTimeSec: number;
  transcript: string;
  comprehension: ComprehensionScore;
  status: AdaptiveStatus;
  recommendation: string;
  nextReadingLevel: 1 | 2 | 3;
  rulesFired: { rule: string; text: string; passed: boolean }[];
  wordScores: WordScoreView[];
  /** true bila hasil berasal dari mode demo (replay), bukan model nyata. */
  isDemoFallback: boolean;
  sessionState: string;
  season?: string;
}

export interface ReadingQuestion {
  id: string;
  competency: Competency;
  prompt: string;
  options: { id: string; text: string }[];
  answerId: string;
}

export interface ReadingText {
  id: string;
  title: string;
  content: string;
  grade: 1 | 2 | 3;
  level: 1 | 2 | 3;
  wordCount: number;
  theme: string;
  /** Estimasi durasi baca (detik) untuk metadata kartu bacaan. */
  estimatedSeconds: number;
  questions: ReadingQuestion[];
}

/** Satu titik tren untuk grafik progres. */
export interface TrendPoint {
  assessmentId: string;
  date: string;
  wcpm: number | null;
  accuracy: number | null;
  comprehension: ComprehensionScore;
}

/** Baris siswa pada dashboard kelas (menggabungkan status engine + metrik). */
export interface DashboardStudentRow {
  studentId: string;
  name: string;
  grade: 1 | 2 | 3;
  wcpm: number | null;
  accuracy: number | null;
  comprehension: ComprehensionScore | null;
  /** Status keputusan engine (null = belum ada asesmen COMPLETED). */
  status: AdaptiveStatus | null;
  recommendation: string;
  trend: TrendPoint[];
}

export interface ClassDashboard {
  classId: string;
  className: string;
  grade: 1 | 2 | 3;
  totalStudents: number;
  students: DashboardStudentRow[];
}

/** Posisi WCPM terhadap referensi Hasbrouck–Tindal (F-11). */
export interface HasbrouckPosition {
  available: boolean;
  position?: string;
  label?: string;
  wcpm: number;
  grade: number;
  season: string;
  p25?: number;
  p50?: number;
  disclaimer: string;
  todoVerify: boolean;
  reason?: string;
}
