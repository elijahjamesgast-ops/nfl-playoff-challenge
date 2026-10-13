-- Run in Supabase SQL editor. Public may INSERT only; no public SELECT/UPDATE/DELETE.
create table if not exists public.submissions (
 id uuid primary key default gen_random_uuid(),
 name text not null check (length(trim(name)) between 1 and 60),
 owner text not null check (length(trim(owner)) between 1 and 60),
 picks jsonb not null check (jsonb_typeof(picks) = 'array' and jsonb_array_length(picks) = 8),
 created_at timestamptz not null default now()
);
alter table public.submissions enable row level security;
revoke all on public.submissions from anon, authenticated;
grant insert on public.submissions to anon, authenticated;
drop policy if exists "Anyone can submit" on public.submissions;
create policy "Anyone can submit" on public.submissions for insert to anon, authenticated with check (true);
-- Security: client-side roster checks are for convenience only. A privileged sync validates
-- picks against data/players.xml and rules.xml before publishing.
