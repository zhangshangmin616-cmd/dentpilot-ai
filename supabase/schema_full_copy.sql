create extension if not exists pgcrypto;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text,
  display_name text,
  role text default 'student',
  plan text default 'beta',
  created_at timestamptz default now()
);

create table if not exists public.study_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  mode text,
  subject text,
  topic text,
  course_context text,
  created_at timestamptz default now()
);

create table if not exists public.study_pack_records (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  subject text,
  source_title text,
  source_text text,
  generated_pack jsonb,
  markdown_export text,
  created_at timestamptz default now()
);

create table if not exists public.written_exam_attempts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  session_id uuid references public.study_sessions(id) on delete set null,
  topic text,
  subject text,
  difficulty text,
  course_context text,
  question text,
  student_answer text,
  model_answer text,
  score numeric,
  feedback text,
  covered_points jsonb default '[]'::jsonb,
  missing_points jsonb default '[]'::jsonb,
  created_at timestamptz default now()
);

create table if not exists public.oral_exam_attempts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  session_id uuid references public.study_sessions(id) on delete set null,
  question text,
  student_answer text,
  score numeric,
  covered_points jsonb default '[]'::jsonb,
  missing_points jsonb default '[]'::jsonb,
  feedback text,
  topic text,
  subject text,
  difficulty text,
  created_at timestamptz default now()
);

create table if not exists public.clinical_case_attempts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  case_title text,
  case_data jsonb,
  student_answer text,
  score numeric,
  diagnosis_score numeric,
  treatment_score numeric,
  missing_points jsonb default '[]'::jsonb,
  feedback text,
  created_at timestamptz default now()
);

create table if not exists public.user_weaknesses (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  subject text,
  topic text,
  weakness_type text,
  score_avg numeric,
  attempt_count integer default 0,
  last_seen_at timestamptz default now()
);

create table if not exists public.usage_limits (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  date date default current_date,
  voice_minutes_used numeric default 0,
  text_exam_count integer default 0,
  study_pack_count integer default 0,
  case_count integer default 0,
  unique (user_id, date)
);

create index if not exists idx_study_sessions_user_id on public.study_sessions (user_id);
create index if not exists idx_study_sessions_created_at on public.study_sessions (created_at desc);

create index if not exists idx_study_pack_records_user_id on public.study_pack_records (user_id);
create index if not exists idx_study_pack_records_created_at on public.study_pack_records (created_at desc);

create index if not exists idx_written_exam_attempts_user_id on public.written_exam_attempts (user_id);
create index if not exists idx_written_exam_attempts_created_at on public.written_exam_attempts (created_at desc);

create index if not exists idx_oral_exam_attempts_user_id on public.oral_exam_attempts (user_id);
create index if not exists idx_oral_exam_attempts_created_at on public.oral_exam_attempts (created_at desc);

create index if not exists idx_clinical_case_attempts_user_id on public.clinical_case_attempts (user_id);
create index if not exists idx_clinical_case_attempts_created_at on public.clinical_case_attempts (created_at desc);

create index if not exists idx_user_weaknesses_user_id on public.user_weaknesses (user_id);
create index if not exists idx_user_weaknesses_last_seen_at on public.user_weaknesses (last_seen_at desc);

create index if not exists idx_usage_limits_user_id on public.usage_limits (user_id);
create index if not exists idx_usage_limits_user_id_date on public.usage_limits (user_id, date);

alter table public.profiles enable row level security;
alter table public.study_sessions enable row level security;
alter table public.study_pack_records enable row level security;
alter table public.written_exam_attempts enable row level security;
alter table public.oral_exam_attempts enable row level security;
alter table public.clinical_case_attempts enable row level security;
alter table public.user_weaknesses enable row level security;
alter table public.usage_limits enable row level security;

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, email)
  values (new.id, new.email)
  on conflict (id) do update set email = excluded.email;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute function public.handle_new_user();

drop policy if exists "profiles_select_own" on public.profiles;
create policy "profiles_select_own"
on public.profiles for select
using (auth.uid() = id);

drop policy if exists "profiles_insert_own" on public.profiles;
create policy "profiles_insert_own"
on public.profiles for insert
with check (auth.uid() = id);

drop policy if exists "profiles_update_own" on public.profiles;
create policy "profiles_update_own"
on public.profiles for update
using (auth.uid() = id)
with check (auth.uid() = id);

drop policy if exists "profiles_delete_own" on public.profiles;
create policy "profiles_delete_own"
on public.profiles for delete
using (auth.uid() = id);

drop policy if exists "study_sessions_select_own" on public.study_sessions;
create policy "study_sessions_select_own"
on public.study_sessions for select
using (auth.uid() = user_id);

drop policy if exists "study_sessions_insert_own" on public.study_sessions;
create policy "study_sessions_insert_own"
on public.study_sessions for insert
with check (auth.uid() = user_id);

drop policy if exists "study_sessions_update_own" on public.study_sessions;
create policy "study_sessions_update_own"
on public.study_sessions for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists "study_sessions_delete_own" on public.study_sessions;
create policy "study_sessions_delete_own"
on public.study_sessions for delete
using (auth.uid() = user_id);

drop policy if exists "study_pack_records_select_own" on public.study_pack_records;
create policy "study_pack_records_select_own"
on public.study_pack_records for select
using (auth.uid() = user_id);

drop policy if exists "study_pack_records_insert_own" on public.study_pack_records;
create policy "study_pack_records_insert_own"
on public.study_pack_records for insert
with check (auth.uid() = user_id);

drop policy if exists "study_pack_records_update_own" on public.study_pack_records;
create policy "study_pack_records_update_own"
on public.study_pack_records for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists "study_pack_records_delete_own" on public.study_pack_records;
create policy "study_pack_records_delete_own"
on public.study_pack_records for delete
using (auth.uid() = user_id);

drop policy if exists "written_exam_attempts_select_own" on public.written_exam_attempts;
create policy "written_exam_attempts_select_own"
on public.written_exam_attempts for select
using (auth.uid() = user_id);

drop policy if exists "written_exam_attempts_insert_own" on public.written_exam_attempts;
create policy "written_exam_attempts_insert_own"
on public.written_exam_attempts for insert
with check (auth.uid() = user_id);

drop policy if exists "written_exam_attempts_update_own" on public.written_exam_attempts;
create policy "written_exam_attempts_update_own"
on public.written_exam_attempts for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists "written_exam_attempts_delete_own" on public.written_exam_attempts;
create policy "written_exam_attempts_delete_own"
on public.written_exam_attempts for delete
using (auth.uid() = user_id);

drop policy if exists "oral_exam_attempts_select_own" on public.oral_exam_attempts;
create policy "oral_exam_attempts_select_own"
on public.oral_exam_attempts for select
using (auth.uid() = user_id);

drop policy if exists "oral_exam_attempts_insert_own" on public.oral_exam_attempts;
create policy "oral_exam_attempts_insert_own"
on public.oral_exam_attempts for insert
with check (auth.uid() = user_id);

drop policy if exists "oral_exam_attempts_update_own" on public.oral_exam_attempts;
create policy "oral_exam_attempts_update_own"
on public.oral_exam_attempts for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists "oral_exam_attempts_delete_own" on public.oral_exam_attempts;
create policy "oral_exam_attempts_delete_own"
on public.oral_exam_attempts for delete
using (auth.uid() = user_id);

drop policy if exists "clinical_case_attempts_select_own" on public.clinical_case_attempts;
create policy "clinical_case_attempts_select_own"
on public.clinical_case_attempts for select
using (auth.uid() = user_id);

drop policy if exists "clinical_case_attempts_insert_own" on public.clinical_case_attempts;
create policy "clinical_case_attempts_insert_own"
on public.clinical_case_attempts for insert
with check (auth.uid() = user_id);

drop policy if exists "clinical_case_attempts_update_own" on public.clinical_case_attempts;
create policy "clinical_case_attempts_update_own"
on public.clinical_case_attempts for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists "clinical_case_attempts_delete_own" on public.clinical_case_attempts;
create policy "clinical_case_attempts_delete_own"
on public.clinical_case_attempts for delete
using (auth.uid() = user_id);

drop policy if exists "user_weaknesses_select_own" on public.user_weaknesses;
create policy "user_weaknesses_select_own"
on public.user_weaknesses for select
using (auth.uid() = user_id);

drop policy if exists "user_weaknesses_insert_own" on public.user_weaknesses;
create policy "user_weaknesses_insert_own"
on public.user_weaknesses for insert
with check (auth.uid() = user_id);

drop policy if exists "user_weaknesses_update_own" on public.user_weaknesses;
create policy "user_weaknesses_update_own"
on public.user_weaknesses for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists "user_weaknesses_delete_own" on public.user_weaknesses;
create policy "user_weaknesses_delete_own"
on public.user_weaknesses for delete
using (auth.uid() = user_id);

drop policy if exists "usage_limits_select_own" on public.usage_limits;
create policy "usage_limits_select_own"
on public.usage_limits for select
using (auth.uid() = user_id);

drop policy if exists "usage_limits_insert_own" on public.usage_limits;
create policy "usage_limits_insert_own"
on public.usage_limits for insert
with check (auth.uid() = user_id);

drop policy if exists "usage_limits_update_own" on public.usage_limits;
create policy "usage_limits_update_own"
on public.usage_limits for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists "usage_limits_delete_own" on public.usage_limits;
create policy "usage_limits_delete_own"
on public.usage_limits for delete
using (auth.uid() = user_id);

notify pgrst, 'reload schema';
