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
create policy "profiles_select_own" on public.profiles
for select using (id = auth.uid());

drop policy if exists "profiles_insert_own" on public.profiles;
create policy "profiles_insert_own" on public.profiles
for insert with check (id = auth.uid());

drop policy if exists "profiles_update_own" on public.profiles;
create policy "profiles_update_own" on public.profiles
for update using (id = auth.uid()) with check (id = auth.uid());

drop policy if exists "profiles_delete_own" on public.profiles;
create policy "profiles_delete_own" on public.profiles
for delete using (id = auth.uid());

drop policy if exists "study_sessions_all_own" on public.study_sessions;
create policy "study_sessions_all_own" on public.study_sessions
for all using (user_id = auth.uid()) with check (user_id = auth.uid());

drop policy if exists "study_pack_records_all_own" on public.study_pack_records;
create policy "study_pack_records_all_own" on public.study_pack_records
for all using (user_id = auth.uid()) with check (user_id = auth.uid());

drop policy if exists "written_exam_attempts_all_own" on public.written_exam_attempts;
create policy "written_exam_attempts_all_own" on public.written_exam_attempts
for all using (user_id = auth.uid()) with check (user_id = auth.uid());

drop policy if exists "oral_exam_attempts_all_own" on public.oral_exam_attempts;
create policy "oral_exam_attempts_all_own" on public.oral_exam_attempts
for all using (user_id = auth.uid()) with check (user_id = auth.uid());

drop policy if exists "clinical_case_attempts_all_own" on public.clinical_case_attempts;
create policy "clinical_case_attempts_all_own" on public.clinical_case_attempts
for all using (user_id = auth.uid()) with check (user_id = auth.uid());

drop policy if exists "user_weaknesses_all_own" on public.user_weaknesses;
create policy "user_weaknesses_all_own" on public.user_weaknesses
for all using (user_id = auth.uid()) with check (user_id = auth.uid());

drop policy if exists "usage_limits_all_own" on public.usage_limits;
create policy "usage_limits_all_own" on public.usage_limits
for all using (user_id = auth.uid()) with check (user_id = auth.uid());
