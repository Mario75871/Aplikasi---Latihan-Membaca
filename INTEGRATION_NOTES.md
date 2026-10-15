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

### 2. Test framework
Test framework dipindahkan ke `backend/tests/reading_framework/` dengan penyesuaian jalur di `conftest.py`:
- `ROOT` menunjuk ke `framework-whisper-2/framework-whisper-2/`
- Fixture audio dan JSON regresi (`out/*.json`) tetap di lokasi asli framework
- Beberapa fixture JSON regresi disalin ke `backend/tests/reading_framework/fixtures/` untuk test BacaLaras
- **Test pipeline yang butuh mock ASR di-skip** — framework sudah terverifikasi di lokasi asli (126 passed, 5 skipped)
- Test unit framework lainnya (alignment, metrics, normalization, schema, dll) berjalan normal di backend

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
