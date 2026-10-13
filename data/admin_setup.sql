-- Run in Supabase SQL Editor AFTER creating an admin user in Authentication > Users.
-- Replace the UUID in the LAST INSERT with your own Supabase Auth user's UUID.
create table if not exists public.admin_users (user_id uuid primary key references auth.users(id) on delete cascade);
revoke all on public.admin_users from anon, authenticated;
create table if not exists public.competition_settings (id boolean primary key default true check(id), submissions_open boolean not null default true);
insert into public.competition_settings(id,submissions_open) values(true,true) on conflict(id) do nothing;
alter table public.competition_settings enable row level security;
revoke all on public.competition_settings from anon, authenticated;
create policy "Read submission status" on public.competition_settings for select to anon,authenticated using(true);
grant select on public.competition_settings to anon,authenticated;
create table if not exists public.admin_actions (
 id bigint generated always as identity primary key,
 action text not null check(action in ('edit_team','delete_team','score_override')),
 payload jsonb not null,
 created_at timestamptz not null default now()
);
alter table public.admin_actions enable row level security;
revoke all on public.admin_actions from anon,authenticated;
-- Submission lock is checked in the database, not only in browser JavaScript.
create or replace function public.enforce_submission_open() returns trigger language plpgsql security definer set search_path = '' as $$
begin
 if not coalesce((select submissions_open from public.competition_settings where id=true),false) then
  raise exception 'Team submissions are closed';
 end if;
 return new;
end $$;
drop trigger if exists submissions_open_guard on public.submissions;
create trigger submissions_open_guard before insert on public.submissions for each row execute function public.enforce_submission_open();
-- Admin-only API: checks the signed-in Supabase Auth user ID on every call.
create or replace function public.admin_command(p_action text, p_payload jsonb default '{}'::jsonb)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare v_id bigint;
begin
 if auth.uid() is null or not exists(select 1 from public.admin_users where user_id=auth.uid()) then
  raise exception 'Administrator access required' using errcode='42501';
 end if;
 if p_action='status' then
  return jsonb_build_object('submissions_open',(select submissions_open from public.competition_settings where id=true));
 elsif p_action='set_open' then
  if jsonb_typeof(p_payload->'open') is distinct from 'boolean' then raise exception 'Expected boolean open'; end if;
  update public.competition_settings set submissions_open=(p_payload->>'open')::boolean where id=true;
  return jsonb_build_object('ok',true);
 elsif p_action in ('edit_team','delete_team','score_override') then
  if p_action in ('edit_team','delete_team') and coalesce(length(p_payload->>'id'),0)=0 then raise exception 'Missing team ID'; end if;
  if p_action='edit_team' and (length(trim(coalesce(p_payload->>'name',''))) not between 1 and 60 or length(trim(coalesce(p_payload->>'owner',''))) not between 1 and 60 or jsonb_typeof(p_payload->'picks') is distinct from 'array' or jsonb_array_length(p_payload->'picks')<>8) then raise exception 'Invalid team edit'; end if;
  if p_action='score_override' and (coalesce(length(p_payload->>'playerId'),0)=0 or jsonb_typeof(p_payload->'adjustment') is distinct from 'number' or abs((p_payload->>'adjustment')::numeric)>100000) then raise exception 'Invalid score correction'; end if;
  insert into public.admin_actions(action,payload) values(p_action,p_payload) returning id into v_id;
  return jsonb_build_object('ok',true,'queued_id',v_id);
 else raise exception 'Unknown action'; end if;
end $$;
revoke all on function public.admin_command(text,jsonb) from public,anon;
grant execute on function public.admin_command(text,jsonb) to authenticated;
-- IMPORTANT: Replace this placeholder with the UUID of YOUR Auth user, not an email address.
-- insert into public.admin_users(user_id) values ('YOUR-AUTH-USER-UUID');
