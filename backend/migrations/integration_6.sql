-- ============================================================
-- Migrasi integrasi #6 — hardening skema (CHECK constraint, FK, index).
-- Jalankan di Supabase SQL Editor (atau psql). Untuk DELTA aman di DB yang
-- SUDAH BERISI DATA, pola: add ... NOT VALID → bersihkan data → validate.
-- Idempotent (drop if exists + add). Sumber kanonis tetap supabase_schema.sql.
--
-- PRASYARAT: terapkan juga backend/migrations/integration_5.sql (#5: updated_at +
-- audio_purge_log) bila belum, karena index di bawah menargetkan audio_purge_log.
-- ============================================================

-- ---------- 0) Pastikan delta #5 sudah ada (idempotent, aman diulang) ----------
alter table assessments add column if not exists updated_at timestamptz default now();
alter table students    add column if not exists updated_at timestamptz default now();
alter table classes     add column if not exists updated_at timestamptz default now();
alter table users       add column if not exists updated_at timestamptz default now();
create table if not exists audio_purge_log (
    id            bigserial primary key,
    assessment_id uuid not null,
    purged_at     timestamptz not null default now(),
    status        text not null check (status in ('PURGED','FAILED','SKIPPED')),
    attempts      smallint not null default 0,
    note          text
);
alter table audio_purge_log enable row level security;

-- ---------- 1) Laporan data yang melanggar (JALANKAN SEBELUM VALIDATE) ----------
-- Bila ada baris di bawah ini, PERBAIKI dulu datanya, baru jalankan VALIDATE.
-- (Sengaja tidak menghapus/mengubah data otomatis.)
--
-- select id, accuracy from assessments where accuracy is not null and (accuracy < 0 or accuracy > 100);
-- select id, wcpm from assessments where wcpm is not null and wcpm < 0;
-- select id from assessments where retrieve is not null and (retrieve < 0 or retrieve > 100);
-- select id from assessments where interpret is not null and (interpret < 0 or interpret > 100);
-- select id from assessments where reflect is not null and (reflect < 0 or reflect > 100);
-- select id from assessments where completed_at is not null and completed_at < created_at;
-- select id from assessments where consecutive_drops is not null and consecutive_drops < 0;
-- select id from assessments where jsonb_typeof(rules_fired) <> 'array';
-- select id from assessments where framework_result is not null and jsonb_typeof(framework_result) <> 'object';
-- select id, position from word_scores where position < 0;
-- select id, confidence from word_scores where confidence is not null and (confidence < 0 or confidence > 1);
-- select id from word_scores where jsonb_typeof(review_reasons) <> 'array';
-- select id from reading_texts where jsonb_typeof(proper_nouns) <> 'array';
-- select id from reading_questions where not (jsonb_typeof(options) in ('object','array'));

-- ---------- 2) CHECK nilai penilaian (add NOT VALID dulu) ----------
alter table assessments drop constraint if exists ck_assess_wcpm;
alter table assessments add constraint ck_assess_wcpm
    check (wcpm is null or wcpm >= 0) not valid;
alter table assessments drop constraint if exists ck_assess_accuracy;
alter table assessments add constraint ck_assess_accuracy
    check (accuracy is null or accuracy between 0 and 100) not valid;
alter table assessments drop constraint if exists ck_assess_retrieve;
alter table assessments add constraint ck_assess_retrieve
    check (retrieve is null or retrieve between 0 and 100) not valid;
alter table assessments drop constraint if exists ck_assess_interpret;
alter table assessments add constraint ck_assess_interpret
    check (interpret is null or interpret between 0 and 100) not valid;
alter table assessments drop constraint if exists ck_assess_reflect;
alter table assessments add constraint ck_assess_reflect
    check (reflect is null or reflect between 0 and 100) not valid;
alter table assessments drop constraint if exists ck_assess_time;
alter table assessments add constraint ck_assess_time
    check (completed_at is null or completed_at >= created_at) not valid;
alter table assessments drop constraint if exists ck_assess_consec_drops;
alter table assessments add constraint ck_assess_consec_drops
    check (consecutive_drops is null or consecutive_drops >= 0) not valid;
alter table assessments drop constraint if exists ck_assess_rules_fired;
alter table assessments add constraint ck_assess_rules_fired
    check (jsonb_typeof(rules_fired) = 'array') not valid;
alter table assessments drop constraint if exists ck_assess_framework;
alter table assessments add constraint ck_assess_framework
    check (framework_result is null or jsonb_typeof(framework_result) = 'object') not valid;
alter table assessments drop constraint if exists ck_assess_previous_wcpm;
alter table assessments add constraint ck_assess_previous_wcpm
    check (previous_wcpm is null or previous_wcpm >= 0) not valid;
alter table assessments drop constraint if exists ck_assess_previous_accuracy;
alter table assessments add constraint ck_assess_previous_accuracy
    check (previous_accuracy is null or previous_accuracy between 0 and 100) not valid;

alter table word_scores drop constraint if exists ck_ws_position;
alter table word_scores add constraint ck_ws_position
    check (position >= 0) not valid;
alter table word_scores drop constraint if exists ck_ws_conf;
alter table word_scores add constraint ck_ws_conf
    check (confidence is null or confidence between 0 and 1) not valid;
alter table word_scores drop constraint if exists ck_ws_review;
alter table word_scores add constraint ck_ws_review
    check (jsonb_typeof(review_reasons) = 'array') not valid;

alter table reading_texts drop constraint if exists ck_rt_proper_nouns;
alter table reading_texts add constraint ck_rt_proper_nouns
    check (jsonb_typeof(proper_nouns) = 'array') not valid;

alter table reading_questions drop constraint if exists ck_rq_options;
alter table reading_questions add constraint ck_rq_options
    check (jsonb_typeof(options) = 'object' or jsonb_typeof(options) = 'array') not valid;

-- ---------- 3) VALIDATE (gagal bila masih ada data melanggar) ----------
alter table assessments     validate constraint ck_assess_wcpm;
alter table assessments     validate constraint ck_assess_accuracy;
alter table assessments     validate constraint ck_assess_retrieve;
alter table assessments     validate constraint ck_assess_interpret;
alter table assessments     validate constraint ck_assess_reflect;
alter table assessments     validate constraint ck_assess_time;
alter table assessments     validate constraint ck_assess_consec_drops;
alter table assessments     validate constraint ck_assess_rules_fired;
alter table assessments     validate constraint ck_assess_framework;
alter table assessments     validate constraint ck_assess_previous_wcpm;
alter table assessments     validate constraint ck_assess_previous_accuracy;
alter table word_scores     validate constraint ck_ws_position;
alter table word_scores     validate constraint ck_ws_conf;
alter table word_scores     validate constraint ck_ws_review;
alter table reading_texts   validate constraint ck_rt_proper_nouns;
alter table reading_questions validate constraint ck_rq_options;

-- ---------- 4) FK reading_id eksplisit + index prune ----------
alter table assessments drop constraint if exists assessments_reading_id_fkey;
alter table assessments add constraint assessments_reading_id_fkey
    foreign key (reading_id) references reading_texts(id) on delete restrict;

create index if not exists idx_audio_purge_assessment on audio_purge_log(assessment_id);

-- ---------- 5) FIX (integrasi #6, Fase D): policy INSERT `users` ----------
-- Blocker runtime: `_sync_public_user` (login) & pemulihan `require_teacher` meng-upsert
-- `public.users` dengan id = auth.uid(). Upsert PostgREST = INSERT ... ON CONFLICT →
-- butuh policy INSERT. Tanpa ini, **login guru selalu 503** (ditemukan saat smoke test
-- staging; tidak tertangkap test lama karena live test membuat baris via service-role).
drop policy if exists users_self_insert on users;
create policy users_self_insert on users
    for insert with check (id = auth.uid());

-- ---------- 6) FIX (integrasi #6, Fase D): policy UPDATE `storage.objects` ----------
-- Blocker runtime kedua (ditemukan saat smoke test lintas-deploy): signed upload URL
-- dibuat dengan `upsert=true` (agar rekam ulang/retry boleh menimpa objek). Saat objek
-- SUDAH ada, Supabase Storage melakukan UPDATE → butuh policy UPDATE. Tanpa ini,
-- `POST /assessments/{id}/audio/upload-url` → **502** (403 RLS "new row violates RLS").
drop policy if exists reading_audio_owner_update on storage.objects;
create policy reading_audio_owner_update on storage.objects
    for update to authenticated
    using (
        bucket_id = 'reading-audio'
        and (storage.foldername(name))[1] = auth.uid()::text
    )
    with check (
        bucket_id = 'reading-audio'
        and (storage.foldername(name))[1] = auth.uid()::text
    );

-- ---------- Verifikasi cepat ----------
-- select conname from pg_constraint where conname like 'ck_%' order by conname;
