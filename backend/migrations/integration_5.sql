-- ============================================================
-- Migrasi integrasi #5 — terapkan ke project Supabase (staging/produksi).
-- Jalankan di Supabase SQL Editor (atau psql). IDEMPOTENT — aman dijalankan ulang.
-- Sumber kanonis tetap `backend/supabase_schema.sql`; berkas ini hanya menerapkan
-- DELTA #5 agar DB yang sudah terpasang (#4) ikut terbarui.
-- ============================================================

-- ---------- 1) updated_at tabel mutable (D1) ----------
alter table assessments add column if not exists updated_at timestamptz default now();
alter table students    add column if not exists updated_at timestamptz default now();
alter table classes     add column if not exists updated_at timestamptz default now();
alter table users       add column if not exists updated_at timestamptz default now();

-- Backfill baris lama (sekali; aman dijalankan ulang).
update assessments set updated_at = coalesce(completed_at, created_at) where updated_at is null;
update students    set updated_at = created_at where updated_at is null;
update classes     set updated_at = created_at where updated_at is null;
update users       set updated_at = created_at where updated_at is null;

-- Fungsi set_updated_at() sudah ada dari #3. Trigger per tabel:
drop trigger if exists trg_assessments_updated_at on assessments;
create trigger trg_assessments_updated_at before update on assessments
    for each row execute function set_updated_at();
drop trigger if exists trg_students_updated_at on students;
create trigger trg_students_updated_at before update on students
    for each row execute function set_updated_at();
drop trigger if exists trg_classes_updated_at on classes;
create trigger trg_classes_updated_at before update on classes
    for each row execute function set_updated_at();
drop trigger if exists trg_users_updated_at on users;
create trigger trg_users_updated_at before update on users
    for each row execute function set_updated_at();

-- ---------- 2) Tabel log retensi audio (D2) ----------
create table if not exists audio_purge_log (
    id            bigserial primary key,
    assessment_id uuid not null,
    purged_at     timestamptz not null default now(),
    status        text not null check (status in ('PURGED','FAILED','SKIPPED')),
    attempts      smallint not null default 0,
    note          text
);
alter table audio_purge_log enable row level security;
-- Tidak ada policy untuk guru: hanya service-role (admin/seed) yang boleh akses.

-- ---------- Verifikasi cepat ----------
-- select column_name from information_schema.columns
--   where table_name in ('assessments','students','classes','users')
--     and column_name = 'updated_at';
-- select count(*) from audio_purge_log;
