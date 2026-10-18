# integration_6.md — Penutup Celah Runtime FE + Hardening Skema + Deploy Vercel

> **Status:** ✅ DIEKSEKUSI — A/B/C/E ✅; **D (deploy Vercel) ✅ SELESAI & terverifikasi end-to-end
> (smoke lintas-deploy 14/14)**; G dilewati. Lihat **§10 Hasil eksekusi**.
> **Prasyarat:** `integration_1.md` … `integration_5.md` sudah dieksekusi.
> **Sumber masalah:** audit pasca-`#5` (jawaban atas "apa lagi yang harus diperhatikan?" dan
> "seberapa match FE↔BE?"). Semua temuan **diverifikasi terhadap kode aktual**, bukan asumsi.
>
> **Prinsip yang dipegang (tak berubah):**
> - Supabase schema = sumber kanonis. `reading_framework/` = vendored, **tanpa modifikasi**.
> - `null` ≠ `0`. Frontend hanya presentasi; keputusan/threshold hanya di backend.
> - Aturan lintas-sisi ditegakkan saat **runtime**, bukan hanya test.
> - **DB ikut menjaga invarian** (defense in depth), bukan hanya kode Python.

---

## 0. Ringkasan cakupan

| Asal | Item | Fase | Severity |
|---|---|---|---|
| audit #5 | Migrasi staging #5 belum di-apply (5 item MISSING; 2 test live gagal) | **F** | 🔴 |
| audit #5 | FE tidak tahu batas **durasi** audio → 422 terlambat, UX buruk | **A** | 🔴 |
| audit #5 | `422` durasi tidak ditangani khusus di halaman processing | **A** | 🟡 |
| audit #5 | `GET /config/audio` **tanpa konsumen** → anti-drift hanya test-time | **B** | 🟡 |
| audit #5 | `getThresholds()` runtime hanya di 1 komponen; `THRESHOLDS` statis dipakai di tempat lain | **B** | 🟡 |
| audit skema | Nilai penilaian tanpa CHECK range (`accuracy` bisa >100/negatif) | **C** | 🟡 |
| audit skema | JSONB tanpa validasi tipe (`framework_result`, `rules_fired`, `review_reasons`) | **C** | 🟡 |
| audit skema | `word_scores.position` tanpa CHECK `>= 0` & `confidence` tanpa range | **C** | 🟡 |
| audit skema | `audio_purge_log` tanpa index `assessment_id` | **C** | 🟢 |
| audit skema | FK `assessments.reading_id` tanpa kebijakan `on delete` eksplisit | **C** | 🟢 |
| audit skema | `completed_at` bisa < `created_at` | **C** | 🟢 |
| audit #5 | Deploy Vercel + backend belum divalidasi (butuh kredensial) | **D** | 🟡 |
| audit #5 | `X-Request-ID` klien tak divalidasi (potensi injeksi log) | **E** | 🟢 |
| audit #5 | Belum ada VCS (semua uncommitted) | **G** | 🟡 |

> **Tujuan akhir:** menutup **semua 🔴/🟡** di atas + opsional 🟢, lalu seluruh test (termasuk
> live) hijau, dan deploy staging (Vercel + backend) berjalan.

---

## 1. Temuan terverifikasi (bukti kode)

### 1.1 🔴 FE tidak tahu batas durasi (temuan utama)

`frontend/app/assess/record/page.tsx`:
```ts
import { blobToWav, MAX_AUDIO_BYTES } from "@/lib/audio-wav";   // ← hanya ukuran
// ...
function goReview() {
  if (!blob || !audioUrl) return;
  if (blob.size > MAX_AUDIO_BYTES) { setSizeError(true); return; }  // ← hanya size
  // TIDAK ada cek durasi.
}
```
Backend **sudah** menolak durasi > `MAX_AUDIO_DURATION_SEC` (default 300 s) dengan **422**
(`backend/api/assessments.py`, via `validate_audio_duration`). Konsekuensi: siswa merekam >5 menit,
lolos di klien, menunggu upload besar, baru ditolak → **boros bandwidth + UX buruk**.

### 1.2 🟡 422 durasi tidak ditangani khusus

`frontend/app/assess/processing/page.tsx` (baris ~79–91):
```ts
if (e instanceof ApiError && e.status === 503) { ... }
else if (e instanceof ApiError && (e.status === 413 || e.status === 415)) { ... }  // ← 413/415 saja
else if (e instanceof ApiError) { setErrorMsg(e.detail); }   // 422 jatuh ke sini (generik)
```
422 tidak punya alur "rekam ulang" yang eksplisit (meski pesan backend sudah jelas).

### 1.3 🟡 `/config/audio` tanpa konsumen runtime

`grep config/audio → frontend` = **kosong**. Endpoint ada (`backend/api/config.py:36`) dan
diuji, tetapi **tidak ada kode FE yang memanggilnya** → anti-drift audio & durasi hanya
ditegakkan **saat test**, bukan saat aplikasi berjalan. Ini melanggar prinsip §0.

### 1.4 🟡 `getThresholds()` runtime tidak konsisten

- `frontend/components/teacher/StatusExplainer.tsx` memanggil `getThresholds()` (server, benar).
- `frontend/lib/tokens.ts` masih mengekspor `THRESHOLDS = { accuracy: {low:90,high:95}, comprehension:80 }`
  dan dipakai lintas komponen sebagai **nilai statis**. Nilainya **kebetulan** sama dengan backend
  (`ACCURACY_LOW=90`, `ACCURACY_HIGH=95`, `COMPREHENSION_MIN=80`) dan dijaga test
  `test_frontend_thresholds_match_backend`, **tapi** bukan berarti runtime memakai backend.

### 1.5 🟡 Skema: nilai penilaian tanpa CHECK range

`backend/supabase_schema.sql` — kolom numerik tanpa constraint:
```
accuracy      numeric(5,2)   -- bisa 500.00 / negatif
wcpm          numeric(6,2)   -- bisa negatif
retrieve/interpret/reflect numeric(5,2)  -- bisa >100 / negatif
confidence    numeric(4,3)   -- bisa >1
```
Tidak ada `check (accuracy between 0 and 100)` dsb.

### 1.6 🟡 Skema: JSONB tanpa validasi tipe

`framework_result jsonb`, `rules_fired jsonb default '[]'`, `review_reasons jsonb default '[]'`,
`proper_nouns jsonb`, `options jsonb` — semua bebas (bisa skalar/null, bukan objek/array).
Tidak ada `check (jsonb_typeof(...)='array')` atau versioning.

### 1.7 🟢 Skema: detail kecil

- `word_scores.position int not null` — tanpa `check (position >= 0)` (hanya unique composite).
- `reading_questions.position` tanpa unique `(reading_id, position)`.
- `audio_purge_log` tanpa index pada `assessment_id`.
- `assessments.reading_id` FK tanpa `on delete` eksplisit (default `no action`).
- `completed_at` tanpa `check (completed_at >= created_at)`.

### 1.8 🟡 Deploy Vercel belum divalidasi

Fase D `#5` hanya menyiapkan env/checklist. Belum ada build/uji nyata karena tanpa akun Vercel
& server backend. **Butuh kredensial dari pengguna** (lihat §6).

### 1.9 🟡 Belum ada VCS

Bukan git repo → 16 file diubah + 9 file baru (#5) uncommitted. Tidak bisa diff/rollback.

---

## 2. Keputusan yang dibutuhkan (D1–D4)

> Sama seperti `#5`, keputusan di bawah berdampak besar. Saya mengusulkan **default**, silakan
> konfirmasi/ubah.

- **D1 — Enforcement batas durasi di FE.** Pilih:
  (a) FE tarik `GET /config/audio` **sekali** (server-side, diliter ke komponen) dan pakai
      `max_audio_duration_sec` untuk (i) menampilkan sisa waktu & (ii) auto-stop/peringatan saat
      durasi hampir habis. **[REKOMENDASI]**
  (b) Hanya **cek durasi** di `goReview()` terhadap konstanta `MAX_AUDIO_DURATION_SEC` di
      `audio-wav.ts` (cermin backend, dijaga test). Lebih murah, tapi tetap duplikasi nilai.
  (c) Kombinasi: (a) sebagai sumber runtime + fallback ke konstanta (b) bila fetch gagal.

- **D2 — Perlakuan threshold statis (`tokens.ts`).** Pilih:
  (a) Pertahankan `THRESHOLDS` sebagai **fallback server-rendered** (dokumentasi jelas: sumber
      runtime = backend) — nilai boleh sama, test anti-drift tetap ada. **[REKOMENDASI]**
  (b) Jadikan `tokens.ts` hanya tipe/warna; **hapus** angka threshold dari sana; semua lewat
      `getThresholds()`. Lebih murni, tapi lebih banyak perubahan konsumen.

- **D3 — Hardening skema: seberapa ketat.** Pilih:
  (a) **Semua** CHECK ℹ️ §1.5–1.7 (nilai range + JSONB tipe + posisi/confidence + completed_at).
      **[REKOMENDASI]** (defense in depth; sesuai prinsip "Supabase = sumber kanonis").
  (b) Hanya CHECK nilai penilaian (§1.5) — paling berdampak, risiko migrasi terkecil.
  (c) Tidak ada hardening (hanya tutup FE). Tidak disarankan.

- **D4 — VCS.** Pilih:
  (a) `git init` + commit awal sebelum eksekusi (agar tiap fase bisa di-diff/rollback).
      **[REKOMENDASI]**
  (b) Tetap tanpa VCS (manual backup). Tidak disarankan.

---

## 3. Matriks celah → target

| # | Celah | Severity | Target | Fase | Bukti uji |
|---|---|---|---|---|---|
| 1 | Migrasi staging #5 belum apply | 🔴 | ter-apply | F | `verify_supabase` 17/17; live 18 passed |
| 2 | FE tak tahu durasi | 🔴 | FE tahu & menegakkan | A | test/`curl` runtime; `tsc`+`build` |
| 3 | 422 durasi tak ditangani khusus | 🟡 | alur "rekam ulang" | A | test komponen/manual |
| 4 | `/config/audio` tanpa konsumen | 🟡 | dipakai runtime | A/B | grep konsumen + test drift |
| 5 | Threshold statis | 🟡 | status terdefinisi (D2) | B | test anti-drift + dok |
| 6 | CHECK nilai range | 🟡 | constraint ada | C | insert invalid → error |
| 7 | JSONB tipe | 🟡 | `jsonb_typeof` check | C | insert skalar → error |
| 8 | posisi/confidence/completed_at | 🟢 | constraint ada | C | insert invalid → error |
| 9 | index purge | 🟢 | index ada | C | `verify_supabase` |
| 10 | Deploy Vercel | 🟡 | staging jalan | D | smoke test lintas-deploy |
| 11 | `X-Request-ID` klien | 🟢 | sanitasi/truncate | E | unit test |
| 12 | VCS | 🟡 | git init+commit | G | `git status` bersih |

---

## 4. Fase eksekusi

### Fase A — Tutup celah runtime FE (durasi + konsumsi `/config/audio`) 🔴

**A.1 — Sumber konstanta runtime (D1).**
Tambahkan `getAudioConfig()` di `frontend/lib/api.ts`:
```ts
export interface AudioConfig {
  targetSampleRate: number;
  maxAudioBytes: number;
  maxAudioDurationSec: number;
}

export async function getAudioConfig(token?: string | null): Promise<AudioConfig | null> {
  try {
    const raw = await request<{
      target_sample_rate: number;
      max_audio_bytes: number;
      max_audio_duration_sec: number;
    }>("/config/audio", { token });
    return {
      targetSampleRate: raw.target_sample_rate,
      maxAudioBytes: raw.max_audio_bytes,
      maxAudioDurationSec: raw.max_audio_duration_sec,
    };
  } catch {
    return null; // pemanggil memakai fallback konstanta (null-safe)
  }
}
```

**A.2 — Liter konfigurasi ke klien (server → client).**
Halaman/komponen yang butuh adalah client component (`record`). Ambil di server lalu teruskan
sebagai prop, agar tidak fetch dari browser berkali-kali:
- `frontend/app/assess/record/page.tsx` saat ini client component. Buat wrapper server
  (`page.tsx` server) yang memanggil `getAudioConfig(getServerToken())` lalu merender komponen
  klien `RecordClient` dengan `maxDurationSec` sebagai prop. **(Perubahan struktur — hati-hati
  `useSearchParams`/Suspense; pertahankan fallback `RecordFallback`.)**
- Alternatif lebih minimal: `record/page.tsx` tetap client; ambil config via `fetch("/api/proxy/config/audio")`
  sekali di `useEffect`. **Pilih salah satu** — rekomendasi: prop server (tanpa round-trip browser).

**A.3 — Tegakkan durasi di `record` (`goReview()`).**
```ts
// Integrasi #6 (D1): cegah 422 — batas durasi, bukan hanya ukuran.
const maxSec = maxDurationSec ?? MAX_AUDIO_DURATION_SEC; // fallback konstanta cermin backend
if (duration > maxSec) { setDurationError(true); return; }
```
Tambah state `durationError` + blok `ErrorState` **"Rekaman terlalu panjang"** dengan pesan
menyebut **durasi** (bukan 10 MB), dan tombol **rekam ulang**.

**A.4 — Fallback konstanta cermin backend (D1c).**
`frontend/lib/audio-wav.ts`:
```ts
/** Batas durasi upload (detik) — cermin `MAX_AUDIO_DURATION_SEC` backend (default 300). */
export const MAX_AUDIO_DURATION_SEC = 300;
```
> Gunakan hanya sebagai **fallback** bila `/config/audio` gagal. Nilai dijaga test anti-drift (§F).

**A.5 — Timer/peringatan mendekati batas (opsional, dari D1a).**
Di `record`, tampilkan sisa waktu bila `duration > maxSec - 30` (mis. "Sisa 20 detik").
Bila memilih auto-stop, hentikan di `maxSec` — **tapi default: peringatan, bukan auto-stop**
(beri keputusan guru/siswa). Bisa ditunda bila ingin minimal.

**A.6 — Tangani 422 di `processing`.**
`frontend/app/assess/processing/page.tsx`:
```ts
} else if (e instanceof ApiError && e.status === 422) {
  setErrorMsg(
    "Rekaman terlalu panjang untuk diproses. Coba rekam ulang dengan durasi lebih singkat ya."
  );
}
```
(Letakkan **sebelum** cabang generik `else if (e instanceof ApiError)`.)

**Acceptance Fase A:** `tsc` + `lint` + `build` bersih; rekam >5 menit ditolak **di klien**
(tanpa upload); pesan menyebut durasi; `/config/audio` **dikonsumsi** kode FE (bukan hanya test).

---

### Fase B — Threshold & anti-drift runtime 🟡

**B.1 — Tentukan status `tokens.ts` (D2).** Bila **(a)**: tambahkan komentar tegas di
`tokens.ts` — "nilai ini **fallback** untuk render server; sumber runtime = `GET /config/thresholds`".
Bila **(b)**: hapus angka dari `tokens.ts` & ganti semua konsumen `THRESHOLDS.*` ke prop `thresholds`
dari server.

**B.2 — Perluas anti-drift ke audio config.** `backend/tests/test_audio_drift.py` sudah ada;
tambahkan assertion bahwa **FE memiliki konsumen** `/config/audio` (mis. cek `frontend/lib/api.ts`
memuat `getAudioConfig`) — mencegah regresi "endpoint tanpa konsumen" di masa depan.
```python
def test_frontend_consumes_audio_config_endpoint():
    api_ts = (Path(__file__).resolve().parents[2] / "frontend" / "lib" / "api.ts")
    if not api_ts.exists():
        pytest.skip("frontend/lib/api.ts tidak tersedia")
    assert "/config/audio" in api_ts.read_text(), "FE tidak mengonsumsi /config/audio"
```

**B.3 — (Bila D2b) test anti-drift tetap ada** untuk `tokens.ts` ↔ `adaptive_rules.py`
(sudah ada di `test_api.py`), pastikan tidak terhapus.

**Acceptance Fase B:** status threshold terdefinisi; test anti-drift hijau; grep konsumen
`/config/audio` tidak kosong.

---

### Fase C — Hardening skema (defense in depth) 🟡 (D3)

> **PENTING — urutan aman untuk DB yang sudah berisi data:** (1) tambahkan constraint sebagai
> **`NOT VALID`** dulu (tak memeriksa baris lama), (2) bersihkan/perbaiki data lama, (3)
> `validate constraint`. Bila data sudah bersih, boleh langsung `add constraint`.

**C.1 — CHECK nilai penilaian.**
```sql
alter table assessments
  add constraint ck_assess_wcpm        check (wcpm is null or wcpm >= 0),
  add constraint ck_assess_accuracy    check (accuracy is null or accuracy between 0 and 100),
  add constraint ck_assess_retrieve    check (retrieve is null or retrieve between 0 and 100),
  add constraint ck_assess_interpret   check (interpret is null or interpret between 0 and 100),
  add constraint ck_assess_reflect     check (reflect is null or reflect between 0 and 100),
  add constraint ck_assess_time        check (completed_at is null or completed_at >= created_at),
  add constraint ck_assess_consec_drops check (consecutive_drops is null or consecutive_drops >= 0);

alter table word_scores
  add constraint ck_ws_position check (position >= 0),
  add constraint ck_ws_conf     check (confidence is null or confidence between 0 and 1);
```
> **`null` tetap diizinkan** (konsisten `null ≠ 0`).

**C.2 — CHECK tipe JSONB.**
```sql
alter table assessments
  add constraint ck_assess_rules_fired  check (jsonb_typeof(rules_fired) = 'array'),
  add constraint ck_assess_framework    check (framework_result is null or jsonb_typeof(framework_result) = 'object');

alter table word_scores
  add constraint ck_ws_review check (jsonb_typeof(review_reasons) = 'array');

alter table reading_texts
  add constraint ck_rt_proper_nouns check (jsonb_typeof(proper_nouns) = 'array');

alter table reading_questions
  add constraint ck_rq_options check (jsonb_typeof(options) = 'object' or jsonb_typeof(options) = 'array');
```
> ⚠️ Cek data lama: `framework_result` yang **bukan** object akan gagal. Verifikasi dulu.

**C.3 — Index & konsistensi FK.**
```sql
create index if not exists idx_audio_purge_assessment on audio_purge_log(assessment_id);

-- FK reading_id: tetapkan kebijakan eksplisit (RESTRICT = cegah hapus teks yang punya asesmen).
alter table assessments drop constraint if exists assessments_reading_id_fkey;
alter table assessments add constraint assessments_reading_id_fkey
    foreign key (reading_id) references reading_texts(id) on delete restrict;
```

**C.4 — (Opsional) unique `reading_questions(reading_id, position)`.**
```sql
create unique index if not exists uq_rq_reading_position
    on reading_questions(reading_id, position);
```
> Cek duplikat posisi sebelum menambah (bisa ada data seed dengan posisi sama).

**C.5 — Migrasi delta.** Tulis `backend/migrations/integration_6.sql` (idempotent, pola #5) +
perbarui `backend/supabase_schema.sql` (sumber kanonis) agar konsisten.

**C.6 — Verifikasi.** Perluas `backend/scripts/verify_supabase.py`: cek keberadaan constraint
(mis. lewat `information_schema.table_constraints`) sebagai item verifikasi baru.

**Acceptance Fase C:** `verify_supabase` bertambah hijau; insert nilai invalid (mis. `accuracy=200`)
→ **error** (uji di staging via service-role); skema & migrasi sinkron.

---

### Fase D — Deploy staging Vercel + backend 🟡 (butuh kredensial)

**D.1 — Prasyarat dari pengguna (lihat §6).** Backend harus **publik + HTTPS**. FE di Vercel.
**D.2 — Env Vercel** (Project → Settings → Environment Variables):
- `API_BASE_URL` = `https://<backend-host>` (server-to-server proxy).
- `SESSION_COOKIE_SECURE` = `true`.
- (Opsional) `NEXT_PUBLIC_API_BASE_URL` — **tidak perlu** (browser lewat `/api/proxy`).
**D.3 — Env backend** (server sendiri):
- `ENV=production`, `CORS_ORIGINS=https://<vercel-app>.vercel.app` (eksplisit, tanpa `*`),
  `SESSION_COOKIE_SECURE=true`, `AUTH_DISABLED=false`,
  `MAX_AUDIO_DURATION_SEC=300`, `ASR_TIMEOUT_SEC=120`, `AUDIO_RETENTION_MONTHS=12`, `LOG_LEVEL=INFO`.
- Jalankan `uvicorn --workers 1` (rate-limit in-memory) di belakang Caddy/Nginx TLS.
- Model Whisper: `WHISPER_MODEL=base` (naik ke `small` bila perlu).
**D.4 — Smoke test lintas-deploy** (browser → Vercel → backend):
1. `GET https://<vercel>/login` OK; login → cookie httpOnly ter-set.
2. `GET https://<vercel>/api/proxy/health` → 200 (proxy→backend).
3. Alur asesmen: buat → rekam (uji batas durasi) → upload → hasil.
4. Cek `X-Request-ID` konsisten di log backend.
5. `curl -I` pastikan cookie `Secure` + backend HTTPS.
**D.5 — Jadwalkan `prune_audio`** (cron server / Supabase scheduled function), bulanan.

**Acceptance Fase D:** alur asesmen end-to-end jalan di staging Vercel↔backend; cookie `Secure`;
CORS tak menolak origin Vercel; tidak ada 401 tak terduga (validasi Fase 0 di produksi).

---

### Fase D (REVISI) — 🔴 Blocker 4.5 MB & Opsi A: presigned upload

> **Konteks (terverifikasi):** Fase 0 mengarahkan **semua** panggilan browser ke proxy same-origin
> `/api/proxy` (route handler Next di Vercel). Vercel Functions membatasi **request body maks 4.5 MB**
> (semua plan; `413 FUNCTION_PAYLOAD_TOO_LARGE`). Upload audio ≤10 MB (WAV 16 kHz ≈ 32 KB/detik →
> 5 menit ≈ 9.6 MB) akan **gagal di Vercel** sebelum mencapai backend. Lokal tak terpengaruh.
>
> **Keputusan:** **Opsi A — presigned upload ke Supabase Storage** (bypass Vercel). Multipart tetap
> dipertahankan sebagai **fallback** (mode demo/in-memory/uji lokal).
> **Backend staging:** **ngrok** (`ngrok http 8000`). **Deploy Vercel:** oleh pengguna sendiri.

**Alur baru:**
```
1. browser → /api/proxy/assessments/{id}/audio/upload-url   (JSON kecil)
              BE cek kepemilikan (guru lain → 404) → create_signed_upload_url(path)
   ← { path, signed_url, token }
2. browser → PUT <signed_url>  (blob ≤10 MB)   [LANGSUNG ke Supabase, bypass Vercel] ✅
3. browser → /api/proxy/assessments/{id}/audio  (JSON { audio_path })
              BE unduh objek dari Storage → validasi (magic bytes + durasi) → transkripsi → skor
```
> **Fallback:** bila `create_signed_upload_url` tak tersedia (in-memory/demo/Supabase off) →
> `upload-url` mengembalikan `{ "mode": "multipart" }`; FE mengirim multipart ke `/audio` seperti biasa.

**D-R.1 — Backend: `services/audio_storage.py`**
- `create_signed_upload_url(client, path) -> dict | None` → buka `client.storage.from_(BUCKET)
  .create_signed_upload_url(path)`; kembalikan `{path, signed_url, token}` (tangani dict/objek &
  varian `signed_url`/`signedUrl`). Gagal → `None`.
- `download(client, path) -> bytes | None` → `client.storage.from_(BUCKET).download(path)`.

**D-R.2 — Backend: `api/assessments.py`**
- **Baru** `POST /{assessment_id}/audio/upload-url`:
  - `_owned_assessment` (guru lain → 404, konsisten); `client = teacher_supabase_client(_bearer(...))`.
  - `client is None` → `{"mode": "multipart"}` (fallback).
  - path = `{teacher}/{assessment_id}/normalized.wav`; signed → `{path, signed_url, token}`;
    gagal → `502`.
- **`POST /{assessment_id}/audio`**: terima **dua bentuk**:
  - `multipart/form-data` (lama) — `audio: UploadFile`.
  - `application/json { audio_path }` — unduh via `audio_storage.download`; **validasi path** milik
    guru ini (prefix `{teacher}/{assessment_id}/`) untuk cegah path traversal/IDOR.
  - Setelah byte diperoleh → pipeline yang sama (magic bytes → temp → transkripsi → durasi → skor).

**D-R.3 — Frontend: `lib/api.ts`**
- `getAudioUploadUrl(assessmentId, token)` → `POST .../audio/upload-url`.
- `uploadAssessmentAudio(...)`: bila `mode==="signed"` → `fetch(signed_url, {method:"PUT", body:blob,
  headers:{ "x-upsert":"false", "content-type": blob.type }})` → lalu `POST /audio {audio_path}`.
  Bila `mode==="multipart"` atau PUT gagal → fallback multipart (perilaku lama).

**D-R.4 — Frontend: `app/api/proxy/[...path]/route.ts`**
- `export const runtime = "nodejs";` (streaming `duplex`).
- `export const maxDuration = 300;` (Whisper CPU; Hobby maks 300s).
- Tambah header **`ngrok-skip-browser-warning: "true"`** ke request backend (hindari halaman
  peringatan ngrok free yang mengembalikan HTML, bukan JSON).

**D-R.5 — Env & deploy**
- Backend (ngrok): `ENV=production` **hanya bila TLS+cookie secure**; untuk uji ngrok cepat boleh
  `ENV=staging` (hindari fail-fast `SESSION_COOKIE_SECURE`). Set
  `CORS_ORIGINS=https://<vercel-app>.vercel.app`, `SUPABASE_URL/KEY/SERVICE_ROLE_KEY`,
  `MAX_AUDIO_DURATION_SEC=300`, `ASR_TIMEOUT_SEC=300`, `LOG_LEVEL=INFO`.
- Vercel: `API_BASE_URL=https://<xxx>.ngrok-free.app`, `SESSION_COOKIE_SECURE=true`.
- Supabase Storage: pastikan **CORS** mengizinkan origin Vercel untuk PUT signed upload (uji D-R.6).

**D-R.6 — Smoke test lintas-deploy (revisi)**
1. `GET https://<vercel>/api/proxy/health` → 200 (proxy→ngrok→BE).
2. Login → cookie httpOnly ter-set (`Secure`).
3. Rekam **>4.5 MB** (mis. ~3 menit) → unggah berhasil via **signed URL langsung ke Supabase**
   (bukti bypass Vercel). Cek objek muncul di bucket.
4. `POST /audio {audio_path}` → pipeline jalan → hasil tampil.
5. Uji batas durasi (rekam >5 menit) → ditolak **di klien**.
6. `X-Request-ID` konsisten di log backend.

**Gotcha yang WAJIB ditangani:**
1. **ngrok free interstitial** → header `ngrok-skip-browser-warning` (D-R.4). Tanpa ini,
   server-to-server dari Vercel menerima HTML → error JSON parse.
2. **CORS Supabase Storage** untuk PUT signed upload dari origin Vercel — uji dulu; bila ditolak,
   atur CORS bucket/`allowedOrigins`.
3. **Proxy timeout** → `maxDuration=300`.
4. **`SESSION_COOKIE_SECURE=true`** di Vercel; backend `ENV=production` fail-fast bila salah.
5. **Path traversal** pada `audio_path` → validasi prefix `{teacher}/{assessment_id}/`.

**Acceptance Fase D (revisi):** upload >4.5 MB **berhasil** end-to-end lewat Vercel (via signed URL),
fallback multipart tetap jalan untuk data kecil/demo; tidak ada 413 Vercel; cookie `Secure`.

---


### Fase E — Hardening kecil 🟢

**E.1 — Sanitasi `X-Request-ID`.** Di `backend/main.py` middleware, potong & filter karakter:
```python
rid = (request.headers.get("X-Request-ID") or uuid.uuid4().hex)[:64]
rid = "".join(ch for ch in rid if ch.isalnum() or ch in "-_") or uuid.uuid4().hex
```
Tambah unit test (header aneh → di-sanitasi).

---

### Fase F — Verifikasi menyeluruh

| Suite | Target |
|---|---|
| `verify_supabase` | **17/17 OK** (+ constraint #6) |
| `pytest tests/test_supabase_live.py` | **18 passed** (setelah migrasi #5+#6 di-apply) |
| Backend non-live | **≥ 257 passed, exit 0** (+test E.1) |
| `pytest tests/reading_framework` | exit 0 (126/5) |
| `npx tsc` / `next lint` / `npm run build` | bersih / sukses |
| `seed.validate` / `check_framework_drift.sh` | OK / OK |
| Smoke test staging (D.4) | lulus |

---

### Fase G — VCS & kebersihan 🟡 (D4)

**G.1** `git init` (bila disetujui) → `.gitignore` pastikan `.env*` (kecuali `.example`) & `node_modules` & `__pycache__` terabaikan → commit awal.
**G.2** Commit per-fase agar bisa di-diff/rollback.

---

## 5. Non-goal (di luar cakupan)

- Migrasi ke server produksi penuh (fokus tetap **staging**).
- Redis multi-instance (rate-limit tetap in-memory + `--workers 1`).
- Menambah jenis kesalahan kata / klasifikasi di luar framework.
- Mengubah `reading_framework/` (vendored) — **tidak akan disentuh**.
- Multi-bahasa / model ASR lain.

---

## 6. Yang saya butuhkan dari Anda (kredensial/config)

> Agar Fase D bisa dieksekusi & divalidasi. **Jangan tulis rahasia di chat** bila tak nyaman —
> cukup konfirmasi bahwa nilainya sudah Anda set / akan Anda set, lalu saya pandu verifikasinya.
>
> **STATUS (terbaru):** migrasi #5 & #6 **sudah di-apply** oleh pengguna di staging —
> terverifikasi `verify_supabase` **18/18 OK** & `test_supabase_live.py` **14/14 passed**.
> Keputusan deploy: **Opsi A (presigned upload)**, **ngrok** untuk backend, **deploy Vercel oleh pengguna**.

**Wajib (untuk validasi deploy):**
1. **URL ngrok** dari `ngrok http 8000` di mesin backend (mis. `https://xxxx.ngrok-free.app`).
   (Authtoken sudah ada di config ngrok pengguna.) → set sebagai `API_BASE_URL` di Vercel.
2. **Origin Vercel final** (mis. `https://bacalaras-xxx.vercel.app`) → untuk `CORS_ORIGINS` backend.
3. **Supabase**: sudah beres (`.env.test` + migrasi ter-apply). Cek **CORS Storage** untuk PUT
   signed upload dari origin Vercel (lihat D-R.6 gotcha #2).
4. **Vercel**: pengguna login & deploy; set `API_BASE_URL` + `SESSION_COOKIE_SECURE=true`.

**Tidak diperlukan lagi:**
- ~~Konfirmasi jalankan SQL migrasi~~ → **sudah dilakukan** ✅.
- ~~Host backend publik permanen~~ → sementara pakai **ngrok**.

**Opsional:**
5. Nama domain final (bila sudah ada) untuk CORS & cookie.
6. Bila ingin **tanpa fallback multipart** sepenuhnya (keputusan: tetap pakai fallback).

> **Keamanan:** saya **tidak** memerlukan service-role key produksi di chat. Cukup staging.
> Bila Anda memilih berbagi, gunakan mekanisme aman (bukan chat) dan ingat: service-role
> **melewati RLS**.

---

## 7. Urutan eksekusi & ketergantungan

```
D4 (VCS, opsional) → A (celah FE) → B (threshold) → C (skema) → F (verifikasi) → D (deploy) → E (kecil) → G (commit)
                                    └── migrasi #5 + #6 di-apply di staging sebelum F/D
```

- **C** memerlukan data staging bersih (backfill/cek) — koordinasi dengan Anda (§6.4).
- **D** memerlukan kredensial (§6.1–6.3).
- **E** kecil, bisa kapan saja.
- **F** dijalankan **setelah** migrasi di staging.

---

## 8. Risiko

| Risiko | Dampak | Mitigasi |
|---|---|---|
| Migrasi skema di DB berisi data | constraint gagal / data tak valid | `NOT VALID` → bersihkan → `validate`; verifikasi dulu |
| `framework_result` lama bukan object | C.2 gagal | cek data & longgarkan bila perlu |
| Ubah `record/page.tsx` ke server+client | regresi Suspense/`useSearchParams` | pertahankan `RecordFallback`; uji `build` |
| Vercel cookie/CORS salah | 401/CORS di produksi | D.3 eksplisit; smoke test D.4 |
| Tanpa VCS | rollback sulit | D4 `git init` |
| `HF_HOME` build↔runtime beda | model re-download | sudah diset `HF_HOME=/app/models` (#5) |

---

## 9. Status

- **Fase A, B, C, E ✅; Fase D (Opsi A) kode BE+FE+proxy SELESAI & teruji** (backend **424 passed**,
  framework 126/5, **live 20/20**, smoke lintas-deploy **12/12**). Fase G (VCS) **dilewati**
  (keputusan D4: tanpa VCS).
- Keputusan: D1=(c) kombinasi, D2=(a) fallback terdokumentasi, D3=(a) semua CHECK, D4=tidak (tanpa VCS),
  Fase D=Opsi A (presigned) + ngrok + deploy Vercel oleh pengguna.
- **Migrasi #5 & #6 (+ 2 policy fix) sudah di-apply pengguna** → `verify_supabase` **19/19 OK**
  (policy check "aktif"), live **20/20 passed** ✅.
- **Blocker ditemukan & disolusikan:** batas body Vercel 4.5 MB → **Opsi A (presigned upload)**;
  roundtrip signed-upload **terverifikasi** di project staging.
- **4 bug runtime ditemukan saat smoke test lintas-deploy — SEMUA teratasi:**
  - **#1 (SQL, ✅ applied)** login guru **503** — `users` tanpa policy RLS `INSERT` → fix
    `users_self_insert` di skema+migrasi §5. Terverifikasi: `/auth/login` → **200**.
  - **#2 (kode, ✅)** `require_teacher` tanpa JWT guru → 503 → fix (JWT ditempelkan).
  - **#3 (kode, ✅)** `get_repository()` singleton anon **tanpa JWT guru** → RLS blok → 404 →
    fix dependency per-request `get_teacher_repository` + `_apply_teacher_token` (JWT ke postgrest
    **dan** storage).
  - **#4 (SQL, ✅ applied)** signed upload `upsert=true` pada objek yang **sudah ada** → butuh policy
    `UPDATE` `storage.objects` → fix `reading_audio_owner_update` di skema+migrasi §6.
- **Deploy Vercel (Fase D) — ✅ SELESAI & TERVERIFIKASI END-TO-END (lihat §10 "Fase D — Deploy Vercel"):**
  - ✅ Pengguna **mematikan Deployment Protection**; ✅ memperbaiki **versi Next.js yang usang**
    lalu redeploy; ✅ domain stabil **`https://bacalaras-frontend.vercel.app`** (▲ Aliased).
  - ✅ **Env Vercel di-set** (via `vercel env add`, 3 environment): `API_BASE_URL` =
    `https://janene-unhanging-mandatorily.ngrok-free.dev`, `SESSION_COOKIE_SECURE=true`.
  - ✅ **Redeploy** (`vercel --prod`) → `/api/proxy/health` & `/ready` = **200**.
  - ✅ **Smoke test lintas-deploy dari origin Vercel = 14/14 PASS** (login→cookie httpOnly+Secure,
    create assessment via proxy, upload-url signed, PUT langsung ke Supabase, pipeline, **PUT >4.5 MB**,
    rekam ulang/upsert). `X-Request-ID` respons = entri log backend (korelasi ✅).
  - Catatan CORS: proxy bersifat **server-to-server** ⇒ CORS browser backend **opsional**;
    Supabase Storage CORS = `allow-origin: *` (PUT signed upload dari Vercel **aman**).

> **Fase D ✅ SELESAI.** Sisa (operasional, di luar cakupan kode): URL **ngrok free dinamis** —
> bila ngrok restart, update `API_BASE_URL` di Vercel (atau pakai domain statis / backend publik).

---

## 10. Hasil eksekusi

### Fase A — Celah runtime FE (durasi + konsumsi `/config/audio`) ✅
- `frontend/lib/api.ts`: +`getAudioConfig()` (+cache +`resetAudioConfigCache`).
- `frontend/lib/audio-wav.ts`: +`MAX_AUDIO_DURATION_SEC = 300` (fallback cermin backend).
- `frontend/app/assess/record/RecordScreen.tsx` (**baru**, client): prop `maxDurationSec`,
  cek durasi di `goReview()`, state `durationError`, peringatan "Sisa N detik", pesan batas durasi.
- `frontend/app/assess/record/page.tsx`: kini **server component** — fetch `getAudioConfig()` lalu
  liter ke komponen klien (tanpa round-trip browser, token tak ke JS).
- `frontend/app/assess/processing/page.tsx`: +penanganan **422** (audio terlalu panjang).
- **Terbukti end-to-end**: `GET /assess/record` → backend menerima `GET /config/audio → 200`
  (FE benar-benar mengonsumsi saat runtime). `tsc`/`lint`/`build` bersih; `/assess/record` = ƒ Dynamic.

### Fase B — Threshold & anti-drift runtime ✅
- `frontend/lib/tokens.ts`: komentar status tegas (nilai = **fallback**; sumber runtime = backend).
- `backend/tests/test_audio_drift.py`: +3 test (durasi sinkron, konsumsi `/config/audio`,
  `RecordScreen` menegakkan durasi) — **hijau**.

### Fase C — Hardening skema ✅ (kode; perlu apply di staging)
- `backend/supabase_schema.sql`: +blok CHECK (nilai range, JSONB tipe, posisi/confidence,
  completed_at, previous_*), FK `reading_id` RESTRICT, index `audio_purge_log`.
- `backend/migrations/integration_6.sql` (**baru**): delta idempotent pola aman
  `NOT VALID → validate` + query laporan data melanggar.
- `backend/scripts/verify_supabase.py`: +cek `CHECK ck_rt_proper_nouns` (insert invalid
  diharapkan ditolak 23514, non-destruktif).

### Fase E — Sanitasi `X-Request-ID` ✅
- `backend/main.py`: sanitasi header klien (filter alnum/`-_`, max 64; kosong → generate baru).
- `backend/tests/test_api.py`: +2 test (malicious disanitasi, kosong → generate) — **hijau**.

### Fase D — Deploy (Opsi A: kode SELESAI; 1 blocker DB ditemukan)
- `frontend/.env.example`: catatan bahwa env audio **tak perlu** di Vercel (FE baca `/config/audio`).
- **REVISI (Opsi A)**: presigned upload menutup blocker body Vercel 4.5 MB. **Kode BE+FE+proxy selesai:**
  - **BE** `services/audio_storage.py`: +`create_signed_upload_url()` (tahan-versi: coba
    pydantic/shape/dict/None) + `download()`.
  - **BE** `api/assessments.py`: +`POST /{id}/audio/upload-url` (kepemilikan; guru lain→404;
    Storage None→`{"mode":"multipart"}`; gagal→502) + `_validate_audio_path()` (anti IDOR);
    `POST /{id}/audio` kini menerima **JSON `{audio_path}`** ATAU multipart, dan **tidak**
    mengunggah ulang bila objek sudah ada di Storage.
  - **FE** `lib/api.ts`: +`getAudioUploadUrl()`; `uploadAssessmentAudio()` PUT **langsung ke
    Supabase** lalu `POST /audio {audio_path}`, dengan **fallback multipart**.
  - **FE** proxy `app/api/proxy/[...path]/route.ts`: `runtime="nodejs"`, `maxDuration=300`,
    header `ngrok-skip-browser-warning: true`.
- **Terverifikasi**: `create_signed_upload_url` **berfungsi** di staging (live test roundtrip:
  PUT langsung → objek tersimpan). ngrok: `/ready` & `/health` **200** dengan header skip-warning.
- **⚠️ 4 BLOCKER RUNTIME ditemukan saat smoke test lintas-deploy (smoke: 11/12 PASS):**
  - **#1 (SQL)** login guru **selalu 503** — tabel `users` tak punya policy RLS `INSERT`,
    padahal `_sync_public_user` meng-upsert `public.users` saat login (upsert PostgREST =
    `INSERT ... ON CONFLICT`). Tidak tertangkap test lama (live test membuat baris via
    service-role). **Perbaikan**: `users_self_insert` di skema + migrasi §5 + test regresi live
    (`test_teacher_can_upsert_own_profile`). **Perlu di-apply ke staging.**
  - **#2 (kode)** `require_teacher` memakai klien anon tanpa JWT guru → select profil kosong →
    503. **Fix**: tempelkan JWT guru (`client.postgrest.auth`) sebelum select/upsert profil.
  - **#3 (kode, arsitektural)** `get_repository()` = singleton anon **tanpa JWT guru** → RLS
    `auth.uid()` null → SEMUA kueri guru (students/assessments/classes/readings) kosong → 404
    (mis. "Student not found"). Melanggar desain #3 B.1 ("repository menerima user context").
    **Fix**: dependency per-request **`get_teacher_repository(request)`** (klien Supabase baru
    dengan JWT guru) + helper **`_apply_teacher_token`** yang menyetel
    `options.headers["Authorization"]` (menjangkau postgrest **dan** storage yang lazily-init).
    Semua endpoint guru (classes/students/assessments/dashboard/readings) kini pakai dependency
    ini. Mode in-memory/demo tetap lewat singleton. **Test**: `test_teacher_repository_carries_jwt`
    (live, +kontrol negatif singleton anon).
  - **#4 (SQL)** signed upload `upsert=true` pada objek yang **sudah ada** (rekam ulang/retry) →
    Supabase Storage melakukan **UPDATE** → butuh policy `UPDATE` `storage.objects` (sebelumnya
    hanya INSERT+SELECT) → `upload-url` balas **502**. Dikonfirmasi dokumentasi Supabase
    ("upsert needs all 3 policies"). **Perbaikan**: policy `reading_audio_owner_update` di skema +
    migrasi §6 + test live `test_signed_upload_url_upsert_existing_object`. **Perlu di-apply.**

### Konfirmasi staging (setelah migrasi #5+#6 + 2 policy fix oleh pengguna)
- `python -m scripts.verify_supabase` → **19/19 OK** (termasuk `CHECK ck_rt_proper_nouns` +
  cek fungsional policy: `users_self_insert + reading_audio_owner_update aktif`).
- `python -m pytest tests/test_supabase_live.py` → **20/20 passed** ✅ (semua policy aktif).
- `python /tmp/smoke_opsi_a.py` (lintas-deploy via ngrok) → **12/12 PASS** ✅
  (Opsi A + PUT >4.5 MB + rekam ulang/upsert).

### Fase F — Verifikasi
| Suite | Hasil |
|---|---|
| Backend non-live | **424 passed, 5 skipped, exit 0** |
| `tests/reading_framework` | **exit 0** (126/5) |
| `npx tsc` / `next lint` / `npm run build` | **bersih / bersih / sukses** |
| `seed.validate` / `check_framework_drift.sh` | **OK** / **OK** (vendored tak tersentuh) |
| `tests/test_supabase_live.py` | **20 passed** ✅ |
| `verify_supabase` | **19/19 OK** ✅ |
| Smoke test lintas-deploy (ngrok) | **12/12 PASS** ✅ |
| Smoke test lintas-deploy (**origin Vercel**) | **14/14 PASS** ✅ |

### ✅ TINDAKAN PENGGUNA (selesai: migrasi & policy sudah di-apply)
Migrasi #5, #6 + 2 policy fix (`users_self_insert`, `reading_audio_owner_update`) **sudah
di-apply** ke Supabase **staging** — terbukti dari live **20/20** + smoke **12/12** + verify
policy "aktif". **Tidak ada tindakan SQL tersisa.**

### Fase D — Deploy Vercel (FE) — ✅ SELESAI & terverifikasi end-to-end

**Status: FE ter-deploy & publik; proxy→backend tersambung; smoke lintas-deploy 14/14 PASS.**

| Item | Status | Bukti |
|---|---|---|
| Deployment Protection (Vercel Auth) | ✅ dimatikan | root & `/login` → **200** |
| Versi Next.js usang → diperbaiki + redeploy | ✅ | build sukses |
| Domain stabil ter-alias | ✅ | **`https://bacalaras-frontend.vercel.app`** (▲ Aliased) |
| Env var Vercel (`API_BASE_URL`, `SESSION_COOKIE_SECURE`) | ✅ **di-set** | `vercel env ls` → 2 var × 3 environment |
| Proxy → backend (`/api/proxy/health`, `/ready`) | ✅ **200** | setelah redeploy |
| Backend via ngrok (`/health`) | ✅ **200** | backend + Supabase sehat |
| Supabase Storage CORS (PUT dari origin Vercel) | ✅ `allow-origin: *` | preflight OK |
| CORS backend utk origin Vercel | ⚪ opsional | tidak krusial (proxy server-to-server) |
| **Smoke test lintas-deploy (origin Vercel)** | ✅ **14/14 PASS** | lihat di bawah |

**Perbaikan 502 yang dieksekusi:** project Vercel **tidak punya env var** → `backendBase()` jatuh
ke `http://localhost:8000` → proxy 502. **Di-set via CLI** (3 environment):
```
vercel env add API_BASE_URL production   → https://janene-unhanging-mandatorily.ngrok-free.dev
vercel env add API_BASE_URL preview      → (sama)
vercel env add API_BASE_URL development  → (sama)
vercel env add SESSION_COOKIE_SECURE production/preview/development → true
vercel --prod   # redeploy → https://bacalaras-frontend.vercel.app
```
Verifikasi: `/api/proxy/health` & `/api/proxy/ready` → **200**.

**Smoke test lintas-deploy (`/tmp/smoke_vercel.py`) — 14/14 PASS** (semua lewat Vercel, bukan ngrok langsung):
1. `proxy → backend /health 200` ✅
2. `login guru via proxy 200 + JWT` ✅
3. `cookie sesi ter-set (httpOnly + Secure)` ✅
4. `create assessment via proxy 200` ✅ (cookie→Bearer otomatis)
5. `upload-url → mode=signed` ✅
6. `path berprefix {teacher}/{assessment}/` ✅
7. `PUT langsung ke Supabase 200` ✅
8. `objek tersimpan di Storage` ✅
9. `pipeline via audio_path 200` (state COMPREHENSION) ✅
10. `audio_url = path (tak diunggah ulang)` ✅
11. `hasil punya wcpm/accuracy` ✅
12. `create assessment #2 200` ✅
13. **`PUT >4.5 MB via signed URL sukses`** (5.24 MB — bypass batas body Vercel) ✅
14. **`rekam ulang (upsert) objek sama sukses`** ✅
+ Korelasi **`X-Request-ID`**: id di respons proxy = entri log backend ✅.

**Catatan penting (CORS & operasional):**
- Alur browser = `browser → /api/proxy (same-origin Vercel) → backend` (**server-to-server**) ⇒
  **CORS browser backend tidak berlaku**; satu-satunya panggilan lintas-origin = **PUT ke Supabase**
  (Storage CORS `*` ✅). `CORS_ORIGINS` backend = **opsional** (defense-in-depth).
- **URL ngrok free dinamis**: berubah tiap restart → `API_BASE_URL` di Vercel harus di-update
  (atau pakai domain statis / backend publik), jika tidak proxy kembali 502.

### Catatan
- **Fase A–E ✅; Fase D (deploy Vercel) ✅ SELESAI & terverifikasi end-to-end (smoke 14/14).**
  **Fase G (VCS)** dilewati (keputusan pengguna).
- `framework-whisper-2/` tak tersentuh (drift OK). Belum ada commit (tanpa VCS).

