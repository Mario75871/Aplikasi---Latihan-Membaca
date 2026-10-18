# BacaLaras — Paket Serah Terima (Handover) ke Server Sendiri

Paket ini berisi **source code + instruksi** untuk memindahkan **backend** BacaLaras dari
laptop + ngrok ke **server sendiri** dengan **domain statis + HTTPS**. Frontend tetap di
**Vercel**; database/auth/storage tetap di **Supabase**.

> **Baca dulu:** **`DEPLOY_SERVER.md`** — itu runbook utama, langkah demi langkah.

---

## Isi paket

| Path | Isi |
|---|---|
| **`DEPLOY_SERVER.md`** | ⭐ Runbook lengkap (FASE 0–9), termasuk **§11 Keselarasan logika lintas-sisi**. Mulai dari sini. |
| **`smoke_deploy.py`** | Skrip uji end-to-end (Vercel → proxy → backend → Supabase). Dipakai di FASE 8. |
| `backend/` | Backend FastAPI (termasuk `Dockerfile`, `migrations/`, `scripts/`, `reading_framework/` vendored). |
| `frontend/` | Frontend Next.js **source saja** (untuk cek keselarasan §11; tidak dijalankan di server ini). |
| `framework-whisper-2/` | Sumber framework referensi (untuk cek anti-drift §11.4). Tidak ikut runtime. |
| `integration_6.md` | Dokumen plan integrasi terakhir (konteks keputusan & riwayat bug yang sudah diperbaiki). |
| `.gitignore` | Aturan ignore repo. |

> **Tidak disertakan (sengaja):** `node_modules/`, `.next/`, `.vercel/`, `__pycache__/`,
> dan **semua berkas `.env*`** (berisi kredensial). Lihat bagian *Keamanan*.

---

## Ringkasan arsitektur

```
Browser ──HTTPS──► Vercel (frontend Next.js)
                      │  /api/proxy/*  (server-to-server: cookie httpOnly → Bearer)
                      ▼
              Backend FastAPI  ◄── domain statis + TLS (Caddy) ──► Supabase
              (server ini)        (menggantikan ngrok)             ├─ Postgres + RLS
                                                                    ├─ Auth (JWT guru)
                                                                    └─ Storage (audio)
```

- **Server ini menjalankan:** backend FastAPI (Docker) + reverse proxy (Caddy).
- **Tetap di cloud:** Supabase (DB/Auth/Storage) dan Vercel (frontend).
- **Kebutuhan resource (terukur):** model `base` int8 → **peak ~0,5 GB RAM** saat
  transkripsi. RAM 8 GB / Intel i3 gen 12 **sangat cukup**; **tidak perlu GPU**.

---

## Langkah cepat

1. Baca **`DEPLOY_SERVER.md`** bagian §0 (prinsip) & §1 (minta kredensial ke pemilik).
2. Ikuti **FASE 0–7** (§2–§9): siapkan server → DNS → transfer → Supabase → env → Docker → Caddy → update Vercel.
3. Jalankan **FASE 8** (§10) — **semua pengujian wajib**, termasuk `smoke_deploy.py`.
4. Jalankan **FASE 9** (§11) — pastikan **frontend & backend selaras** (anti-drift).
5. Centang **§13 Checklist akhir** sampai semua terpenuhi.

---

## Keamanan (PENTING)

- **JANGAN** memakai kredensial `.env.test` milik pengembang. Buat **`.env` baru** di server
  dengan kredensial **produksi** (lihat `DEPLOY_SERVER.md` §6).
- **`SUPABASE_SERVICE_ROLE_KEY` = rahasia.** Server-only. **Jangan pernah** dikirim ke
  frontend/klien. Jangan pula `SUPABASE_KEY` (anon) disamakan dengan service-role.
- Saat `ENV=production`, backend **menolak start (fail-fast)** bila: `AUTH_DISABLED=true`,
  `SESSION_COOKIE_SECURE=false`, `CORS_ORIGINS` memuat `*`, atau anon == service-role.
  Ini pengaman — **perbaiki env, jangan matikan validasi**.
- Firewall server: hanya **22 (SSH), 80, 443**.

---

## Prinsip yang tidak boleh dilanggar

1. **Supabase schema = sumber kanonis.** ID `uuid` dibuat DB; `teacher_id` boleh `null`;
   `null` ≠ `0`.
2. **`backend/reading_framework/` = vendored, jangan dimodifikasi.**
3. **Frontend hanya presentasi.** Semua keputusan/threshold dihitung **di backend**.
4. **Aturan lintas-sisi ditegakkan saat runtime**, bukan hanya test.
5. **DB ikut menjaga invarian** (CHECK, RLS, trigger) — *defense in depth*.
6. **Hybrid key:** jalur guru = anon (RLS aktif); jalur admin/seed = service-role (server-only).

---

## Bantuan / pertanyaan

Semua nilai yang perlu diisi ditandai **⟨ISI: …⟩** di `DEPLOY_SERVER.md`. Bila ada
perbedaan konstanta frontend ↔ backend, **selaraskan ke arah backend** (backend = sumber
kebenaran), lalu jalankan ulang §11.3 sampai hijau sebelum deploy.
