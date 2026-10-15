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
