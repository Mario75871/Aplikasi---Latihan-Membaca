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
create table if not exists students (
    id          uuid primary key default gen_random_uuid(),
    class_id    uuid references classes(id) on delete cascade,
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
create index if not exists idx_assessments_student on assessments(student_id);
create index if not exists idx_assessments_created on assessments(student_id, created_at);
create index if not exists idx_word_scores_assessment on word_scores(assessment_id);

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
