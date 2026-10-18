# BacaLaras — Backend (FastAPI)

Backend BacaLaras **v2.5**: asesmen membaca (WCPM, Akurasi, pemahaman) + Adaptive
Engine rule-based. Struktur sesuai PRD §36; skema DB ada di `supabase_schema.sql`.

## Struktur

```text
backend/
├── requirements.txt
├── pytest.ini
├── supabase_schema.sql         # skema Supabase PostgreSQL (§34)
├── main.py                     # entry FastAPI (v2.5) + middleware auth + CORS
├── repository.py               # Repository ABC + InMemory (default) + Supabase
├── api/
│   ├── auth.py                 # POST /auth/login, /auth/logout (D7)
│   ├── students.py             # /students ...
│   ├── classes.py              # /classes ...
│   ├── readings.py             # /readings ...
│   ├── assessments.py          # /assessments (+ audio, comprehension)
│   ├── dashboard.py            # /dashboard/class/{id}
│   └── hasbrouck.py            # /hasbrouck/reference (season opsional)
├── services/
│   ├── speech.py               # Model #1: adapter framework (audio → transkrip + confidence/kata)
│   ├── scoring.py              # Model #2: penilaian kata benar/salah (§13.2)
│   ├── assessment.py           # WCPM & Accuracy (§14, §15)
│   ├── adaptive.py             # orkestrasi Adaptive Engine
│   ├── dashboard.py            # agregasi dashboard kelas
│   └── hasbrouck.py            # tabel P25/P50 + wcpm_floor (§30)
├── rules/
│   └── adaptive_rules.py       # BR-01..BR-05, BR-07, BR-08 (§20–§26)
├── seed/
│   ├── reading_texts.py        # 9 teks Level 1–3 (B1–B3)
│   ├── validator.py            # validator penjenjangan
│   └── validate.py             # CLI: python -m seed.validate
├── reading_framework/          # VENDORED — TIDAK dimodifikasi (D13)
└── tests/                      # pytest (unit + API + skenario demo)
```

> Catatan: `services/alignment.py` (versi lama) sudah **dihapus**; alignment kini
> memakai output `reading_framework` (bukan LCS/`avg_logprob` lama).

> **Batas `framework-whisper-2/` vs `reading_framework/` (integrasi #2):**
> - `backend/reading_framework/` = **vendored**, dipakai saat **runtime** & deploy. Ini
>   satu-satunya yang ikut produksi. Jangan dimodifikasi.
> - `framework-whisper-2/` = folder **sumber/referensi** (sibling, di luar `backend/`).
>   **Tidak** ikut deploy dan **tidak** dibutuhkan saat runtime — backend mengimpor dari
>   paket lokal sendiri (`pytest.ini` → `pythonpath = .`). Isinya identik dengan
>   `backend/reading_framework/` (kecuali `__pycache__`/`.DS_Store`).
> - Test framework kini **mandiri**: fixture ada di
>   `backend/tests/reading_framework/fixtures/` sehingga seluruh test backend lulus
>   **tanpa** folder `framework-whisper-2/`. Lihat `INTEGRATION_NOTES.md`.


## Menjalankan

```bash
python -m venv .venv
.venv\Scripts\activate           # Windows
pip install -r requirements.txt

# mode demo (tanpa model Whisper):
set DEMO_FALLBACK=true           # PowerShell: $env:DEMO_FALLBACK="true"
uvicorn main:app --reload --port 8000
```

- Dokumentasi interaktif: <http://localhost:8000/docs>
- Health: <http://localhost:8000/health>

### Environment

Lihat `backend/.env.example`. Variabel utama: `WHISPER_MODEL`, `WHISPER_DEVICE`,
`WHISPER_COMPUTE_TYPE`, `WHISPER_CPU_THREADS`, `DEMO_FALLBACK`, `CORS_ORIGINS`,
`SUPABASE_URL`, `SUPABASE_KEY`, `DEMO_USERNAME`, `DEMO_PASSWORD`,
`SESSION_TTL_HOURS`, `AUTH_DISABLED`.

## Menjalankan Test

```bash
pytest -q
```

Validasi seed teks (Level B1–B3):

```bash
python -m seed.validate
```

Test integrasi opsional (butuh model Whisper + audio nyata):

```bash
set RAW_READING_INTEGRATION=1    # PowerShell: $env:RAW_READING_INTEGRATION="1"
pytest -q
```

## Auth (D7)

- `POST /auth/login` → `{token}`; `POST /auth/logout`.
- Semua endpoint kecuali `/health`, `/docs`, `/openapi.json`, `/redoc`, dan
  `/auth/*` memerlukan header `Authorization: Bearer <token>`.
- `AUTH_DISABLED=true` melewati middleware (hanya test/dev).
- **Isolasi per-guru (integrasi #3):** setiap endpoint data di-scope ke guru pemilik
  (`teacher_id` dari JWT Supabase). Guru A tidak dapat melihat kelas/siswa/asesmen guru B.

## Produksi — Supabase & deployment (integrasi #3)

**Hybrid key (D1):**
- Jalur **guru** memakai `SUPABASE_KEY` (**anon**) → RLS ditegakkan di database.
- Jalur **admin/seed** memakai `SUPABASE_SERVICE_ROLE_KEY` (**server-only**, bypass RLS).
  Jangan pernah menaruh key ini di klien/frontend.

**Migrasi & RLS:** seluruh kebijakan ada di `supabase_schema.sql` (RLS per-tabel,
`teacher_id` eksplisit, trigger `updated_at`, RPC atomik `replace_word_scores`).
Terapkan ke project Supabase sebelum menjalankan backend.

**Urutan deploy:**
1. Terapkan `supabase_schema.sql` ke project Supabase.
2. Isi env (lihat `.env.example`): `SUPABASE_URL`, `SUPABASE_KEY`,
   `SUPABASE_SERVICE_ROLE_KEY`, `CORS_ORIGINS`, batas audio.
3. `python -m seed.validate` → `python -m seed.load_supabase` (seed idempotent).
4. Jalankan backend (`uvicorn main:app`) atau image Docker (lihat `Dockerfile`).
5. Frontend: set `NEXT_PUBLIC_API_BASE_URL` (browser) / `API_BASE_URL` (server).

**Batas upload audio (D4):** maks **10 MB** (`MAX_AUDIO_BYTES`), hanya **WAV & MP3**
(divalidasi magic bytes). Klien yang merekam webm via MediaRecorder harus dikonversi.

## Model AI (§38)

| Model | Modul | Peran |
|---|---|---|
| #1 reading_framework + faster-whisper | `services/speech.py` | Audio → transkrip + timestamp + **confidence per kata** |
| #2 Penilaian Kata | `services/scoring.py` | Confidence → Correct/Incorrect → WCPM & Accuracy |

**Aturan tetap (§13.2):** `confidence > 0.5 → Correct`, `≤ 0.5 → Incorrect`; proper
noun yang terdeteksi tetap Correct.

> **Adaptive Engine tetap deterministik & rule-based** (§38.2). AI tidak menentukan
> status siswa.

## Mode demo (`DEMO_FALLBACK=true`)

Tanpa model Whisper, `services/speech.py` membuat transkrip + alignment
**deterministik lewat aligner framework asli** (bukan replay fixture mentah), lalu
menandai respons `is_demo_fallback: true`. UI menampilkan label **"Mode demo"**.
Tidak ada transkrip palsu yang diam-diam pada jalur produksi: kegagalan ASR → **503**
dengan pesan Retry.

## Catatan v2.5

- Tidak ada `self_correction`, klasifikasi jenis kesalahan, BR-06, BR-10.
- `services/scoring.py` **wajib** mencatat confidence + aturan per kata (traceability §38.3).
- `services/adaptive.py` hanya memakai WCPM, Accuracy, Comprehension, Previous
  Progress, dan Text Complexity.
- Batas WCPM memakai `wcpm_floor(grade, season)`; tidak ada angka WCPM tetap di kode.
- Temuan integrasi (termasuk pergeseran `model_probability` pada kata bertanda
  hubung) ada di `INTEGRATION_NOTES.md`.

---

## Integrasi #4 — Produksi, Hardening & Aturan Lintas-Sisi

Rencana lengkap: `../.opencode/plan/integration_4.md`. Ringkasan operasional:

### Uji Supabase staging (Fase A)

Pengujian integrasi Supabase (RLS, RPC, trigger, Storage) **di-skip** kecuali env
staging tersedia. **Jangan** arahkan pengujian destruktif ke produksi.

Isi `backend/.env.test` (salin dari `.env.test.example`) — test & skrip membacanya
otomatis:

```bash
cp backend/.env.test.example backend/.env.test   # lalu isi 3 nilai di bawah
#   SUPABASE_TEST_URL=https://xxx.supabase.co
#   SUPABASE_TEST_ANON_KEY=...
#   SUPABASE_TEST_SERVICE_ROLE_KEY=...

cd backend
python -m scripts.verify_supabase          # target: 12/12 OK (skema terpasang)
python -m pytest tests/test_supabase_live.py -v   # target: 10 passed
```

Test live membuat **2 guru uji + data sementara** lalu membersihkannya sendiri
(idempotent). Karena memakai jaringan nyata, jalankan dengan timeout lebih besar
(±60s+). Test yang dicakup: skema, **isolasi RLS lintas-guru**, RPC kepemilikan
(42501 untuk bukan pemilik), trigger konsistensi `teacher_id`, dan scoping Storage.

**Migrasi:** terapkan `supabase_schema.sql` ke project staging. **Rollback:**
`drop policy <nama> on <tabel>;` · `drop trigger <nama> on <tabel>;` ·
`alter table <tabel> disable row level security;` · `delete from storage.buckets
where id = 'reading-audio';`.

### Konvensi audio (Fase B, D2)

- Input ASR standar: **16 kHz mono**. Klien menormalkan rekaman (`frontend/lib/audio-wav.ts`
  memakai `OfflineAudioContext`), bukan decimasi kasar.
- Format diterima: **WAV & MP3** (magic bytes). Batas **10 MB/file** (`MAX_AUDIO_BYTES`).
- **Audio disimpan** di Supabase Storage bucket **private** `reading-audio`
  (path `{teacher_id}/{assessment_id}/normalized.wav`), akses via signed URL berumur
  pendek. Gagal unggah **tidak** menggagalkan penilaian (`audio_url` tetap `null`).
- Retensi: audio siswa = data sensitif; hapus berkala (kebijakan N bulan).

### Rate limit (Fase C, D4)

| Endpoint | Kunci | Batas | Jendela |
|---|---|---|---|
| `POST /assessments/{id}/audio` | per-guru | 10 | 10 menit |
| `POST /assessments/{id}/audio` | per-IP | 30 | 10 menit |
| `POST /auth/login` | per-IP | 20 | 10 menit |
| `GET /assessments/{id}` (polling) | per-guru | 120 | 1 menit |

Override via env `RATE_LIMIT_*`. **Batas MVP:** in-memory → hanya 1 proses; multi-instance
butuh store bersama (Redis).

### Sesi & HTTPS (Fase C, D5)

- Token disimpan di cookie **httpOnly** (`/api/session`, Next route handler) — JS tak bisa
  membacanya (aman dari XSS).
- `Secure` **kondisional** via `SESSION_COOKIE_SECURE` (default `false`). Saat HTTPS aktif →
  set `true`.
- `ENV=production` akan **fail-fast** bila: `AUTH_DISABLED=true`, `SESSION_COOKIE_SECURE=false`,
  `CORS_ORIGINS` berisi `*`, atau `SUPABASE_KEY == SUPABASE_SERVICE_ROLE_KEY`.
- Reverse proxy TLS disarankan (Caddy auto-TLS / Nginx + Let's Encrypt).

---

## Integrasi #5 — Sisa #4 + Kesiapan Produksi

Rencana lengkap: `../.opencode/plan/integration_5.md`. Ringkasan operasional:

### Autentikasi client ↔ backend (Fase 0, BLOCKER)

Setelah cookie sesi dipindah ke **httpOnly** (#4, D5), client component tak lagi bisa
mengirim `Authorization: Bearer` direkt ke backend (cross-origin). Solusi: **proxy
same-origin** `frontend/app/api/proxy/[...path]/route.ts` — route handler membaca cookie
httpOnly lalu meneruskan ke backend dengan Bearer. **Token tak pernah terlihat JS.**

- Browser: `apiBaseUrl()` = `/api/proxy`.
- Server component: langsung ke backend (`API_BASE_URL`) + token eksplisit.
- Backend **tidak** perlu diakses langsung dari browser (CORS lebih sempit).

### `updated_at` tabel mutable (Fase A)

`assessments`, `students`, `classes`, `users` kini punya `updated_at` + trigger
`set_updated_at()` (idempotent, di `supabase_schema.sql`). Tidak bentrok dengan trigger
`teacher_id` (kolom berbeda).

### Batas durasi audio (Fase A)

Selain batas **ukuran** 10 MB, kini ada batas **durasi** (`MAX_AUDIO_DURATION_SEC`, default
300 = 5 menit) → `422` bila melebihi. Durasi `None` (tak tersedia) **tidak** ditolak.

### Anti-drift konstanta audio (Fase A)

`GET /config/audio` mengembalikan `{target_sample_rate, max_audio_bytes, max_audio_duration_sec}`
dari satu sumber backend. Test `tests/test_audio_drift.py` memastikan konstanta
`frontend/lib/audio-wav.ts` identik.

### Akses audio (Fase B, D3)

`GET /assessments/{id}/audio-url` → **signed URL** berumur pendek (hanya pemilik; guru lain
→ 404; `audio_url` null → 404). Halaman hasil menampilkan pemutar + transkripsi.

### Retensi audio (Fase B, D2)

Kebijakan: **12 bulan** (`AUDIO_RETENTION_MONTHS`). Prune via:

```bash
python -m scripts.prune_audio            # DRY-RUN (default; tak mengubah apa pun)
AUDIO_RETENTION_MONTHS=12 python -m scripts.prune_audio --apply
```

- Hapus objek Storage → null-kan `audio_url` → catat di `audio_purge_log` (tanpa URL/path).
- Gagal hapus → **retry** (3× backoff) & **referensi dipertahankan** (anti objek yatim).
- Jadwalkan via cron eksternal / Supabase scheduled function.

### Observability & ketahanan (Fase C, D5)

- **Logging JSON** terstruktur (`logging_config.py`), level via `LOG_LEVEL`.
- Setiap respons membawa **`X-Request-ID`** + log akses (method/path/status/durasi).
- **Batas waktu ASR** (`ASR_TIMEOUT_SEC`, default 120s) → `504` (bukan menggantung).
- **`/ready`** (readiness: model termuat + repo reachable) terpisah dari `/health` (liveness).

### Deploy (Fase D, D6)

- **Frontend → Vercel**; **backend → server sendiri** (di belakang reverse proxy TLS).
- Env Vercel: `API_BASE_URL` (https backend), `SESSION_COOKIE_SECURE=true`.
- Backend: `CORS_ORIGINS` = origin Vercel eksplisit; `--workers 1` (rate-limit in-memory +
  model tunggal). Dockerfile pre-download model Whisper saat build (anti cold-start).
- Model Whisper: rekomendasi mulai `base` (CPU int8); naik ke `small` via `WHISPER_MODEL`.

---

## Integrasi #6 — Celah runtime FE + hardening skema

Rencana lengkap: `../.opencode/plan/integration_6.md`. Ringkasan:

### Batas durasi audio **ditegakkan di runtime FE** (Fase A)

Sebelumnya FE hanya tahu batas **ukuran** (10 MB); siswa bisa merekam >5 menit lalu
baru ditolak backend (**422**). Kini:

- `frontend/app/assess/record/page.tsx` = **server component** yang memanggil
  `GET /config/audio` (via `getAudioConfig()`) lalu meneruskan `max_duration_sec` ke
  komponen klien — batas durasi ditegakkan **saat runtime**, bukan hanya test.
- Bila backend tak terjangkau → fallback konstanta cermin `MAX_AUDIO_DURATION_SEC`
  di `frontend/lib/audio-wav.ts` (dijaga test anti-drift).
- Halaman `/assess/processing` menangani **422** dengan pesan "rekam ulang" khusus.

### Threshold: status fallback (Fase B)

`frontend/lib/tokens.ts` kini berstatus **fallback**; sumber runtime = `GET /config/thresholds`.
Test anti-drift memverifikasi konsumsi `/config/audio` (cegah regresi "endpoint tanpa konsumen").

### Hardening skema (Fase C) — defense in depth

`supabase_schema.sql` + `migrations/integration_6.sql` menambah **CHECK**:
- nilai `0..100` (`accuracy/retrieve/interpret/reflect/previous_accuracy`), `wcpm >= 0`,
  `confidence 0..1`, `completed_at >= created_at`;
- tipe JSONB (`rules_fired/review_reasons/proper_nouns` = array, `framework_result` = object);
- FK `assessments.reading_id` → `on delete restrict`; index `audio_purge_log(assessment_id)`.

Terapkan di Supabase (SQL Editor), urut:
```
migrations/integration_5.sql   # updated_at + audio_purge_log
migrations/integration_6.sql   # CHECK + FK + index (NOT VALID → validate)
```
> `migrations/integration_6.sql` menyertakan query laporan data melanggar — jalankan dulu bila
> DB sudah berisi data, perbaiki, baru `validate` (agar migrasi tak gagal).

### Sanitasi `X-Request-ID` (Fase E)

Middleware menyaring karakter header klien (alnum/`-_`, maks 64) → mencegah injeksi log.

### Verifikasi

```
python -m scripts.verify_supabase            # termasuk cek CHECK
python -m pytest tests/test_audio_drift.py   # anti-drift audio + konsumsi runtime
```
