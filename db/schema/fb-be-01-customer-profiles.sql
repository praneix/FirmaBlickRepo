-- Additive, Frankfurt-staging-only customer profile foundation.
-- Do not apply until staging auth settings and current grants have been verified.
begin;

create table public.fb_customer_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade default auth.uid(),
  full_name text not null check (
    full_name = btrim(full_name)
    and char_length(full_name) between 1 and 160
  ),
  company_name text not null check (
    company_name = btrim(company_name)
    and char_length(company_name) between 1 and 160
  ),
  country text not null check (country ~ '^[A-Z]{2}$'),
  preferred_language text not null default 'en'
    check (preferred_language in ('en', 'de')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.fb_customer_profiles enable row level security;

create policy fb_customer_profiles_select_own
  on public.fb_customer_profiles
  for select
  to authenticated
  using (auth.uid() = user_id);

create policy fb_customer_profiles_insert_own
  on public.fb_customer_profiles
  for insert
  to authenticated
  with check (auth.uid() = user_id);

create policy fb_customer_profiles_update_own
  on public.fb_customer_profiles
  for update
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create function public.fb_customer_profiles_protect_identity()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if new.user_id is distinct from old.user_id then
    raise exception 'CUSTOMER_PROFILE_OWNER_IMMUTABLE' using errcode = 'P0001';
  end if;
  new.updated_at := statement_timestamp();
  return new;
end;
$$;

create trigger fb_customer_profiles_protect_identity
  before update on public.fb_customer_profiles
  for each row execute function public.fb_customer_profiles_protect_identity();

revoke all on public.fb_customer_profiles from public, anon, authenticated;
grant select on public.fb_customer_profiles to authenticated;
grant insert (user_id, full_name, company_name, country, preferred_language)
  on public.fb_customer_profiles to authenticated;
grant update (full_name, company_name, country, preferred_language)
  on public.fb_customer_profiles to authenticated;
revoke all on function public.fb_customer_profiles_protect_identity()
  from public, anon, authenticated;

commit;
