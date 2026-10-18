# Integrasi Reading Framework ke BacaLaras

## Metadata integrasi

- **Sumber:** `framework-whisper-2/framework-whisper-2/reading_framework/`
- **Versi framework:** 1.0.0
- **Schema version:** 1.0.0
- **Tanggal integrasi:** 2026-10-15
- **Metode:** Vendoring (paket disalin tanpa modifikasi)

## Dependensi yang diverifikasi framework

Framework diverifikasi pada:
- Python 3.10
- faster-whisper 1.2.1 (membawa ctranslate2 4.8.2, av 17.1.0, numpy 2.2.6)
- pydantic 2.14.0
- fastapi 0.143.0
- uvicorn 0.27.0

BacaLaras backend telah upgrade dependencies ke versi yang sama.

## Cara menyinkronkan ulang

Bila framework diperbaharui:
1. Backup `backend/reading_framework/` yang lama
2. Salin ulang dari sumber dengan `xcopy /E /I /Y framework-whisper-2\framework-whisper-2\reading_framework backend\reading_framework`
3. Hapus `__pycache__/` dari hasil salin
4. Jalankan test backend dan framework: `python -m pytest`
5. Periksa `INTEGRATION_NOTES.md` ini dan sesuaikan bila ada breaking changes

## Temuan integrasi

### 1. Framework tidak dimodifikasi
Paket `reading_framework/` disalin apa adanya. Adapter BacaLaras ada di `backend/services/`.

### 1b. Penjaga kontrak framework↔backend (Fase B, integrasi #2)
`services/speech.py` memiliki `_check_framework_contract()` + konstanta
`EXPECTED_SCHEMA_VERSION` (diturunkan dari `reading_framework.config.SCHEMA_VERSION`, saat
ini `1.0.0`). Sebelum ekstraksi, adapter memverifikasi:
- `schema_version` ada dan **cocok** dengan yang diharapkan;
- bentuk wajib ada: `transcript.raw_text`, `alignment.words`, `audio.duration_seconds`.

Bila framework di-update dan mengubah kontrak, adapter **gagal cepat** dengan pesan jelas
(bukan `KeyError`/`None` diam-diam). Test: `tests/test_speech_schema_guard.py`.
**Langkah saat sync ulang:** perbarui `EXPECTED_SCHEMA_VERSION` (otomatis via import) dan
tinjau adapter bila bentuk berubah.

### 2. Test framework
Test framework dipindahkan ke `backend/tests/reading_framework/` dengan penyesuaian jalur di `conftest.py`:
- **Fase A (integrasi #2): fixture MANDIRI di dalam backend.** `ROOT` kini menunjuk
  `backend/tests/reading_framework/fixtures/` (bukan folder `framework-whisper-2/` di luar).
  Fixture yang disalin: `fixtures/audio/{indo_1-1_correct,indo_1-1_typo,tes_14_10_26_6}.wav`
  dan `fixtures/examples/question_bank/questions.json`, plus JSON regresi `fixtures/indo_*.json`.
  Dengan ini `backend/` dapat di-deploy & di-test **tanpa** folder `framework-whisper-2/`.
- Penyesuaian jalur hanya di file **test** (`conftest.py`, `test_integration_real_asr.py`,
  `test_regression_real_json.py`) — **bukan** di `reading_framework/` (vendored).
- Beberapa fixture JSON regresi ada di `backend/tests/reading_framework/fixtures/` untuk test BacaLaras
- Test pipeline yang butuh mock ASR memakai fixture audio lokal; test integrasi nyata tetap
  di-gate `RAW_READING_INTEGRATION=1` (5 skipped secara default)
- **Anti-drift (Fase D, integrasi #2):** `backend/scripts/check_framework_drift.sh`
  membandingkan `backend/reading_framework/` dengan sumber `framework-whisper-2/reading_framework/`
  (abaikan `__pycache__`/`.DS_Store`). Jalankan sebelum rilis; gagal = perlu sinkron ulang.

### 2b. Kesiapan produksi Supabase (integrasi #3)
- **Isolasi per-guru (A):** `students`/`assessments` mendapat kolom `teacher_id`
  (denormalisasi dari `classes.teacher_id`); endpoint di-scope via `require_teacher`
  (JWT → user_id). Test: `tests/test_isolation.py`.
- **RLS + hybrid key (D1):** `supabase_schema.sql` memuat RLS per-tabel (policy
  `teacher_id = auth.uid()`), bacaan global read-only untuk guru (D5). Jalur guru = anon
  key; jalur admin/seed = `SUPABASE_SERVICE_ROLE_KEY` (`get_admin_repository()`).
- **`word_scores` atomik (B.2):** RPC `replace_word_scores` (delete+insert satu transaksi,
  dengan cek kepemilikan) + fallback non-atomik.
- **Upload audio (C, D4):** hanya **WAV & MP3**, maks **10 MB** — `services/audio_validation.py`
  (validasi magic bytes). Frontend mengonversi rekaman ke WAV (`lib/audio-wav.ts`).
- **`status` awal (D.1):** `None` (bukan `"PENDING"` yang melanggar check constraint).
- **`/health` bermakna (D.3):** laporkan repository, schema_version, whisper_loaded.
- **Ambang satu sumber (F):** `GET /config/thresholds`; test anti-drift memastikan
  `frontend/lib/tokens.ts` == `rules/adaptive_rules.py`.

### 3. Entry point utama
```python
from reading_framework import transcribe_reading, FrameworkConfig
from reading_framework.asr_engine import load_model

# Muat model sekali saat startup
model, info = load_model("base", "cpu", "int8", cpu_threads=4)

# Panggil per asesmen
result = transcribe_reading(
    audio_path,
    question_id=...,
    repository=...,
    model=model,
    config=FrameworkConfig(...),
    output_dir=...,
    persist=True
)
```

### 4. Output framework (kontrak schema 1.0.0)
`result.result` adalah dict dengan struktur:
- `job`: status, job_id, question_id
- `audio`: duration_seconds (aktual), metadata
- `transcript.raw_text`: **immutable**, hasil ASR mentah
- `transcript.segments[].words[]`: timestamp + `model_probability` per kata
- `alignment.words[]`: per kata reference vs transcript
  - `operation`: match | substitution | deletion | insertion
  - `model_probability`: float | null (dari kata ASR)
  - `reference_word`, `transcript_word`: str | null
- `alignment.wer`, `alignment.cer`: metrik alignment
- `review.review_required`: bool, sinyal review bukan vonis
- `review.items[]`: flag per kata/segmen yang perlu diperiksa
- `performance`: elapsed_seconds, real_time_factor, peak_rss_mb
- `errors`, `warnings`: list pesan

### 5. Prinsip framework yang harus dipatuhi BacaLaras
1. **`raw_text` tidak pernah diubah** — bukti sumber immutable
2. **Target tidak bocor ke ASR** — `reference.used_during_asr` selalu false
3. **Confidence sinyal review, bukan vonis** — `assessment.reading_correctness_confirmed` dan `pronunciation_verified` tetap false
4. **Nilai null = tidak tersedia** — jangan pakai 0/false untuk data yang tidak ada
5. **Metadata segmen dapat berulang** — faster-whisper 1.2.1 issue, ditandai `suspicious_segment_metadata`
6. **Model base kemungkinan kurang untuk suara anak** — framework mencatat belum terukur untuk bahasa Indonesia

### 6. Risiko yang perlu diverifikasi: pergeseran probabilitas pada kata dengan tanda hubung/baca

**Situasi:** Framework melakukan alignment token setelah normalisasi. Bila satu kata ASR pecah menjadi dua token setelah normalisasi (mis. kata bertanda hubung seperti "ke-pasar"), probabilitas yang berasal dari `faster_whisper.Segment.words[].probability` bisa terpasang ke kata yang salah.

**Status: TERBUKTI (diverifikasi).** Risiko ini NYATA dan direproduksi.

**Bukti (test `backend/tests/test_speech_shift_guard.py`):**
- Referensi: `"adik pergi ke pasar itu"`; ASR menghasilkan SATU WordStamp `"ke-pasar"` (prob 0.20) + `"itu"` (prob 0.99).
- Setelah normalisasi, `raw_text` menjadi 5 token (`adik pergi ke pasar itu`), sedangkan `segments[].words` hanya 4 kata → `flat_words` bergeser.
- Hasil `align_transcript`: `pasar` mendapat prob **0.99** (milik `itu`), dan `itu` mendapat `None`. Prob 0.20 (milik `ke-pasar`) terpasang ke `ke`.

**Penanganan (framework TIDAK diubah):**
- `services/speech.py` menambahkan `apply_alignment_shift_guard()`: bila `jumlah kata segmen ≠ jumlah token transkrip ternormalisasi`, semua kata yang memakai probability ditandai `review_reasons += ["alignment_ambiguous"]` dan `review_required=True`.
- `framework_result` (JSON audit) tetap UTUH; penjaga hanya menyalin untuk `word_scores` BacaLaras.
- UI (`WordTracePanel`) menampilkan kata itu sebagai **"perlu diperiksa"**, sehingga guru tidak menaruh percaya buta pada skor kata tersebut.
- Penjaga bersifat **no-op** saat jumlah token cocok (mencegah false positive) — diuji di test yang sama.

**Sisa keterbatasan:** Penjaga menandai (bukan memperbaiki) pergeseran. Perbaikan akurat memerlukan pemetaan token→kata di dalam framework (di luar scope "tanpa modifikasi"). Bila nanti framework di-update, jalankan ulang test ini.

**TODO (manusia):** Putuskan apakah perlu patch framework di masa depan untuk pemetaan probability per kata yang tahan pecahan token.


### 7. API bawaan framework tidak dipakai
Framework menyediakan `integrations/fastapi_app.py` dengan endpoint `/jobs/*` dan storage lokal. BacaLaras tidak memakai ini; framework hanya library. API BacaLaras tetap `/assessments/*`.

### 8. Normalisasi ejaan opsional
Framework menyediakan `spelling_normalization.py` (nonaktif default). BacaLaras tidak mengaktifkannya di MVP. Bila nanti perlu, gunakan `config=FrameworkConfig(spelling_normalization_enabled=True)`.

## Catatan tambahan

- Framework mencatat metrik bahasa Indonesia **NOT MEASURED** (belum ada korpus terverifikasi)
- Model base kemungkinan kurang untuk pengucapan anak Indonesia; perlu model yang lebih besar atau fine-tuned
- Framework tidak menyimpulkan ketepatan pelafalan/fonem secara otomatis
- Confidence bukan probabilitas terkalibrasi bahwa anak membaca dengan benar
- WER=0 tidak membuktikan pelafalan benar

## Referensi
- Framework README: `framework-whisper-2/framework-whisper-2/README.md`
- Konsep: `RAW_READING.md`
- Kontrak: `JSON_SCHEMA.md`
- Integrasi website: `WEBSITE_INTEGRATION.md`
- Laporan final: `FINAL_REPORT.md`
