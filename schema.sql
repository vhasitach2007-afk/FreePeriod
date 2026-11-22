-- Run this entire script in Supabase SQL Editor.
create extension if not exists pgcrypto;

create table if not exists public.profiles (
    id uuid primary key references auth.users(id) on delete cascade,
    full_name text not null default '',
    role text not null default 'student' check (role in ('student','faculty'))
);

create table if not exists public.classrooms (
    id uuid primary key default gen_random_uuid(),
    room_number text not null,
    block text not null,
    floor text,
    capacity integer not null default 40 check (capacity > 0),
    projector boolean not null default false,
    smartboard boolean not null default false,
    ac boolean not null default false,
    notes text,
    created_at timestamptz not null default now(),
    unique(room_number, block)
);

create table if not exists public.timetable (
    id uuid primary key default gen_random_uuid(),
    room_id uuid not null references public.classrooms(id) on delete cascade,
    class_date date not null,
    start_time time not null,
    end_time time not null,
    subject text,
    faculty_name text,
    created_at timestamptz not null default now(),
    check (end_time > start_time),
    unique(room_id, class_date, start_time, end_time)
);

create index if not exists timetable_date_idx on public.timetable(class_date);
create index if not exists timetable_room_date_idx on public.timetable(room_id, class_date);

-- Automatically create a student profile after signup.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id, full_name, role)
  values (
    new.id,
    coalesce(new.raw_user_meta_data ->> 'full_name', ''),
    'student'
  );
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute procedure public.handle_new_user();

alter table public.profiles enable row level security;
alter table public.classrooms enable row level security;
alter table public.timetable enable row level security;

-- Users can read their own profile.
create policy "Users read own profile"
on public.profiles for select
to authenticated
using (auth.uid() = id);

-- Faculty can update their own profile only for non-role fields.
-- Role changes should be performed by an administrator in Supabase.
create policy "Users update own name"
on public.profiles for update
to authenticated
using (auth.uid() = id)
with check (auth.uid() = id);

-- All logged-in users can view classrooms and timetable.
create policy "Authenticated users read classrooms"
on public.classrooms for select to authenticated using (true);

create policy "Faculty insert classrooms"
on public.classrooms for insert to authenticated
with check (exists (
  select 1 from public.profiles p
  where p.id = auth.uid() and p.role = 'faculty'
));

create policy "Faculty update classrooms"
on public.classrooms for update to authenticated
using (exists (
  select 1 from public.profiles p
  where p.id = auth.uid() and p.role = 'faculty'
))
with check (exists (
  select 1 from public.profiles p
  where p.id = auth.uid() and p.role = 'faculty'
));

create policy "Faculty delete classrooms"
on public.classrooms for delete to authenticated
using (exists (
  select 1 from public.profiles p
  where p.id = auth.uid() and p.role = 'faculty'
));

create policy "Authenticated users read timetable"
on public.timetable for select to authenticated using (true);

create policy "Faculty insert timetable"
on public.timetable for insert to authenticated
with check (exists (
  select 1 from public.profiles p
  where p.id = auth.uid() and p.role = 'faculty'
));

create policy "Faculty update timetable"
on public.timetable for update to authenticated
using (exists (
  select 1 from public.profiles p
  where p.id = auth.uid() and p.role = 'faculty'
))
with check (exists (
  select 1 from public.profiles p
  where p.id = auth.uid() and p.role = 'faculty'
));

create policy "Faculty delete timetable"
on public.timetable for delete to authenticated
using (exists (
  select 1 from public.profiles p
  where p.id = auth.uid() and p.role = 'faculty'
));

-- IMPORTANT: After a faculty member registers, promote their profile manually:
-- update public.profiles set role = 'faculty'
-- where id = (select id from auth.users where email = 'faculty@college.edu');
