-- ============================================================
-- Migrasi integrasi #7 — tabel pendaftaran akun mandiri (sign up manual).
-- Jalankan di Supabase SQL Editor (atau psql). Idempotent, aman diulang.
-- Sumber kanonis tetap supabase_schema.sql (salinan blok yang sama ada di sana).
--
-- Tabel ini menyimpan TANTANGAN OTP (kode verifikasi email) untuk alur daftar:
--   /auth/signup/start   → simpan hash kode + kirim email
--   /auth/signup/verify  → cocokkan kode, terbitkan tiket
--   /auth/signup/complete→ buat user di Supabase Auth, hapus/tinggalkan baris
--
-- PRASYARAT: tidak ada (berdiri sendiri). Tidak menyentuh tabel yang sudah ada,
-- jadi tidak ada risiko terhadap data guru yang sedang berjalan.
-- ============================================================

create table if not exists signup_otp (
    id          uuid primary key default gen_random_uuid(),
    email       text not null,
    code_hash   text not null,          -- hanya HMAC; kode mentah TIDAK PERNAH disimpan
    name        text,                   -- nama dari langkah 1, ditahan sampai selesai
    attempts    smallint not null default 0,
    consumed_at timestamptz,            -- terisi = kode sudah terpakai / dibatalkan
    expires_at  timestamptz not null,
    created_at  timestamptz not null default now(),
    request_ip  text
);

-- Pencarian utama: tantangan terbaru yang masih terbuka untuk satu email.
create index if not exists idx_signup_otp_email on signup_otp(email, created_at desc);

-- ---------- RLS: aktif TANPA policy ----------
-- Sengaja tidak ada policy sama sekali: hanya service-role (backend) yang boleh
-- menyentuh tabel ini. Anon & authenticated tidak melihat apa pun.
-- Pola yang sama sudah dipakai tabel audio_purge_log (lihat integration_5/6 dan
-- supabase_schema.sql), dan terbukti bekerja.
alter table signup_otp enable row level security;

-- ---------- Housekeeping (opsional, jalankan manual bila tabel menumpuk) ----------
-- Baris kedaluwarsa boleh dihapus kapan saja; tidak ada yang membacanya.
-- delete from signup_otp where created_at < now() - interval '7 days';

-- ---------- Verifikasi cepat ----------
-- select count(*) from signup_otp;
-- select relname, relrowsecurity from pg_class where relname = 'signup_otp';  -- harus t
