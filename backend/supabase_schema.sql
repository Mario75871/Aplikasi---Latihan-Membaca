-- ============================================================
-- BacaLaras — Supabase PostgreSQL Schema (v2.5)
-- Sumber: PRD v2.5 Bagian 8 (Data Model)
-- Catatan v2.5: proper_nouns, framework_result (JSON audit), WordScores dengan
-- attempted/reason/review_reasons. TIDAK ada error pattern, self-correction.
-- ============================================================

-- Ekstensi UUID
create extension if not exists "pgcrypto";

-- ---------- USERS (Guru) ----------
create table if not exists users (
    id          uuid primary key default gen_random_uuid(),
    name        text not null,
    email       text unique not null,
    password_hash text,           -- nullable bila pakai Supabase Auth
    created_at  timestamptz default now()
);

-- ---------- CLASSES ----------
create table if not exists classes (
    id          uuid primary key default gen_random_uuid(),
    teacher_id  uuid references users(id) on delete cascade,
    name        text not null,
    grade       smallint not null check (grade between 1 and 3),
    created_at  timestamptz default now()
);

-- ---------- STUDENTS ----------
-- teacher_id: denormalisasi dari classes.teacher_id (D3, integrasi #3) untuk
-- query cepat ber-scope. Sumber kebenaran tetap classes.teacher_id.
create table if not exists students (
    id          uuid primary key default gen_random_uuid(),
    class_id    uuid references classes(id) on delete cascade,
    teacher_id  uuid references users(id) on delete cascade,   -- D3: denormalisasi
    name        text not null,
    grade       smallint not null check (grade between 1 and 3),
    created_at  timestamptz default now()
);

-- ---------- READING TEXTS ----------
create table if not exists reading_texts (
    id            uuid primary key default gen_random_uuid(),
    title         text not null,
    content       text not null,                 -- sumber target_text framework (F-04)
    grade         smallint not null check (grade between 1 and 3),
    complexity    smallint not null check (complexity between 1 and 3),
    book_level    text not null check (book_level in ('B1','B2','B3')),  -- F-04 v2.5
    word_count    int not null,
    theme         text,
    proper_nouns  jsonb not null default '[]'::jsonb,  -- D5: daftar nama per teks
    version       text not null default 'v1',          -- untuk QuestionRepository framework
    created_at    timestamptz default now(),
    updated_at    timestamptz default now()
);

-- ---------- READING QUESTIONS (F-07) ----------
create table if not exists reading_questions (
    id           uuid primary key default gen_random_uuid(),
    reading_id   uuid not null references reading_texts(id) on delete cascade,
    competency   text not null check (competency in ('retrieve','interpret','reflect')),
    prompt       text not null,
    options      jsonb not null,
    answer_id    text not null,
    position     smallint not null default 0
);

-- ---------- ASSESSMENTS ----------
-- status: INTERVENE | STAY | PROMOTION_CANDIDATE | PROMOTE (F-08)
create table if not exists assessments (
    id                uuid primary key default gen_random_uuid(),
    student_id        uuid not null references students(id) on delete cascade,
    reading_id        uuid not null references reading_texts(id),
    teacher_id        uuid references users(id) on delete cascade,  -- D3: denormalisasi
    reading_level     smallint not null check (reading_level between 1 and 3),

    -- ReadingResult (F-06)
    wcpm              numeric(6,2),
    accuracy          numeric(5,2),
    correct_words     int,
    incorrect_words   int,
    total_words_read  int,              -- D1: denominator Accuracy
    reading_time_sec  numeric(6,2),

    -- ComprehensionResult (F-07)
    retrieve          numeric(5,2),
    interpret         numeric(5,2),
    reflect           numeric(5,2),

    -- Adaptive decision (F-08)
    status            text check (status in ('INTERVENE','STAY','PROMOTION_CANDIDATE','PROMOTE')),
    recommendation    text,
    next_reading_level smallint check (next_reading_level between 1 and 3),
    rules_fired       jsonb default '[]'::jsonb,     -- traceability
    previous_wcpm     numeric(6,2),                  -- D3
    previous_accuracy numeric(5,2),                  -- D3
    consecutive_drops int default 0,                 -- D3
    season            text check (season in ('fall','winter','spring')),  -- D2

    -- Framework audit (1A.7)
    framework_result  jsonb,            -- JSON audit lengkap dari framework
    is_demo_fallback  boolean not null default false,

    -- Metadata
    transcript        text,             -- raw_text (immutable)
    audio_url         text,
    session_state     text not null default 'DRAFT'
                      check (session_state in ('DRAFT','RECORDING','PROCESSING','COMPREHENSION','COMPLETED')),
    created_at        timestamptz default now(),
    completed_at      timestamptz
);

-- ---------- WORD SCORES (1B) ----------
-- Hanya correct/incorrect dari alignment. TIDAK ada error type di ringkasan.
-- Label operasi (match/substitution/deletion/insertion) hanya di framework_result JSON.
create table if not exists word_scores (
    id              bigserial primary key,
    assessment_id   uuid not null references assessments(id) on delete cascade,
    position        int not null,
    reference_word  text,
    transcript_word text,
    confidence      numeric(4,3),       -- model_probability dari framework (bisa null)
    attempted       boolean not null,   -- D1
    is_correct      boolean not null,
    is_proper_noun  boolean not null default false,
    reason          text,               -- D10: traceability
    review_reasons  jsonb default '[]'::jsonb,  -- dari framework
    ts_start        numeric(8,3),
    ts_end          numeric(8,3)
);

-- ---------- INDEX ----------
create index if not exists idx_students_class on students(class_id);
create index if not exists idx_students_teacher on students(teacher_id);        -- D3
create index if not exists idx_assessments_student on assessments(student_id);
create index if not exists idx_assessments_teacher on assessments(teacher_id);  -- D3
create index if not exists idx_assessments_created on assessments(student_id, created_at);
create index if not exists idx_word_scores_assessment on word_scores(assessment_id);

-- Unique (assessment_id, position): dasar idempotensi word_scores (integrasi #3, B.2).
create unique index if not exists uq_word_scores_assessment_position
    on word_scores(assessment_id, position);

-- ============================================================
-- INTEGRASI #3 — Migrasi & kebijakan produksi
-- ============================================================

-- ---------- updated_at otomatis (D.2) ----------
create or replace function set_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

drop trigger if exists trg_reading_texts_updated_at on reading_texts;
create trigger trg_reading_texts_updated_at
    before update on reading_texts
    for each row execute function set_updated_at();

-- ---------- updated_at tabel mutable (integrasi #5, D1) ----------
-- Sebelumnya hanya reading_texts yang punya updated_at. Tambahkan ke tabel yang
-- sering di-update agar ada jejak "kapan baris terakhir berubah" (assessments
-- paling krusial: status/session_state berubah beberapa kali). Idempotent.
alter table assessments add column if not exists updated_at timestamptz default now();
alter table students    add column if not exists updated_at timestamptz default now();
alter table classes     add column if not exists updated_at timestamptz default now();
alter table users       add column if not exists updated_at timestamptz default now();

-- Trigger memakai fungsi set_updated_at() yang sudah ada. `before update` (tanpa
-- kolom spesifik) → ikut ter-trigger pada update kolom apa pun, termasuk saat
-- trigger teacher_id mengubah new.teacher_id. Tidak bentrok: set_updated_at hanya
-- menyentuh updated_at; trigger teacher_id hanya menyentuh teacher_id.
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

-- ---------- CHECK constraint (integrasi #6, D3) — defense in depth ----------
-- DB ikut menjaga invarian, bukan hanya kode Python. Semua constraint
-- `drop if exists` + `add` agar idempotent. `null` SELALU diizinkan (null != 0).
-- Bila DB sudah berisi data, terapkan via migrations/integration_6.sql dengan
-- urutan aman (NOT VALID → bersihkan → validate); blok ini untuk DB baru.

-- Nilai penilaian: cegah >100%, negatif, atau confidence >1.
alter table assessments drop constraint if exists ck_assess_wcpm;
alter table assessments add constraint ck_assess_wcpm
    check (wcpm is null or wcpm >= 0);
alter table assessments drop constraint if exists ck_assess_accuracy;
alter table assessments add constraint ck_assess_accuracy
    check (accuracy is null or accuracy between 0 and 100);
alter table assessments drop constraint if exists ck_assess_retrieve;
alter table assessments add constraint ck_assess_retrieve
    check (retrieve is null or retrieve between 0 and 100);
alter table assessments drop constraint if exists ck_assess_interpret;
alter table assessments add constraint ck_assess_interpret
    check (interpret is null or interpret between 0 and 100);
alter table assessments drop constraint if exists ck_assess_reflect;
alter table assessments add constraint ck_assess_reflect
    check (reflect is null or reflect between 0 and 100);
alter table assessments drop constraint if exists ck_assess_time;
alter table assessments add constraint ck_assess_time
    check (completed_at is null or completed_at >= created_at);
alter table assessments drop constraint if exists ck_assess_consec_drops;
alter table assessments add constraint ck_assess_consec_drops
    check (consecutive_drops is null or consecutive_drops >= 0);
alter table assessments drop constraint if exists ck_assess_rules_fired;
alter table assessments add constraint ck_assess_rules_fired
    check (jsonb_typeof(rules_fired) = 'array');
alter table assessments drop constraint if exists ck_assess_framework;
alter table assessments add constraint ck_assess_framework
    check (framework_result is null or jsonb_typeof(framework_result) = 'object');
alter table assessments drop constraint if exists ck_assess_previous_wcpm;
alter table assessments add constraint ck_assess_previous_wcpm
    check (previous_wcpm is null or previous_wcpm >= 0);
alter table assessments drop constraint if exists ck_assess_previous_accuracy;
alter table assessments add constraint ck_assess_previous_accuracy
    check (previous_accuracy is null or previous_accuracy between 0 and 100);

alter table word_scores drop constraint if exists ck_ws_position;
alter table word_scores add constraint ck_ws_position check (position >= 0);
alter table word_scores drop constraint if exists ck_ws_conf;
alter table word_scores add constraint ck_ws_conf
    check (confidence is null or confidence between 0 and 1);
alter table word_scores drop constraint if exists ck_ws_review;
alter table word_scores add constraint ck_ws_review
    check (jsonb_typeof(review_reasons) = 'array');

alter table reading_texts drop constraint if exists ck_rt_proper_nouns;
alter table reading_texts add constraint ck_rt_proper_nouns
    check (jsonb_typeof(proper_nouns) = 'array');

alter table reading_questions drop constraint if exists ck_rq_options;
alter table reading_questions add constraint ck_rq_options
    check (jsonb_typeof(options) = 'object' or jsonb_typeof(options) = 'array');

-- FK reading_id: kebijakan eksplisit (RESTRICT = cegah hapus teks yang punya asesmen).
alter table assessments drop constraint if exists assessments_reading_id_fkey;
alter table assessments add constraint assessments_reading_id_fkey
    foreign key (reading_id) references reading_texts(id) on delete restrict;

-- ---------- Guard konsistensi teacher_id (D6, aturan #3) ----------
-- teacher_id di students/assessments adalah denormalisasi. Trigger memaksa nilainya
-- selalu mengikuti sumber kebenaran (classes→students→assessments) pada INSERT/UPDATE,
-- sehingga tidak bisa "melenceng" bila class_id/student_id diubah.
create or replace function enforce_student_teacher()
returns trigger as $$
begin
    select c.teacher_id into new.teacher_id
    from classes c where c.id = new.class_id;
    return new;
end;
$$ language plpgsql;

drop trigger if exists trg_students_teacher on students;
create trigger trg_students_teacher
    before insert or update of class_id, teacher_id on students
    for each row execute function enforce_student_teacher();

create or replace function enforce_assessment_teacher()
returns trigger as $$
begin
    select s.teacher_id into new.teacher_id
    from students s where s.id = new.student_id;
    return new;
end;
$$ language plpgsql;

drop trigger if exists trg_assessments_teacher on assessments;
create trigger trg_assessments_teacher
    before insert or update of student_id, teacher_id on assessments
    for each row execute function enforce_assessment_teacher();

-- ---------- RPC atomik: ganti word_scores (B.2) ----------
-- Menghindari jendela delete-then-insert yang bisa menghapus data bila gagal.
-- security definer: berjalan sebagai owner (bypass RLS) agar klien anon guru dapat
-- memanggilnya; namun WAJIB memverifikasi kepemilikan assessment (auth.uid()).
create or replace function replace_word_scores(p_assessment_id uuid, p_rows jsonb)
returns void as $$
declare
    v_owner uuid;
begin
    -- Verifikasi kepemilikan (D1 hybrid: jangan sampai lintas-guru).
    select teacher_id into v_owner from assessments where id = p_assessment_id;
    if v_owner is distinct from auth.uid() then
        raise exception 'assessment % bukan milik pengguna', p_assessment_id
            using errcode = '42501';  -- insufficient_privilege
    end if;

    delete from word_scores where assessment_id = p_assessment_id;
    insert into word_scores (
        assessment_id, position, reference_word, transcript_word, confidence,
        attempted, is_correct, is_proper_noun, reason, review_reasons, ts_start, ts_end
    )
    select
        p_assessment_id,
        (r->>'position')::int,
        r->>'reference_word',
        r->>'transcript_word',
        (r->>'confidence')::numeric,
        (r->>'attempted')::boolean,
        (r->>'is_correct')::boolean,
        coalesce((r->>'is_proper_noun')::boolean, false),
        r->>'reason',
        coalesce(r->'review_reasons', '[]'::jsonb),
        (r->>'ts_start')::numeric,
        (r->>'ts_end')::numeric
    from jsonb_array_elements(coalesce(p_rows, '[]'::jsonb)) as r;
end;
$$ language plpgsql security definer;

-- ---------- ROW LEVEL SECURITY (A.4) ----------
-- D1 hybrid: jalur guru memakai anon key + RLS; admin/seed memakai service-role
-- (bypass RLS). D5: reading_texts/reading_questions = global read-only untuk guru.
alter table users            enable row level security;
alter table classes          enable row level security;
alter table students         enable row level security;
alter table assessments      enable row level security;
alter table word_scores      enable row level security;
alter table reading_texts    enable row level security;
alter table reading_questions enable row level security;

-- users: hanya diri sendiri.
drop policy if exists users_self_select on users;
create policy users_self_select on users
    for select using (id = auth.uid());
drop policy if exists users_self_update on users;
create policy users_self_update on users
    for update using (id = auth.uid()) with check (id = auth.uid());
-- Integrasi #6 (fix login): guru membuat baris profilnya SENDIRI saat login
-- (`_sync_public_user` meng-upsert public.users dengan id = auth.uid()). Tanpa policy
-- INSERT, login guru selalu 503. Upsert PostgREST = INSERT ... ON CONFLICT → butuh ini.
drop policy if exists users_self_insert on users;
create policy users_self_insert on users
    for insert with check (id = auth.uid());

-- classes: milik guru (teacher_id = auth.uid()).
drop policy if exists classes_owner_all on classes;
create policy classes_owner_all on classes
    for all using (teacher_id = auth.uid()) with check (teacher_id = auth.uid());

-- students: milik guru (D3: teacher_id eksplisit).
drop policy if exists students_owner_all on students;
create policy students_owner_all on students
    for all using (teacher_id = auth.uid()) with check (teacher_id = auth.uid());

-- assessments: milik guru (D3: teacher_id eksplisit).
drop policy if exists assessments_owner_all on assessments;
create policy assessments_owner_all on assessments
    for all using (teacher_id = auth.uid()) with check (teacher_id = auth.uid());

-- word_scores: lewat assessment milik guru.
drop policy if exists word_scores_owner_all on word_scores;
create policy word_scores_owner_all on word_scores
    for all using (
        assessment_id in (select id from assessments where teacher_id = auth.uid())
    ) with check (
        assessment_id in (select id from assessments where teacher_id = auth.uid())
    );

-- reading_texts: global read-only untuk guru terautentikasi (D5). Tulis = service-role.
drop policy if exists reading_texts_read_authenticated on reading_texts;
create policy reading_texts_read_authenticated on reading_texts
    for select to authenticated using (true);

drop policy if exists reading_questions_read_authenticated on reading_questions;
create policy reading_questions_read_authenticated on reading_questions
    for select to authenticated using (true);

-- ---------- Supabase Storage: audio siswa (integrasi #4, D2 / B.4) ----------
-- Bucket PRIVATE untuk rekaman siswa (data sensitif). Path: {teacher_id}/{assessment_id}/...
-- Dibuat idempotent. Policy ber-scope guru via prefix folder = auth.uid().
insert into storage.buckets (id, name, public)
values ('reading-audio', 'reading-audio', false)
on conflict (id) do nothing;

-- Guru hanya dapat membaca objek di folder miliknya (prefix = auth.uid()).
drop policy if exists reading_audio_owner_select on storage.objects;
create policy reading_audio_owner_select on storage.objects
    for select to authenticated
    using (
        bucket_id = 'reading-audio'
        and (storage.foldername(name))[1] = auth.uid()::text
    );

-- Guru hanya dapat menulis objek di folder miliknya.
drop policy if exists reading_audio_owner_insert on storage.objects;
create policy reading_audio_owner_insert on storage.objects
    for insert to authenticated
    with check (
        bucket_id = 'reading-audio'
        and (storage.foldername(name))[1] = auth.uid()::text
    );

-- Guru hanya dapat MENIMPA (upsert) objek di folder miliknya. Integrasi #6 (fix 502):
-- signed upload URL dibuat dengan `upsert=true` (retry/rekam ulang). Saat objek SUDAH
-- ada, Supabase Storage melakukan UPDATE → butuh policy UPDATE, bukan hanya INSERT.
-- Tanpa ini, unggah ulang path yang sama → 403 RLS → endpoint `upload-url` 502.
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

-- ---------- Retensi audio: log penghapusan (integrasi #5, D2) ----------
-- Menyimpan STATUS penghapusan (bukan URL/path/data sensitif). Tanpa FK: baris
-- asesmen boleh tetap ada (hasil penilaian dipertahankan tanpa audio).
create table if not exists audio_purge_log (
    id            bigserial primary key,
    assessment_id uuid not null,
    purged_at     timestamptz not null default now(),
    status        text not null check (status in ('PURGED','FAILED','SKIPPED')),
    attempts      smallint not null default 0,
    note          text
);
alter table audio_purge_log enable row level security;
-- Tidak ada policy untuk guru: hanya service-role (admin/seed) yang boleh akses
-- (bypass RLS). Ini mencegah guru melihat/​mengubah log pembersihan.

-- Index untuk prune (query per-asesmen) — integrasi #6, C.3.
create index if not exists idx_audio_purge_assessment on audio_purge_log(assessment_id);

-- ---------- Pendaftaran mandiri: tantangan OTP (integrasi #7) ----------
-- Menyimpan HANYA hash kode verifikasi email, bukan kode mentahnya. `name` ditahan
-- dari langkah 1 dan baru dipakai saat akun benar-benar dibuat di langkah 3.
-- Lihat migrations/integration_7.sql dan services/signup_otp.py.
create table if not exists signup_otp (
    id          uuid primary key default gen_random_uuid(),
    email       text not null,
    code_hash   text not null,          -- hanya HMAC; kode mentah TIDAK PERNAH disimpan
    name        text,
    attempts    smallint not null default 0,
    consumed_at timestamptz,            -- terisi = kode sudah terpakai / dibatalkan
    expires_at  timestamptz not null,
    created_at  timestamptz not null default now(),
    request_ip  text
);
create index if not exists idx_signup_otp_email on signup_otp(email, created_at desc);
alter table signup_otp enable row level security;
-- Sama seperti audio_purge_log: sengaja TANPA policy. Hanya service-role (backend)
-- yang boleh menyentuh; anon/authenticated tidak melihat apa pun.

-- ---------- VIEW: Student Profile terbaru ----------
create or replace view student_latest_profile as
select distinct on (a.student_id)
    a.student_id,
    a.wcpm            as current_wcpm,
    a.accuracy,
    a.correct_words,
    a.incorrect_words,
    a.total_words_read,
    a.retrieve,
    a.interpret,
    a.reflect,
    a.reading_level   as current_text_complexity,
    a.status,
    a.recommendation,
    a.created_at
from assessments a
where a.session_state = 'COMPLETED'
order by a.student_id, a.created_at desc;

-- ---------- SEED contoh (lengkap via backend/seed/) ----------
-- Jalankan backend/seed/validate.py untuk validasi, lalu load via aplikasi.
