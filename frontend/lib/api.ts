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
 * - Pengambil koleksi dibungkus `cache()` React dan pencarian tabel dijalankan
 *   bersamaan dengan pengambilan induknya, supaya satu render tidak menunggu
 *   beberapa permintaan berurutan (lihat catatan di tiap fungsi).
 */
import { cache } from "react";
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
 * JS tidak dapat membaca token setelah ini (aman dari XSS). Ganti `setClientToken`.
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
  /**
   * Umur cache data Next (detik) untuk endpoint yang isinya **identik bagi semua
   * pengguna**. Bila diisi, `cache: "no-store"` diganti `next: { revalidate }`.
   *
   * ⚠️ Cache data Next dibagi antar-pengguna dalam satu deployment. Isi opsi ini
   * HANYA untuk endpoint global yang tidak di-scope ke guru (mis. katalog bacaan,
   * lihat `list_readings()` di `backend/repository.py` yang tidak menerima
   * `teacher_id`). Untuk endpoint milik guru, biarkan kosong — jawabannya berbeda
   * per akun dan akan bocor antar-sesi.
   */
  revalidate?: number;
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
      // Bila `revalidate` diisi, `cache` dibiarkan kosong supaya Next memakai cache
      // berjangka; selain itu selalu `no-store` — data guru tidak boleh basi
      // sesudah menyimpan kelas/siswa/asesmen.
      cache: options.revalidate ? undefined : "no-store",
      next: options.revalidate ? { revalidate: options.revalidate } : undefined,
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
    // cookie sesi & arahkan ke login. Dikecualikan untuk endpoint identitas pra-sesi
    // (login & daftar): di sana 401 berarti "kode/tiket salah", bukan "sesi habis" —
    // mengalihkan pengguna akan membuang isian formulirnya di tengah alur.
    const isIdentityPath =
      path.startsWith("/auth/login") || path.startsWith("/auth/signup/");
    if (res.status === 401 && typeof window !== "undefined" && !isIdentityPath) {
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
// Endpoint: Daftar akun (integrasi #7)
// Alur tiga langkah: kirim kode → verifikasi kode → buat password.
// Pengguna BELUM login setelah langkah 2; `signupVerify` mengembalikan tiket
// sementara, bukan sesi. Akun baru lahir di `signupComplete`, dan hanya hasil
// langkah itu yang disimpan sebagai token sesi.
// ─────────────────────────────────────────────────────────────

export interface SignupStartResponse {
  email: string;
  expiresInSec: number;
  resendAfterSec: number;
}

export interface SignupVerifyResponse {
  /** Tiket sementara — bukan token sesi. Hanya berlaku untuk `signupComplete`. */
  ticket: string;
  email: string;
  name: string;
  expiresAt: string;
}

/** Langkah 1 — minta kode verifikasi dikirim ke `email`. */
export async function signupStart(
  email: string,
  name: string
): Promise<SignupStartResponse> {
  const raw = await request<{
    status: string;
    email: string;
    expires_at: string;
    expires_in_sec: number;
    resend_after_sec: number;
  }>("/auth/signup/start", {
    method: "POST",
    body: { email, name },
    token: null,
  });
  return {
    email: raw.email,
    expiresInSec: raw.expires_in_sec,
    resendAfterSec: raw.resend_after_sec,
  };
}

/** Langkah 2 — verifikasi kode. Mengembalikan tiket, bukan sesi. */
export async function signupVerify(
  email: string,
  code: string
): Promise<SignupVerifyResponse> {
  const raw = await request<{
    ticket: string;
    email: string;
    name: string;
    expires_at: string;
  }>("/auth/signup/verify", {
    method: "POST",
    body: { email, code },
    token: null,
  });
  return {
    ticket: raw.ticket,
    email: raw.email,
    name: raw.name,
    expiresAt: raw.expires_at,
  };
}

/**
 * Langkah 3 — buat password & akun.
 *
 * Bentuk balasannya identik dengan `login()`, jadi pemanggil memakai ulang
 * `setSessionToken()` yang sama.
 */
export async function signupComplete(
  ticket: string,
  password: string
): Promise<LoginResponse> {
  const raw = await request<{ token: string; username: string; expires_at: string }>(
    "/auth/signup/complete",
    { method: "POST", body: { ticket, password }, token: null }
  );
  return { token: raw.token, username: raw.username, expiresAt: raw.expires_at };
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

// ─────────────────────────────────────────────────────────────
// Endpoint: Kelas, Siswa, Bacaan
// ─────────────────────────────────────────────────────────────

/**
 * Daftar kelas milik guru (GET /classes).
 *
 * Dibungkus `cache()` React: dalam satu render, halaman memanggil ini langsung
 * **dan** lewat `listStudents`/`listAllAssessments`. Tanpa pembungkusan ini
 * `/classes` terukur diminta tiga kali, masing-masing satu putaran ~1,3 detik.
 */
export const listClasses = cache(async (token?: string | null): Promise<ClassRoom[]> => {
  const raws = await request<RawClass[]>("/classes", { token });
  return raws.map((c) => ({
    id: c.id,
    name: c.name,
    grade: asGrade(c.grade),
    studentCount: 0,
  }));
});

export async function getClass(classId: string, token?: string | null): Promise<ClassRoom | null> {
  try {
    const c = await request<RawClass>(`/classes/${classId}`, { token });
    return { id: c.id, name: c.name, grade: asGrade(c.grade), studentCount: 0 };
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  }
}

/** Buat kelas baru (POST /classes). Pemilik (teacher_id) ditentukan backend dari token. */
export async function createClass(
  input: { name: string; grade: 1 | 2 | 3 },
  token?: string | null
): Promise<ClassRoom> {
  const raw = await request<RawClass>("/classes", {
    method: "POST",
    body: { name: input.name, grade: input.grade },
    token,
  });
  return { id: raw.id, name: raw.name, grade: asGrade(raw.grade), studentCount: 0 };
}

/**
 * Daftar siswa beserta label kelasnya.
 *
 * Nama kelas diambil lewat `listClasses()` (bukan permintaan `/classes` sendiri)
 * supaya cache React membagikannya dengan pemanggil yang juga butuh daftar kelas —
 * halaman siswa membutuhkannya untuk dialog "Tambah Siswa".
 */
export const listStudents = cache(async (token?: string | null): Promise<Student[]> => {
  const [students, classes] = await Promise.all([
    request<RawStudent[]>("/students", { token }),
    listClasses(token),
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
});

/**
 * Tambah siswa ke sebuah kelas (POST /students).
 *
 * Backend menyimpan `grade` per siswa, tetapi selalu sama dengan tingkat kelasnya
 * (lihat konvensi seed). Karena itu `grade` diturunkan dari kelas yang dipilih,
 * bukan ditanyakan lagi ke guru. `classLabel` ikut diminta agar pemanggil tidak
 * perlu satu permintaan tambahan hanya untuk mengisi label kelas.
 */
export async function createStudent(
  input: { name: string; grade: 1 | 2 | 3; classId: string; classLabel: string },
  token?: string | null
): Promise<Student> {
  const raw = await request<RawStudent>("/students", {
    method: "POST",
    body: { name: input.name, grade: input.grade, class_id: input.classId },
    token,
  });
  return {
    id: raw.id,
    name: raw.name,
    grade: asGrade(raw.grade),
    classId: raw.class_id,
    classLabel: input.classLabel,
    assessmentCount: 0,
  };
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

/**
 * Katalog bacaan (GET /readings) — hanya 9 bacaan, isinya sama untuk semua guru.
 *
 * Dua lapis cache, keduanya disengaja:
 * - `cache()` React membagikan hasilnya **dalam satu render**. `getAssessment`,
 *   `listStudentAssessments`, dan `listAllAssessments` semuanya memakainya untuk
 *   mencari judul/level bacaan; dulu masing-masing memanggil `/readings/{id}`
 *   setelah permintaan induknya selesai, menambah satu putaran ~1,3 detik.
 * - `revalidate` menyimpannya **antar-permintaan**. Aman karena `list_readings()`
 *   di `backend/repository.py` tidak menerima `teacher_id` — tidak ada data milik
 *   akun tertentu yang bisa bocor. Jangan tiru pola ini untuk endpoint guru.
 */
export const listReadings = cache(async (token?: string | null): Promise<ReadingText[]> => {
  const raws = await request<RawReading[]>("/readings", { token, revalidate: 300 });
  return raws.map(mapReading);
});

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
  filename = "rekaman.webm",
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

/**
 * Ambil detail asesmen + judul/level bacaan.
 *
 * Katalog bacaan diminta **bersamaan** dengan asesmennya lalu dicari di memori.
 * Dulu `/readings/{reading_id}` baru diminta setelah asesmennya tiba, sehingga
 * halaman hasil menunggu dua putaran (~2,6 detik) hanya untuk satu judul.
 * Katalognya hanya 9 bacaan, jadi menukar satu putaran dengan sedikit byte ini
 * sangat menguntungkan. Kegagalan katalog tidak menjatuhkan halaman — judul dan
 * level menjadi kosong, persis seperti perilaku sebelumnya.
 */
export async function getAssessment(
  assessmentId: string,
  token?: string | null
): Promise<AssessmentResult | null> {
  let raw: RawAssessment;
  let readings: ReadingText[] = [];
  try {
    [raw, readings] = await Promise.all([
      request<RawAssessment>(`/assessments/${assessmentId}`, { token }),
      listReadings(token).catch(() => [] as ReadingText[]),
    ]);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  }
  const reading = readings.find((r) => r.id === raw.reading_id) ?? null;
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
  } catch (e) {
    if (e instanceof ApiError && (e.status === 404 || e.status === 502)) return null;
    return null;
  }
}

/**
 * Riwayat asesmen COMPLETED untuk satu siswa (urut lama → baru).
 *
 * `/assessments?student_id=…` dan katalog bacaan dijalankan **bersamaan**; dulu
 * katalognya menunggu daftar asesmen selesai (2 putaran → 1).
 */
export async function listStudentAssessments(
  studentId: string,
  token?: string | null
): Promise<AssessmentResult[]> {
  const [raws, readings] = await Promise.all([
    request<RawAssessment[]>(`/assessments?student_id=${encodeURIComponent(studentId)}`, {
      token,
    }),
    listReadings(token).catch(() => [] as ReadingText[]),
  ]);
  const completed = raws.filter((a) => a.session_state === "COMPLETED");
  const readingMap = new Map(readings.map((r) => [r.id, r]));
  return completed
    .map((a) => {
      const r = readingMap.get(a.reading_id);
      return mapAssessment(a, r?.title ?? "", r?.level ?? 1);
    })
    .sort((a, b) => a.date.localeCompare(b.date));
}

/**
 * Riwayat semua asesmen COMPLETED (untuk halaman Asesmen).
 *
 * Ketiga permintaan dijalankan **bersamaan**. Dulu `/assessments` menunggu sendiri,
 * baru katalog bacaan dan daftar siswa (yang di dalamnya masih meminta `/students`
 * dan `/classes`) — dua putaran menjadi satu.
 *
 * Dibungkus `cache()` karena halaman yang sama sering memanggilnya bersama
 * `listStudents`/`listClasses`; tanpa itu `/classes` terukur diminta tiga kali dan
 * `/students` dua kali dalam satu render.
 */
export const listAllAssessments = cache(async (
  token?: string | null
): Promise<AssessmentResult[]> => {
  const [raws, readings, students] = await Promise.all([
    request<RawAssessment[]>("/assessments", { token }),
    listReadings(token).catch(() => [] as ReadingText[]),
    listStudents(token).catch(() => [] as Student[]),
  ]);
  const completed = raws.filter((a) => a.session_state === "COMPLETED");
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
});

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
