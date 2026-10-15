/**
 * lib/api.ts — Klien REST bertipe untuk backend BacaLaras (Fase 3).
 *
 * Prinsip:
 * - Satu tempat untuk base URL, token, dan error terstruktur.
 * - Tidak ada logika Adaptive Engine di sini; engine tetap di backend (§38.2).
 * - Respons backend (snake_case) dipetakan ke view model camelCase di `lib/types.ts`
 *   sehingga komponen UI tidak perlu tahu bentuk mentah API.
 * - Aman dipakai di server component (token dari cookie) maupun client component
 *   (token dari cookie di browser). Tidak mengimpor `next/headers` di sini.
 */
import type {
  AdaptiveStatus,
  Competency,
} from "./tokens";
import type {
  AssessmentResult,
  ClassDashboard,
  ClassRoom,
  DashboardStudentRow,
  HasbrouckPosition,
  ReadingText,
  Student,
  TrendPoint,
  WordScoreView,
} from "./types";

// ─────────────────────────────────────────────────────────────
// Konfigurasi & token
// ─────────────────────────────────────────────────────────────

/** Base URL backend. Server pakai API_BASE_URL, browser pakai NEXT_PUBLIC_API_BASE_URL. */
export function apiBaseUrl(): string {
  return (
    process.env.API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    "http://localhost:8000"
  );
}

/** Nama cookie penyimpan token sesi (dibaca server component & browser). */
export const TOKEN_COOKIE = "bacalaras_token";

/** Baca token dari cookie di browser. Di server kembalikan null (pakai param eksplisit). */
export function getClientToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(
    new RegExp("(?:^|; )" + TOKEN_COOKIE + "=([^;]*)")
  );
  return match ? decodeURIComponent(match[1]) : null;
}

/** Simpan token di cookie (bukan httpOnly; MVP sederhana sesuai D7). */
export function setClientToken(token: string, maxAgeSec = 60 * 60 * 12): void {
  if (typeof document === "undefined") return;
  document.cookie = `${TOKEN_COOKIE}=${encodeURIComponent(token)}; path=/; max-age=${maxAgeSec}; samesite=lax`;
}

/** Hapus token dari cookie. */
export function clearClientToken(): void {
  if (typeof document === "undefined") return;
  document.cookie = `${TOKEN_COOKIE}=; path=/; max-age=0; samesite=lax`;
}

// ─────────────────────────────────────────────────────────────
// Error terstruktur
// ─────────────────────────────────────────────────────────────

/** Error API terstruktur — membawa status HTTP + pesan detail dari backend. */
export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }

  /** true bila penyebabnya autentikasi (401). */
  get isUnauthorized(): boolean {
    return this.status === 401;
  }
}

// ─────────────────────────────────────────────────────────────
// Request inti
// ─────────────────────────────────────────────────────────────

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  /** FormData (upload audio) — bila diisi, body diabaikan. */
  form?: FormData;
  /** Token eksplisit (dipakai server component). Bila kosong, ambil dari cookie. */
  token?: string | null;
  signal?: AbortSignal;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const token = options.token ?? getClientToken();
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;

  let body: BodyInit | undefined;
  if (options.form) {
    body = options.form;
  } else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }

  let res: Response;
  try {
    res = await fetch(`${apiBaseUrl()}${path}`, {
      method: options.method ?? "GET",
      headers,
      body,
      signal: options.signal,
      cache: "no-store",
    });
  } catch {
    throw new ApiError(0, "Tidak dapat menghubungi server. Periksa koneksi lalu coba lagi.");
  }

  if (!res.ok) {
    let detail = `Permintaan gagal (${res.status}).`;
    try {
      const data = await res.json();
      if (typeof data?.detail === "string") detail = data.detail;
      else if (Array.isArray(data?.detail)) detail = "Data yang dikirim tidak valid.";
    } catch {
      /* biarkan pesan default */
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// ─────────────────────────────────────────────────────────────
// Tipe respons mentah backend (snake_case)
// ─────────────────────────────────────────────────────────────

interface RawStudent {
  id: string;
  name: string;
  grade: number;
  class_id: string;
}

interface RawClass {
  id: string;
  name: string;
  grade: number;
}

interface RawReadingQuestion {
  id: string;
  competency: string;
  prompt: string;
  options: { id: string; text: string }[];
  answer_id: string;
}

interface RawReading {
  id: string;
  title: string;
  content: string;
  grade: number;
  complexity: number;
  book_level: string;
  word_count?: number;
  theme?: string;
  proper_nouns?: string[];
  questions?: RawReadingQuestion[];
}

interface RawWordScore {
  position: number;
  reference_word: string | null;
  transcript_word: string | null;
  confidence: number | null;
  attempted: boolean;
  is_correct: boolean;
  is_proper_noun: boolean;
  reason: string;
  review_reasons: string[];
}

interface RawRuleFired {
  rule: string;
  text: string;
  fired: boolean;
}

interface RawAssessment {
  id: string;
  student_id: string;
  reading_id: string;
  status: string;
  session_state: string;
  created_at: string;
  completed_at?: string;
  wcpm?: number;
  accuracy?: number;
  correct_words?: number;
  incorrect_words?: number;
  total_words_read?: number;
  reading_time_sec?: number;
  transcript?: string;
  word_scores?: RawWordScore[];
  is_demo_fallback?: boolean;
  retrieve?: number;
  interpret?: number;
  reflect?: number;
  recommendation?: string;
  next_reading_level?: number;
  rules_fired?: RawRuleFired[];
  season?: string;
}

interface RawDashboardStudent {
  student_id: string;
  name: string;
  grade: number;
  wcpm: number | null;
  accuracy: number | null;
  comprehension: { retrieve: number; interpret: number; reflect: number } | null;
  status: string;
  adaptive_status: string | null;
  recommendation: string;
  trend: {
    assessment_id: string;
    date: string;
    wcpm: number;
    accuracy: number;
    comprehension: { retrieve: number; interpret: number; reflect: number };
  }[];
}

interface RawClassDashboard {
  class_id: string;
  class_name: string;
  grade: number;
  total_students: number;
  status_summary: Record<string, number>;
  students: RawDashboardStudent[];
}

interface RawHasbrouck {
  available: boolean;
  position?: string;
  label?: string;
  wcpm: number;
  grade: number;
  season: string;
  p25?: number;
  p50?: number;
  disclaimer: string;
  todo_verify: boolean;
  reason?: string;
}

// ─────────────────────────────────────────────────────────────
// Pemetaan (adapter) respons mentah → view model
// ─────────────────────────────────────────────────────────────

function asGrade(value: number): 1 | 2 | 3 {
  return (value === 1 || value === 2 || value === 3 ? value : 1) as 1 | 2 | 3;
}

function asLevel(value: number): 1 | 2 | 3 {
  return (value === 1 || value === 2 || value === 3 ? value : 1) as 1 | 2 | 3;
}

function asCompetency(value: string): Competency {
  return (value === "retrieve" || value === "interpret" || value === "reflect"
    ? value
    : "retrieve") as Competency;
}

function asStatus(value: string | null | undefined): AdaptiveStatus | null {
  if (value === "INTERVENE" || value === "STAY" || value === "PROMOTION_CANDIDATE" || value === "PROMOTE") {
    return value;
  }
  return null;
}

/** Hitung jumlah kata dari konten (konsisten untuk metadata kartu bacaan). */
function countWords(text: string): number {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

export function mapReading(raw: RawReading): ReadingText {
  const wordCount = raw.word_count ?? countWords(raw.content);
  // Estimasi durasi baca: asumsi ~40 kata/menit untuk siswa kelas 1–3.
  const estimatedSeconds = Math.round((wordCount / 40) * 60);
  return {
    id: raw.id,
    title: raw.title,
    content: raw.content,
    grade: asGrade(raw.grade),
    level: asLevel(raw.complexity),
    wordCount,
    theme: raw.theme ?? "Umum",
    estimatedSeconds,
    questions: (raw.questions ?? []).map((q) => ({
      id: q.id,
      competency: asCompetency(q.competency),
      prompt: q.prompt,
      options: q.options,
      answerId: q.answer_id,
    })),
  };
}

function mapWordScore(raw: RawWordScore): WordScoreView {
  return {
    position: raw.position,
    word: raw.reference_word ?? raw.transcript_word ?? "—",
    transcriptWord: raw.transcript_word,
    confidence: raw.confidence,
    attempted: raw.attempted,
    isCorrect: raw.is_correct,
    isProperNoun: raw.is_proper_noun,
    reason: raw.reason,
    reviewReasons: raw.review_reasons ?? [],
  };
}

function mapAssessment(raw: RawAssessment, readingTitle = "", readingLevel: 1 | 2 | 3 = 1): AssessmentResult {
  return {
    id: raw.id,
    studentId: raw.student_id,
    readingId: raw.reading_id,
    date: raw.completed_at ?? raw.created_at,
    readingTitle,
    readingLevel,
    wcpm: raw.wcpm ?? 0,
    accuracy: raw.accuracy ?? 0,
    correctWords: raw.correct_words ?? 0,
    incorrectWords: raw.incorrect_words ?? 0,
    totalWordsRead: raw.total_words_read ?? 0,
    readingTimeSec: raw.reading_time_sec ?? 0,
    transcript: raw.transcript ?? "",
    comprehension: {
      retrieve: raw.retrieve ?? 0,
      interpret: raw.interpret ?? 0,
      reflect: raw.reflect ?? 0,
    },
    status: asStatus(raw.status) ?? "STAY",
    recommendation: raw.recommendation ?? "",
    nextReadingLevel: asLevel(raw.next_reading_level ?? readingLevel),
    rulesFired: (raw.rules_fired ?? []).map((r) => ({
      rule: r.rule,
      text: r.text,
      passed: r.fired,
    })),
    wordScores: (raw.word_scores ?? []).map(mapWordScore),
    isDemoFallback: Boolean(raw.is_demo_fallback),
    sessionState: raw.session_state,
    season: raw.season,
  };
}

function mapDashboardStudent(raw: RawDashboardStudent): DashboardStudentRow {
  return {
    studentId: raw.student_id,
    name: raw.name,
    grade: asGrade(raw.grade),
    wcpm: raw.wcpm,
    accuracy: raw.accuracy,
    comprehension: raw.comprehension,
    status: asStatus(raw.adaptive_status),
    recommendation: raw.recommendation,
    trend: raw.trend.map((t) => ({
      assessmentId: t.assessment_id,
      date: t.date,
      wcpm: t.wcpm,
      accuracy: t.accuracy,
      comprehension: t.comprehension,
    })),
  };
}

// ─────────────────────────────────────────────────────────────
// Endpoint: Auth (D7)
// ─────────────────────────────────────────────────────────────

export interface LoginResponse {
  token: string;
  username: string;
  expiresAt: string;
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const raw = await request<{ token: string; username: string; expires_at: string }>(
    "/auth/login",
    { method: "POST", body: { username, password }, token: null }
  );
  return { token: raw.token, username: raw.username, expiresAt: raw.expires_at };
}

export async function logout(token?: string | null): Promise<void> {
  try {
    await request<{ status: string }>("/auth/logout", { method: "POST", token });
  } catch {
    /* logout bersifat best-effort; cookie tetap dibersihkan di pemanggil */
  }
}

// ─────────────────────────────────────────────────────────────
// Endpoint: Kelas, Siswa, Bacaan
// ─────────────────────────────────────────────────────────────

export async function listClasses(token?: string | null): Promise<ClassRoom[]> {
  const raws = await request<RawClass[]>("/classes", { token });
  return raws.map((c) => ({
    id: c.id,
    name: c.name,
    grade: asGrade(c.grade),
    studentCount: 0,
  }));
}

export async function getClass(classId: string, token?: string | null): Promise<ClassRoom | null> {
  try {
    const c = await request<RawClass>(`/classes/${classId}`, { token });
    return { id: c.id, name: c.name, grade: asGrade(c.grade), studentCount: 0 };
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  }
}

export async function listStudents(token?: string | null): Promise<Student[]> {
  const [students, classes] = await Promise.all([
    request<RawStudent[]>("/students", { token }),
    request<RawClass[]>("/classes", { token }),
  ]);
  const classNames = new Map(classes.map((c) => [c.id, c.name]));
  return students.map((s) => ({
    id: s.id,
    name: s.name,
    grade: asGrade(s.grade),
    classId: s.class_id,
    classLabel: classNames.get(s.class_id) ?? "Tanpa kelas",
    assessmentCount: 0,
  }));
}

export async function getStudent(studentId: string, token?: string | null): Promise<Student | null> {
  try {
    const [s, classes] = await Promise.all([
      request<RawStudent>(`/students/${studentId}`, { token }),
      request<RawClass[]>("/classes", { token }),
    ]);
    const classNames = new Map(classes.map((c) => [c.id, c.name]));
    return {
      id: s.id,
      name: s.name,
      grade: asGrade(s.grade),
      classId: s.class_id,
      classLabel: classNames.get(s.class_id) ?? "Tanpa kelas",
      assessmentCount: 0,
    };
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  }
}

export async function listReadings(token?: string | null): Promise<ReadingText[]> {
  const raws = await request<RawReading[]>("/readings", { token });
  return raws.map(mapReading);
}

export async function getReading(
  readingId: string | null | undefined,
  token?: string | null
): Promise<ReadingText | null> {
  if (!readingId) return null;
  try {
    const raw = await request<RawReading>(`/readings/${readingId}`, { token });
    return mapReading(raw);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  }
}

// ─────────────────────────────────────────────────────────────
// Endpoint: Asesmen (alur end-to-end)
// ─────────────────────────────────────────────────────────────

export interface CreateAssessmentResult {
  id: string;
  studentId: string;
  readingId: string;
}

export async function createAssessment(
  studentId: string,
  readingId: string,
  token?: string | null
): Promise<CreateAssessmentResult> {
  const raw = await request<RawAssessment>("/assessments", {
    method: "POST",
    body: { student_id: studentId, reading_id: readingId },
    token,
  });
  return { id: raw.id, studentId: raw.student_id, readingId: raw.reading_id };
}

export interface UploadAudioResult {
  assessmentId: string;
  wcpm: number;
  accuracy: number;
  isDemoFallback: boolean;
}

/** Upload audio → jalankan pipeline ASR + penilaian kata di backend. */
export async function uploadAssessmentAudio(
  assessmentId: string,
  blob: Blob,
  filename = "rekaman.webm",
  token?: string | null
): Promise<UploadAudioResult> {
  const form = new FormData();
  form.append("audio", blob, filename);
  const raw = await request<RawAssessment>(`/assessments/${assessmentId}/audio`, {
    method: "POST",
    form,
    token,
  });
  return {
    assessmentId: raw.id,
    wcpm: raw.wcpm ?? 0,
    accuracy: raw.accuracy ?? 0,
    isDemoFallback: Boolean(raw.is_demo_fallback),
  };
}

export async function submitComprehension(
  assessmentId: string,
  answers: Record<string, string>,
  token?: string | null
): Promise<AssessmentResult> {
  const raw = await request<RawAssessment>(`/assessments/${assessmentId}/comprehension`, {
    method: "POST",
    body: { answers },
    token,
  });
  return mapAssessment(raw);
}

/** Ambil detail asesmen + judul/level bacaan (join di klien via `/readings`). */
export async function getAssessment(
  assessmentId: string,
  token?: string | null
): Promise<AssessmentResult | null> {
  let raw: RawAssessment;
  try {
    raw = await request<RawAssessment>(`/assessments/${assessmentId}`, { token });
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  }
  const reading = await getReading(raw.reading_id, token).catch(() => null);
  return mapAssessment(raw, reading?.title ?? "", reading?.level ?? 1);
}

/** Riwayat asesmen COMPLETED untuk satu siswa (urut lama → baru). */
export async function listStudentAssessments(
  studentId: string,
  token?: string | null
): Promise<AssessmentResult[]> {
  const raws = await request<RawAssessment[]>(`/assessments?student_id=${encodeURIComponent(studentId)}`, {
    token,
  });
  const completed = raws.filter((a) => a.session_state === "COMPLETED");
  const readings = await listReadings(token).catch(() => []);
  const readingMap = new Map(readings.map((r) => [r.id, r]));
  return completed
    .map((a) => {
      const r = readingMap.get(a.reading_id);
      return mapAssessment(a, r?.title ?? "", r?.level ?? 1);
    })
    .sort((a, b) => a.date.localeCompare(b.date));
}

/** Riwayat semua asesmen COMPLETED (untuk halaman Asesmen). */
export async function listAllAssessments(token?: string | null): Promise<AssessmentResult[]> {
  const raws = await request<RawAssessment[]>("/assessments", { token });
  const completed = raws.filter((a) => a.session_state === "COMPLETED");
  const [readings, students] = await Promise.all([
    listReadings(token).catch(() => []),
    listStudents(token).catch(() => []),
  ]);
  const readingMap = new Map(readings.map((r) => [r.id, r]));
  const studentMap = new Map(students.map((s) => [s.id, s]));
  return completed
    .map((a) => {
      const r = readingMap.get(a.reading_id);
      const view = mapAssessment(a, r?.title ?? "", r?.level ?? 1);
      (view as AssessmentResult & { studentName?: string }).studentName =
        studentMap.get(a.student_id)?.name ?? a.student_id;
      return view;
    })
    .sort((a, b) => b.date.localeCompare(a.date));
}

// ─────────────────────────────────────────────────────────────
// Endpoint: Dashboard kelas & referensi Hasbrouck
// ─────────────────────────────────────────────────────────────

export async function getClassDashboard(
  classId: string,
  token?: string | null
): Promise<ClassDashboard | null> {
  let raw: RawClassDashboard;
  try {
    raw = await request<RawClassDashboard>(`/dashboard/class/${classId}`, { token });
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  }
  return {
    classId: raw.class_id,
    className: raw.class_name,
    grade: asGrade(raw.grade),
    totalStudents: raw.total_students,
    students: raw.students.map(mapDashboardStudent),
  };
}

export async function getHasbrouckReference(
  grade: number,
  season: string,
  wcpm: number,
  token?: string | null
): Promise<HasbrouckPosition> {
  const params = new URLSearchParams({ grade: String(grade), wcpm: String(wcpm) });
  if (season) params.set("season", season);
  const raw = await request<RawHasbrouck>(
    `/hasbrouck/reference?${params.toString()}`,
    { token }
  );
  return {
    available: raw.available,
    position: raw.position,
    label: raw.label,
    wcpm: raw.wcpm,
    grade: raw.grade,
    season: raw.season,
    p25: raw.p25,
    p50: raw.p50,
    disclaimer: raw.disclaimer,
    todoVerify: raw.todo_verify,
    reason: raw.reason,
  };
}

export type { TrendPoint };
