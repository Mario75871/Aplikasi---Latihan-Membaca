/**
 * lib/api.ts — Klien REST bertipe untuk backend BacaLaras (Fase 3).
 *
 * Prinsip:
 * - Satu tempat untuk base URL, token, dan error terstruktur.
 * - Tidak ada logika Adaptive Engine di sini; engine tetap di backend.
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

/**
 * Base URL backend yang dipakai `request()`.
 *
 * - **Browser** → `/api/proxy` (same-origin). Route handler proxy membaca cookie
 *   httpOnly lalu menyuntik `Authorization: Bearer` (integrasi #5, Fase 0) — token
 *   tak pernah terlihat JS.
 * - **Server component** → langsung ke backend (`API_BASE_URL`), token dikirim
 *   eksplisit via `options.token` (dari `getServerToken()`).
 */
export function apiBaseUrl(): string {
  if (typeof window !== "undefined") return "/api/proxy";
  return (
    process.env.API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    "http://localhost:8000"
  );
}

/** Nama cookie penyimpan token sesi (httpOnly; hanya di-set server — integrasi #4, D5). */
export const TOKEN_COOKIE = "bacalaras_token";

/**
 * Simpan token sesi via route handler server (cookie **httpOnly**).
 * JS tidak dapat membaca token setelah ini (aman dari XSS).
 */
export async function setSessionToken(token: string): Promise<void> {
  if (typeof window === "undefined") return;
  await fetch("/api/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  });
}

/** Hapus cookie sesi via route handler server. */
export async function clearSessionToken(): Promise<void> {
  if (typeof window === "undefined") return;
  try {
    await fetch("/api/session", { method: "DELETE" });
  } catch {
    /* best-effort */
  }
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
  // Token eksplisit (server component). Di browser, otentikasi dilakukan oleh proxy
  // same-origin (`/api/proxy`) yang membaca cookie httpOnly → Bearer (integrasi #5,
  // Fase 0): token tak pernah terlihat JS.
  const token = options.token ?? undefined;
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
      // Same-origin (proxy) sudah otomatis membawa cookie; `include` dipertahankan
      // agar tetap benar bila base URL diarahkan ke backend langsung (mis. server).
      credentials: "include",
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
    // Integrasi #4 (D.2): 401 → sesi kedaluwarsa/tidak valid. Di browser, bersihkan
    // cookie sesi & arahkan ke login (kecuali request ke /auth/login itu sendiri).
    if (res.status === 401 && typeof window !== "undefined" && !path.startsWith("/auth/login")) {
      void clearSessionToken();
      const next = window.location.pathname + window.location.search;
      const loginUrl = `/login?next=${encodeURIComponent(next)}`;
      if (!window.location.pathname.startsWith("/login")) {
        window.location.assign(loginUrl);
      }
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
  wcpm?: number | null;
  accuracy?: number | null;
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
    wcpm: number | null;
    accuracy: number | null;
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
    wcpm: raw.wcpm ?? null,
    accuracy: raw.accuracy ?? null,
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
// Endpoint: Config (ambang resmi — integrasi #4, D.1 / aturan #9)
// ─────────────────────────────────────────────────────────────

export interface Thresholds {
  accuracyLow: number;
  accuracyHigh: number;
  comprehensionMin: number;
}

interface RawThresholds {
  accuracy_low: number;
  accuracy_high: number;
  comprehension_min: number;
}

/** Cache nilai ambang dari server selama sesi (hindari permintaan berulang). */
let _thresholdsCache: Thresholds | null = null;

/**
 * Ambil ambang resmi dari backend (`GET /config/thresholds`).
 *
 * Integrasi #4 (D.1): frontend **mengonsumsi** nilai ini saat runtime (satu sumber
 * kebenaran), bukan hanya via test anti-drift. Nilai statis di `lib/tokens.ts` tetap
 * dipakai sebagai **fallback** bila permintaan gagal — frontend tetap HANYA presentasi.
 */
export async function getThresholds(token?: string | null): Promise<Thresholds> {
  if (_thresholdsCache) return _thresholdsCache;
  const raw = await request<RawThresholds>("/config/thresholds", { token });
  const value: Thresholds = {
    accuracyLow: raw.accuracy_low,
    accuracyHigh: raw.accuracy_high,
    comprehensionMin: raw.comprehension_min,
  };
  _thresholdsCache = value;
  return value;
}

/** Kosongkan cache ambang (untuk test / setelah logout). */
export function resetThresholdsCache(): void {
  _thresholdsCache = null;
}

// ─────────────────────────────────────────────────────────────
// Konfigurasi audio (integrasi #6, D1) — runtime FE tahu batas durasi
// ─────────────────────────────────────────────────────────────

export interface AudioConfig {
  targetSampleRate: number;
  maxAudioBytes: number;
  maxAudioDurationSec: number;
}

interface RawAudioConfig {
  target_sample_rate: number;
  max_audio_bytes: number;
  max_audio_duration_sec: number;
}

let _audioConfigCache: AudioConfig | null = null;

/**
 * Ambil konfigurasi audio resmi dari backend (`GET /config/audio`).
 *
 * Integrasi #6 (D1c): FE **mengonsumsi** batas durasi (bukan hanya 10 MB) saat runtime
 * — siswa ditolak di klien sebelum upload besar, bukan setelah menunggu 422. Bila
 * permintaan gagal → `null` (pemanggil memakai fallback konstanta cermin backend di
 * `lib/audio-wav.ts`). Frontend tetap HANYA presentasi: keputusan tetap di backend.
 */
export async function getAudioConfig(
  token?: string | null
): Promise<AudioConfig | null> {
  if (_audioConfigCache) return _audioConfigCache;
  try {
    const raw = await request<RawAudioConfig>("/config/audio", { token });
    const value: AudioConfig = {
      targetSampleRate: raw.target_sample_rate,
      maxAudioBytes: raw.max_audio_bytes,
      maxAudioDurationSec: raw.max_audio_duration_sec,
    };
    _audioConfigCache = value;
    return value;
  } catch {
    return null; // pemanggil memakai fallback konstanta (null-safe)
  }
}

/** Kosongkan cache konfigurasi audio (untuk test / setelah logout). */
export function resetAudioConfigCache(): void {
  _audioConfigCache = null;
}

export interface RegisterResponse {
  token: string;
  username: string;
  expiresAt: string;
}

/**
 * Daftar akun guru baru (FR-01 lanjutan).
 *
 * CATATAN: backend `POST /auth/register` BELUM tersedia (backend hanya punya
 * `/auth/login` + `/auth/logout`). Fungsi ini disiapkan agar begitu endpoint ada,
 * frontend langsung jalan. Selama endpoint belum ada, pemanggil akan menerima
 * ApiError dan menampilkan pesan ramah ("Pendaftaran belum tersedia").
 */
export async function register(
  name: string,
  email: string,
  password: string
): Promise<RegisterResponse> {
  const raw = await request<{ token: string; username: string; expires_at: string }>(
    "/auth/register",
    { method: "POST", body: { name, email, password }, token: null }
  );
  return { token: raw.token, username: raw.username, expiresAt: raw.expires_at };
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
  wcpm: number | null;
  accuracy: number | null;
  isDemoFallback: boolean;
}

/** Upload audio → jalankan pipeline ASR + penilaian kata di backend. */
export async function uploadAssessmentAudio(
  assessmentId: string,
  blob: Blob,
  filename = "rekaman.wav",
  token?: string | null
): Promise<UploadAudioResult> {
  // Integrasi #6 (Fase D, Opsi A): unggah langsung ke Supabase Storage via signed
  // URL (bypass batas body Vercel 4.5 MB), lalu minta backend memproses objek itu.
  const signed = await getAudioUploadUrl(assessmentId, token).catch(() => null);
  if (signed && signed.mode === "signed" && signed.signed_url) {
    try {
      const put = await fetch(signed.signed_url, {
        method: "PUT",
        body: blob,
        headers: {
          "content-type": blob.type || "audio/wav",
          "x-upsert": "true",
        },
      });
      if (!put.ok) throw new Error(`upload ${put.status}`);
      const raw = await request<RawAssessment>(`/assessments/${assessmentId}/audio`, {
        method: "POST",
        body: { audio_path: signed.path },
        token,
      });
      return {
        assessmentId: raw.id,
        wcpm: raw.wcpm ?? null,
        accuracy: raw.accuracy ?? null,
        isDemoFallback: Boolean(raw.is_demo_fallback),
      };
    } catch {
      // jatuh ke fallback multipart di bawah
    }
  }

  // Fallback (mode demo/in-memory, Storage tak dikonfigurasi, atau PUT gagal).
  const form = new FormData();
  form.append("audio", blob, filename);
  const raw = await request<RawAssessment>(`/assessments/${assessmentId}/audio`, {
    method: "POST",
    form,
    token,
  });
  return {
    assessmentId: raw.id,
    wcpm: raw.wcpm ?? null,
    accuracy: raw.accuracy ?? null,
    isDemoFallback: Boolean(raw.is_demo_fallback),
  };
}

/** Bentuk respons `POST /assessments/{id}/audio/upload-url` (integrasi #6, Opsi A). */
export interface AudioUploadUrl {
  mode: "signed" | "multipart";
  path?: string;
  signed_url?: string;
  token?: string;
}

/**
 * Minta signed upload URL agar browser mengunggah audio **langsung ke Supabase**
 * (bypass Vercel). Bila Storage tak dikonfigurasi → `mode: "multipart"`.
 */
export async function getAudioUploadUrl(
  assessmentId: string,
  token?: string | null
): Promise<AudioUploadUrl> {
  return request<AudioUploadUrl>(
    `/assessments/${assessmentId}/audio/upload-url`,
    { method: "POST", token }
  );
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

/**
 * Ambil signed URL audio untuk asesmen (integrasi #5, D3). `null` bila rekaman
 * tidak tersedia (404) atau gagal (502) — pemanggil menampilkan pesan, bukan error.
 * Signed URL berumur pendek (~10 menit) → jangan di-cache lama.
 */
export async function getAssessmentAudioUrl(
  assessmentId: string,
  token?: string | null
): Promise<string | null> {
  try {
    const res = await request<{ url: string; expires_in: number }>(
      `/assessments/${assessmentId}/audio-url`,
      { token }
    );
    return res.url ?? null;
  } catch {
    return null;
  }
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
