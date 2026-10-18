# Instruksi Deploy — BacaLaras Backend ke Server Sendiri (tanpa ngrok)

> **Untuk:** teman yang menangani server (RAM ~8 GB, Intel i3 gen 12).
> **Tujuan:** memindahkan **backend** dari laptop + ngrok ke **server sendiri** dengan
> **domain statis + HTTPS**, lalu menyambungkan kembali **frontend (Vercel)** ke backend baru.
> **Hasil akhir:** tidak ada lagi ngrok; `https://<domain-backend>/health` stabil.

> **Catatan penulis:** dokumen ini ditulis dari kode aktual (bukan asumsi). Semua nilai
> (env, ambang, endpoint) diverifikasi terhadap repo. Bagian yang perlu Anda isi ditandai
> **⟨ISI: …⟩**.

---

## 0. Arsitektur & prinsip (WAJIB dipahami dulu)

```
Browser ──HTTPS──► Vercel (frontend Next.js)
                      │  /api/proxy/*  (server-to-server, cookie httpOnly → Bearer)
                      ▼
              Backend FastAPI  ◄── domain statis + TLS (Caddy)  ──►  Supabase
              (server ini)          (menggantikan ngrok)              ├─ Postgres + RLS
                                                                     ├─ Auth (JWT guru)
                                                                     └─ Storage (audio)
```

**Yang berubah:** backend tidak lagi di laptop + ngrok, tetapi di **server ini**, diakses
lewat **domain HTTPS statis**. Frontend tetap di Vercel; Supabase tetap di cloud.

**Prinsip yang TIDAK boleh dilanggar** (dijaga oleh kode + test + DB):
1. **Supabase schema = sumber kanonis.** ID `uuid` dibuat DB; `teacher_id` boleh `null`;
   `null` ≠ `0` (data hilang ≠ angka nol).
2. **`backend/reading_framework/` = vendored, JANGAN dimodifikasi.** Folder
   `framework-whisper-2/` **tidak ikut deploy** (hanya referensi).
3. **Frontend hanya presentasi.** Semua keputusan/threshold (WCPM, Accuracy, status)
   dihitung **di backend**. FE tidak menghitung ulang.
4. **Aturan lintas-sisi ditegakkan saat runtime**, bukan hanya di test.
5. **DB ikut menjaga invarian** (CHECK constraint, RLS, trigger) — *defense in depth*.
6. **Hybrid key:** jalur guru = `SUPABASE_KEY` (**anon**, RLS aktif). Jalur admin/seed =
   `SUPABASE_SERVICE_ROLE_KEY` (**server-only**, bypass RLS — jangan pernah ke klien).

---

## 1. Informasi yang harus diminta dari pemilik (isi dulu sebelum mulai)

| Item | Nilai | Catatan |
|---|---|---|
| Nama domain backend | ⟨ISI: mis. `api.bacalaras.id`⟩ | A record → IP server |
| IP publik server | ⟨ISI⟩ | |
| `SUPABASE_URL` | ⟨ISI: `https://<ref>.supabase.co`⟩ | project **produksi/staging** |
| `SUPABASE_KEY` (anon) | ⟨ISI⟩ | dipakai jalur guru |
| `SUPABASE_SERVICE_ROLE_KEY` | ⟨ISI⟩ | **rahasia**, server-only |
| Origin frontend Vercel | ⟨ISI: `https://bacalaras-frontend.vercel.app`⟩ | untuk `CORS_ORIGINS` |
| Email guru produksi | ⟨ISI⟩ | akun Supabase Auth untuk login guru |
| OS server | ⟨ISI: Ubuntu 22.04/24.04 dsb.⟩ | |

> **⚠️ Jangan pakai kredensial `.env.test`** milik pengembang. Buat `.env` baru di server.

---

## 2. FASE 0 — Persiapan server

```bash
# 1) Update & paket dasar
sudo apt update && sudo apt -y upgrade
sudo apt -y install ca-certificates curl git ufw

# 2) Docker (dipakai untuk menjalankan backend)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"      # lalu logout/login agar berlaku

# 3) Firewall: hanya SSH + HTTP + HTTPS
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
sudo ufw status
```

**Cek CPU core** (untuk `WHISPER_CPU_THREADS` nanti):

```bash
nproc                 # jumlah thread logis
lscpu | grep -E "^CPU\(s\)|Core|Model name"
```

> **Catatan RAM/CPU:** model `base` (int8) butuh **peak ~0,5 GB RAM** saat transkripsi
> (terukur). 8 GB sangat cukup. Server ini **hanya** menjalankan backend + reverse proxy
> (DB & FE di cloud), jadi lega. **Tidak perlu GPU.**

---

## 3. FASE 1 — Domain & DNS

1. Buat **A record**: `api.⟨domain⟩` → **IP publik server**.
2. Tunggu propagasi DNS, cek:
   ```bash
   dig +short api.⟨domain⟩      # harus menunjuk IP server
   ```
3. **Jangan** lanjut ke TLS sebelum DNS benar.

---

## 4. FASE 2 — Transfer source code ke server

> **PENTING:** proyek ini **belum memakai VCS (git)**. Jadi kirim **folder apa adanya**
> (bukan `git clone`). Yang dibutuhkan di server: **`backend/`** (termasuk
> `backend/reading_framework/`). Folder `frontend/` & `framework-whisper-2/` **tidak**
> perlu untuk menjalankan backend, tetapi lihat §9 (verifikasi keselarasan butuh keduanya).

**Struktur yang benar:**
```
<root>/
├── backend/            ← WAJIB (termasuk reading_framework/)
│   ├── main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── supabase_schema.sql
│   ├── migrations/
│   ├── services/ api/ rules/ seed/ scripts/ tests/
│   └── reading_framework/     ← VENDORED, jangan diubah
├── frontend/           ← (untuk cek keselarasan; tidak dipakai runtime backend)
└── framework-whisper-2/  ← tidak perlu
```

**Cara transfer (pilih salah satu):**

```bash
# Opsi A: rsync dari mesin pengembang (paling aman, hemat)
rsync -av --exclude 'node_modules' --exclude '.next' --exclude '__pycache__' \
  --exclude '.env' --exclude '.env.*' --exclude '.venv' \
  backend/ user@SERVER:/opt/bacalaras/backend/

# Opsi B: tar + scp
tar --exclude='__pycache__' --exclude='.env*' --exclude='.venv' \
    -czf backend.tgz backend/
scp backend.tgz user@SERVER:/opt/bacalaras/
```

**JANGAN transfer:** `.env`, `.env.test`, `.venv/`, `node_modules/`, `.next/`, `__pycache__/`.

**Cek setelah transfer:**
```bash
cd /opt/bacalaras/backend
ls -la                        # ada main.py, Dockerfile, requirements.txt, reading_framework/
python3 -c "print('backend folder ok')"
```

---

## 5. FASE 3 — Supabase (skema, policy, seed)

> **Jika memakai project Supabase yang SUDAH terpasang** (kasus staging yang sudah jalan):
> lewati ke langkah **5b** (verifikasi). Jika **project baru**, lakukan 5a.

### 5a. Terapkan skema (project baru)
Di **Supabase Dashboard → SQL Editor**, jalankan berurutan:
```
backend/supabase_schema.sql              # skema kanonis (tabel, RLS, policy, bucket)
backend/migrations/integration_5.sql     # updated_at + audio_purge_log
backend/migrations/integration_6.sql     # CHECK + FK + index (pola NOT VALID → validate)
```
> `integration_6.sql` menyertakan **query laporan data melanggar** — jalankan dulu bila DB
> sudah berisi data, perbaiki, baru `validate`.

Pastikan bucket Storage **private** `reading-audio` ada (sudah dibuat oleh skema).

### 5b. Verifikasi skema & policy (dari server, butuh kredensial)
```bash
cd /opt/bacalaras/backend
cp .env.test.example .env.test     # lalu isi 3 nilai:
#   SUPABASE_TEST_URL=https://<ref>.supabase.co
#   SUPABASE_TEST_ANON_KEY=...
#   SUPABASE_TEST_SERVICE_ROLE_KEY=...
set -a && source .env.test && set +a
python -m scripts.verify_supabase          # target: 19/19 OK
python -m pytest tests/test_supabase_live.py -v   # target: 20 passed
```
> Test live membuat **data uji sementara** lalu membersihkannya sendiri (idempotent).
> **Hanya** arahkan ke project yang benar — jangan menabrak data produksi nyata.

### 5c. Seed teks bacaan (idempotent, aman diulang)
```bash
set -a && source .env.test && set +a
export SUPABASE_URL=$SUPABASE_TEST_URL
export SUPABASE_SERVICE_ROLE_KEY=$SUPABASE_TEST_SERVICE_ROLE_KEY
python -m seed.validate          # validasi penjenjangan teks
python -m seed.load_supabase     # muat 9 teks Level 1–3 (upsert)
```

### 5d. Akun guru produksi
- Buat user guru via **Supabase → Authentication → Users** (email + password, confirmed).
- Saat login pertama, backend otomatis menyinkronkan baris `public.users`
  (`_sync_public_user`). Tidak perlu seeding manual.

---

## 6. FASE 4 — Konfigurasi env backend (produksi)

Buat file env (jangan commit): `/opt/bacalaras/backend.env`

```bash
# === ENV & keamanan (WAJIB) ===
ENV=production
AUTH_DISABLED=false
SESSION_COOKIE_SECURE=true

# === CORS (origin FE eksplisit, JANGAN '*') ===
CORS_ORIGINS=https://bacalaras-frontend.vercel.app

# === Supabase ===
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_KEY=<anon-key>
SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
# SUPABASE_JWT_SECRET=<opsional>

# === Whisper (CPU) ===
WHISPER_MODEL=base
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
WHISPER_CPU_THREADS=4
DEMO_FALLBACK=false

# === Batas audio & penyimpanan ===
MAX_AUDIO_BYTES=10485760
MAX_AUDIO_DURATION_SEC=300
AUDIO_ALLOWED_FORMATS=wav,mp3
TARGET_SAMPLE_RATE=16000
AUDIO_STORAGE_BUCKET=reading-audio
AUDIO_SIGNED_URL_TTL_SEC=600
ASR_TIMEOUT_SEC=300

# === Sesi & observability ===
SESSION_TTL_HOURS=12
LOG_LEVEL=INFO
AUDIO_RETENTION_MONTHS=12

# === Akun demo (fallback lokal; di produksi tidak dipakai) ===
DEMO_USERNAME=guru@demo.com
DEMO_PASSWORD=demo123
```

> **`ENV=production` akan MENOLAK startup (fail-fast)** bila salah satu terjadi:
> - `AUTH_DISABLED=true`
> - `SESSION_COOKIE_SECURE=false`
> - `CORS_ORIGINS` mengandung `*`
> - `SUPABASE_KEY == SUPABASE_SERVICE_ROLE_KEY` (anon == service-role → RLS bocor)
>
> Ini pengaman, bukan bug. Perbaiki env, jangan matikan validasi.

> **`WHISPER_CPU_THREADS`:** set = jumlah core fisik (i3 gen 12 biasanya **4**). Terlalu
> besar tidak mempercepat dan bisa berebut CPU.

> **Rate limit in-memory → WAJIB 1 worker.** Jangan jalankan multi-worker/multi-instance
> tanpa Redis (lihat §7).

---

## 7. FASE 5 — Jalankan backend (Docker, direkomendasikan)

`backend/Dockerfile` sudah menyiapkan: non-root, pre-download model Whisper saat build
(anti cold-start), healthcheck, dan `--workers 1`.

```bash
cd /opt/bacalaras/backend

# Build (unduh model saat build → butuh internet sekali)
sudo docker build -t bacalaras-backend:2.5 --build-arg WHISPER_MODEL=base .

# Jalankan (bind ke localhost saja — Caddy yang mengekspos ke publik)
sudo docker run -d \
  --name bacalaras-backend \
  --restart unless-stopped \
  --env-file /opt/bacalaras/backend.env \
  -p 127.0.0.1:8000:8000 \
  bacalaras-backend:2.5

# Cek
sudo docker ps
sudo docker logs --tail 50 bacalaras-backend
```

**Yang harus terlihat di log:** `startup BacaLaras API v2.5`, `[speech] Model loaded`,
tanpa `RuntimeError` env.

```bash
# Health dari dalam server
curl -s http://127.0.0.1:8000/health ; echo
curl -s http://127.0.0.1:8000/ready  ; echo
# Harapan:
# /health → {"status":"ok",...,"repository":"supabase","whisper_loaded":true,"auth_disabled":false}
# /ready  → {"status":"ready","model_loaded":true,"demo_mode":false,"repository_ok":true}
```

> **Alternatif tanpa Docker** (jika diinginkan): venv + `uvicorn main:app --host 127.0.0.1
> --port 8000 --workers 1` di bawah `systemd`. Model akan diunduh saat start pertama
> (butuh internet). Docker lebih disarankan karena model sudah ter-cache di image.

---

## 8. FASE 6 — Reverse proxy + HTTPS (Caddy, auto-TLS)

```bash
sudo apt -y install debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
  | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
  | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt -y install caddy
```

`/etc/caddy/Caddyfile`:
```
api.⟨domain⟩ {
    reverse_proxy 127.0.0.1:8000
}
```

```bash
sudo systemctl reload caddy
sudo systemctl status caddy --no-pager
```

**Verifikasi publik (TLS):**
```bash
curl -s https://api.⟨domain⟩/health ; echo
curl -s https://api.⟨domain⟩/ready  ; echo
# → 200 + JSON seperti §7
```

> **CORS browser ke backend TIDAK krusial** di arsitektur ini: browser hanya memanggil
> **proxy same-origin di Vercel** (`/api/proxy`), yang meneruskan ke backend
> **server-to-server**. Satu-satunya panggilan lintas-origin adalah **PUT audio langsung
> ke Supabase** (Storage CORS = `allow-origin: *`). `CORS_ORIGINS` tetap diisi origin
> Vercel sebagai *defense-in-depth*.

---

## 9. FASE 7 — Update frontend (Vercel)

**Arahkan FE ke domain backend baru (menggantikan URL ngrok).**

```bash
cd frontend
# Hapus nilai lama (URL ngrok) bila ada, lalu set nilai baru:
vercel env rm API_BASE_URL production preview development
printf 'https://api.⟨domain⟩' | vercel env add API_BASE_URL production
printf 'https://api.⟨domain⟩' | vercel env add API_BASE_URL preview
printf 'https://api.⟨domain⟩' | vercel env add API_BASE_URL development

# Pastikan cookie Secure aktif (FE selalu HTTPS di Vercel):
vercel env ls
# SESSION_COOKIE_SECURE harus = true (Production/Preview)

# Env hanya berlaku pada deployment BARU → wajib redeploy:
vercel --prod --yes
```

> **Catatan header `ngrok-skip-browser-warning`:** proxy FE masih mengirim header ini; setelah
> pindah dari ngrok, header itu **tidak berpengaruh** (backend mengabaikannya). Tidak perlu
> diubah, tetapi boleh dibersihkan.

**Verifikasi proxy→backend:**
```bash
VFE=https://bacalaras-frontend.vercel.app
curl -s "$VFE/api/proxy/health" ; echo   # → {"status":"ok",...}
curl -s "$VFE/api/proxy/ready"  ; echo   # → {"status":"ready",...}
```

---

## 10. FASE 8 — VERIFIKASI (pengujian relevan) ✅ WAJIB

Jalankan **semua** di bawah ini. Semua harus hijau sebelum dianggap selesai.

### 10.1 Backend unit + API + framework (di server)
```bash
cd /opt/bacalaras/backend
python -m pytest tests -q -p no:cacheprovider
# Harapan: 424 passed, 5 skipped  (5 skip = test integrasi ASR nyata, di-gate env)
python -m pytest tests/reading_framework -q
# Harapan: hijau
```

### 10.2 Guard env produksi (pastikan tidak fail-fast)
```bash
python -m pytest tests/test_env_validation.py -q
```

### 10.3 Supabase live (butuh `.env.test`, lihat §5b)
```bash
set -a && source .env.test && set +a
python -m scripts.verify_supabase                      # → 19/19 OK
python -m pytest tests/test_supabase_live.py -q        # → 20 passed
```

### 10.4 Kontrak framework (anti-drift vendored)
```bash
bash scripts/check_framework_drift.sh
# Harapan: OK (backend/reading_framework/ identik dengan sumber)
```

### 10.5 End-to-end lintas-deploy (dari origin Vercel)
Jalankan **smoke test lintas-deploy** (skrip di lampiran A) yang menempuh:
```
proxy → /health → login guru → cookie httpOnly+Secure → create assessment
→ upload-url (signed) → PUT audio langsung ke Supabase → pipeline penilaian
→ PUT >4.5 MB (uji bypass batas body Vercel) → rekam ulang/upsert
```
Harapan: **semua PASS**. Ini membuktikan FE (Vercel) ↔ backend (server ini) ↔ Supabase
tersambung end-to-end tanpa ngrok.

### 10.6 Observabilitas
```bash
# X-Request-ID dikembalikan proxy = entri log backend
curl -s -D - -o /dev/null https://api.⟨domain⟩/health | grep -i x-request-id
sudo docker logs --tail 20 bacalaras-backend | grep request_id
```

---

## 11. FASE 9 — KESELARASAN LOGIKA LINTAS-SISI ⭐ (permintaan khusus)

> **Risiko nyata:** jika frontend diambil dari **snapshot lama** (mis. versi yang masih
> memakai ngrok, atau sebelum penyelarasan), maka **aturan/konstanta bisa berbeda** dengan
> backend. Backend & frontend HARUS memakai angka & alur yang sama. Berikut cara
> memastikannya.

### 11.1 Tabel "satu sumber kebenaran" (wajib sama)

| Konsep | **Sumber kanonis (backend)** | Cermin di frontend | Test penjaga |
|---|---|---|---|
| Ambang akurasi rendah | `rules/adaptive_rules.py` `ACCURACY_LOW=90.0` | `lib/tokens.ts` `THRESHOLDS.accuracy.low=90` | `tests/test_api.py::test_frontend_thresholds_match_backend` |
| Ambang akurasi tinggi | `ACCURACY_HIGH=95.0` | `THRESHOLDS.accuracy.high=95` | idem |
| Ambang pemahaman | `COMPREHENSION_MIN=80.0` | `THRESHOLDS.comprehension=80` | idem |
| Sample rate audio | `services/audio_validation.py` `target_sample_rate()` = 16000 | `lib/audio-wav.ts` `TARGET_SAMPLE_RATE=16000` | `tests/test_audio_drift.py` |
| Batas ukuran audio | `max_audio_bytes()` = 10 MB | `MAX_AUDIO_BYTES=10*1024*1024` | idem |
| Batas durasi audio | `max_audio_duration_sec()` = 300 | `MAX_AUDIO_DURATION_SEC=300` | idem |
| Aturan kata benar | `services/scoring.py` `confidence > 0.5 → Correct` | FE **tidak** menghitung | `tests/test_scoring.py` |
| Versi kontrak framework | `reading_framework` `SCHEMA_VERSION=1.0.0` | — | `tests/test_speech_schema_guard.py` |
| Nama cookie token | — | `lib/api.ts` `TOKEN_COOKIE="bacalaras_token"` | `app/api/session/route.ts` |

### 11.2 Aturan **runtime** yang harus tetap berlaku
- FE **tidak** memutuskan status siswa; hanya menampilkan. Keputusan di backend.
- FE mengambil ambang **saat runtime** dari `GET /config/thresholds` dan
  `GET /config/audio` (dikonsumsi di server component). Konstanta di `lib/tokens.ts` &
  `lib/audio-wav.ts` hanyalah **fallback** bila backend tak terjangkau.
- Semua panggilan data FE lewat **`/api/proxy`** (same-origin), bukan langsung ke backend.
  Token **tidak pernah** terlihat JS (cookie httpOnly).

### 11.3 Cara memverifikasi keselarasan (JALANKAN INI)

> Test anti-drift backend **membaca file frontend** secara relatif (`../frontend/...`).
> Karena itu jalankan dari mesin/checkout yang memiliki **kedua folder**
> (`backend/` **dan** `frontend/` dalam satu root). Bila `frontend/` tidak ada, test akan
> `skip` (bukan gagal) — jadi **pastikan tidak skip**.

```bash
# Dari root yang berisi backend/ DAN frontend/ :
cd <root>/backend
python -m pytest tests/test_audio_drift.py tests/test_api.py::test_frontend_thresholds_match_backend -v
# Harapan: PASSED (bukan SKIPPED)
```

Cek manual bila perlu (bandingkan angka):
```bash
# Backend:
grep -nE "ACCURACY_LOW|ACCURACY_HIGH|COMPREHENSION_MIN" backend/rules/adaptive_rules.py
grep -nE "MAX_AUDIO_BYTES|MAX_AUDIO_DURATION_SEC|TARGET_SAMPLE_RATE" backend/services/audio_validation.py
# Frontend:
grep -nE "THRESHOLDS|accuracy|comprehension" frontend/lib/tokens.ts
grep -nE "TARGET_SAMPLE_RATE|MAX_AUDIO_BYTES|MAX_AUDIO_DURATION_SEC" frontend/lib/audio-wav.ts
```

### 11.4 Cek khusus "frontend dari snapshot lama / masih ngrok"
Periksa bahwa snapshot FE **sudah** memuat perubahan penyelarasan terbaru:
1. **Proxy ada & dipakai**: `frontend/app/api/proxy/[...path]/route.ts` ada, dan
   `frontend/lib/api.ts` `apiBaseUrl()` mengembalikan **`/api/proxy`** (bukan URL absolut).
2. **Env FE**: `API_BASE_URL` (server-side), **bukan** hanya `NEXT_PUBLIC_API_BASE_URL`.
3. **Batas durasi runtime**: `frontend/app/assess/record/page.tsx` (server component)
   memanggil `getAudioConfig()`; ada `frontend/app/assess/record/RecordScreen.tsx`.
4. **Penanganan 422** (audio terlalu panjang) ada di `app/assess/processing/page.tsx`.
5. **Upload signed (Opsi A)**: `frontend/lib/api.ts` `uploadAssessmentAudio()` melakukan
   `PUT` ke `signed_url` lalu `POST /audio {audio_path}`, dengan **fallback multipart**.
6. **Tidak ada URL ngrok** yang tertanam di kode/manifest FE (harus dari env):
   ```bash
   grep -rn "ngrok" frontend/app frontend/lib || echo "OK: tidak ada ngrok di kode FE"
   ```
7. **Build FE bersih** (di mesin dev/CI, sebelum/sesudah):
   ```bash
   cd frontend && npx tsc --noEmit && npm run lint && npm run build
   ```

> Bila ada perbedaan: **selaraskan ke arah backend** (backend = sumber kebenaran), lalu
> jalankan ulang §11.3 sampai hijau, baru deploy.

---

## 12. Troubleshooting cepat

| Gejala | Penyebab umum | Tindakan |
|---|---|---|
| Backend gagal start, log `RuntimeError: Konfigurasi env tidak valid` | `ENV=production` + `SESSION_COOKIE_SECURE!=true` / `AUTH_DISABLED=true` / `CORS_ORIGINS`=`*` / anon==service | Perbaiki `/opt/bacalaras/backend.env` (lihat §6) |
| `/health` 200 tapi `/ready` 503 | Model belum termuat / Supabase tak terjangkau | Cek log `[speech] Model loaded`; cek `SUPABASE_URL/KEY` |
| Proxy FE 502 | `API_BASE_URL` FE salah / backend mati / TLS belum jadi | Cek §9 env + `curl https://api.⟨domain⟩/health` |
| Login guru 503 | Profil `public.users` gagal disinkronkan | Pastikan policy `users_self_insert` ter-apply (§5a) |
| Upload audio `upload-url` 502 | Policy `UPDATE` Storage hilang | Pastikan `reading_audio_owner_update` ter-apply (§5a) |
| RLS memblokir (data kosong/404) | JWT guru tidak menempel | Sudah ditangani kode (`get_teacher_repository`); pastikan versi backend terbaru |
| `429 Terlalu banyak permintaan` saat uji | Rate limit wajar | Tunggu jendela, atau naikkan `RATE_LIMIT_*` |
| Test anti-drift `SKIPPED` | `frontend/` tidak ada di checkout | Jalankan dari root yang punya `frontend/` (§11.3) |

---

## 13. Checklist akhir (centang semua)

- [ ] DNS `api.⟨domain⟩` → IP server benar.
- [ ] `https://api.⟨domain⟩/health` = 200, `whisper_loaded: true`, `auth_disabled: false`.
- [ ] `https://api.⟨domain⟩/ready` = 200, `repository_ok: true`, `demo_mode: false`.
- [ ] `verify_supabase` = 19/19 OK; `test_supabase_live.py` = 20 passed.
- [ ] `pytest tests -q` = 424 passed, 5 skipped; framework hijau.
- [ ] `check_framework_drift.sh` = OK.
- [ ] Test anti-drift FE↔BE **PASSED** (bukan skipped) — §11.3.
- [ ] Vercel `API_BASE_URL` = `https://api.⟨domain⟩`; `SESSION_COOKIE_SECURE=true`; **sudah redeploy**.
- [ ] `/api/proxy/health` & `/api/proxy/ready` dari Vercel = 200.
- [ ] Smoke test lintas-deploy (§10.5) semua PASS (termasuk PUT >4.5 MB & upsert).
- [ ] `X-Request-ID` respons = entri log backend.
- [ ] Docker container `--restart unless-stopped`; Caddy aktif (`systemctl status caddy`).
- [ ] UFW hanya 22/80/443.
- [ ] **Tidak ada lagi ngrok** di mana pun (kode/env/dokumen).
- [ ] `.env` & `.env.test` **tidak** ikut ter-commit/ter-transfer; service-role key aman.

---

## 14. Pemeliharaan

```bash
# Restart backend
sudo docker restart bacalaras-backend
# Update kode: transfer ulang backend/ → rebuild → ganti container
sudo docker build -t bacalaras-backend:2.5 ./backend
sudo docker stop bacalaras-backend && sudo docker rm bacalaras-backend
sudo docker run -d --name bacalaras-backend --restart unless-stopped \
  --env-file /opt/bacalaras/backend.env -p 127.0.0.1:8000:8000 bacalaras-backend:2.5
# Log
sudo docker logs -f bacalaras-backend
# Retensi audio (kebijakan 12 bulan) — jalankan via cron
python -m scripts.prune_audio              # DRY-RUN
AUDIO_RETENTION_MONTHS=12 python -m scripts.prune_audio --apply
```

> **Naikkan model Whisper** (bila akurasi kurang, dengan konsekuensi lebih lambat di CPU):
> set `WHISPER_MODEL=small` + rebuild image dengan `--build-arg WHISPER_MODEL=small`.

---

## Lampiran A — Smoke test lintas-deploy (end-to-end dari origin Vercel)

Skrip **`smoke_deploy.py`** disertakan bersama dokumen ini (folder `plan/`). Ia menempuh
jalur **persis seperti browser** (Vercel → proxy → backend → Supabase), termasuk
**PUT >4.5 MB** (bukti bypass batas body Vercel) dan **rekam ulang/upsert**. Butuh
kredensial Supabase (service-role) untuk membuat/membersihkan data uji sementara.

```bash
# dari root proyek (yang punya backend/):
set -a && source backend/.env.test && set +a
VFE=https://bacalaras-frontend.vercel.app python smoke_deploy.py
# opsional: SMOKE_WAV=/path/audio.wav   (default: WAV senyap dibuat otomatis)
```
Harapan: `==== SMOKE: 14/14 PASS ====`. Isi skrip sama dengan yang dipakai saat
verifikasi Vercel (14/14 PASS).

---

## Lampiran B — Ringkasan endpoint penting

| Endpoint | Auth | Guna |
|---|---|---|
| `GET /health` | publik | liveness + info repo/model |
| `GET /ready` | publik | readiness (model + repo) |
| `POST /auth/login` | publik | login guru → JWT |
| `GET /config/thresholds` | guru | ambang resmi (presentasi FE) |
| `GET /config/audio` | guru | konvensi audio resmi (anti-drift FE) |
| `POST /assessments/{id}/audio/upload-url` | guru | signed upload URL (Opsi A) |
| `POST /assessments/{id}/audio` | guru | pipeline penilaian (multipart ATAU `{audio_path}`) |
| `GET /assessments/{id}/audio-url` | guru | signed URL akses audio |
| `GET /docs` | publik | dokumentasi interaktif |
