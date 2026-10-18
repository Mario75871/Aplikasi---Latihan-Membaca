# BacaLaras — Frontend (Next.js)

**Versi:** 2.5 · **Stack:** Next.js 15 (App Router) + TypeScript + Tailwind CSS

Aplikasi web BacaLaras: landing page publik, login guru, dashboard kelas/siswa,
dan alur asesmen siswa. Seluruh data diambil dari API backend (tidak ada mock).

---

## Menjalankan

```bash
npm install

# salin env
copy .env.example .env.local      # Windows
# cp .env.example .env.local      # macOS/Linux

npm run dev      # http://localhost:3000
npm run build    # build produksi
npm run start    # jalankan hasil build
npm run lint     # ESLint (next/core-web-vitals)
```

### Environment (`frontend-starter/.env.example`)

| Variabel | Keterangan |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | Base URL backend untuk **browser** (default `http://localhost:8000`) |
| `API_BASE_URL` | Opsional — base URL backend untuk **server component** (prioritas utama; mis. alamat internal di produksi) |

---

## Rute

| Rute | Deskripsi |
|---|---|
| `/` | Landing page publik (F-00): toggle persona Guru/Siswa, 3 disclaimer |
| `/login` | Login guru → `POST /auth/login`, token disimpan di cookie |
| `/dashboard` | Dashboard kelas (KPI + daftar siswa) |
| `/classes`, `/classes/[id]` | Daftar & detail kelas |
| `/students`, `/students/[id]`, `/students/[id]/progress` | Daftar, profil, dan progres siswa |
| `/readings` | Bank bacaan Level 1–3 |
| `/assessments`, `/assessments/[id]` | Riwayat & hasil asesmen (jejak kata) |
| `/assess` | Wizard mulai asesmen |
| `/assess/start` → `/read` → `/record` → `/review` → `/processing` → `/answer` → `/done` | Alur asesmen siswa (S-01…S-07) |

Halaman guru diproteksi `middleware.ts` (tanpa token → `/login?next=...`).

---

## Struktur

```text
frontend-starter/
├── middleware.ts                 # proteksi rute guru + redirect /login
├── tailwind.config.ts            # token warna, font, radius, shadow
├── app/
│   ├── page.tsx                  # landing (F-00)
│   ├── layout.tsx
│   └── globals.css
├── lib/
│   ├── api.ts                    # klien REST bertipe + ApiError + token cookie
│   ├── api-server.ts             # getServerToken() (server component)
│   ├── types.ts                  # tipe domain (view model)
│   ├── tokens.ts                 # konstanta status/threshold/warna
│   └── utils.ts                  # cn(), formatDateID(), countWords()
└── components/
    ├── ui/                       # primitif (Button, Card, Meter, States, DisclaimerBanner, ...)
    ├── landing/                  # LandingPage.tsx (F-00)
    ├── teacher/                  # dashboard, tabel, WordTracePanel, AssessWizard, ...
    └── student/                  # MicControl, ReadingPassage, QuestionCard, StudentShell
```

---

## Prinsip yang ditanam di komponen

| Prinsip | Implementasi |
|---|---|
| Non-punitif | kata salah = amber, bukan merah; halaman selesai tanpa angka menghakimi |
| Ikon + teks untuk status | `StatusBadge` selalu punya label & ikon |
| Target sentuh besar | tombol ≥ 44px; `MicControl` lebih besar |
| Warna punya arti tetap | `lib/tokens.ts` sebagai sumber tunggal |
| Traceability | `WordTracePanel` menampilkan confidence + kata "perlu diperiksa" |
| Disclaimer wajib | `DisclaimerBanner` varian hasbrouck/threshold/medical |
| Selalu ada jalan keluar | `ErrorState` selalu punya tombol "Coba Lagi" |
| Hasil = estimasi | label **"penilaian otomatis (estimasi)"**, tanpa label jenis kesalahan |

---

## Non-goals

Jangan tambahkan gamifikasi, leaderboard, XP, badge, TTS, PDF export, parent
dashboard, atau fitur Out of Scope lain (PRD §4).
