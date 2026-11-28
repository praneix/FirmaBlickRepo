-- Run only against an isolated staging test setup with two synthetic auth.users
-- that have no existing profile. Supply their UUIDs with psql variables user_a
-- and user_b. The transaction rolls all test profiles back.
\set ON_ERROR_STOP on
\if :{?user_a}
\else
\echo 'Set psql variable user_a to a synthetic auth.users UUID'
\quit 2
\endif
\if :{?user_b}
\else
\echo 'Set psql variable user_b to a different synthetic auth.users UUID'
\quit 2
\endif

begin;

select set_config('fb.test.user_a', :'user_a', true);
select set_config('fb.test.user_b', :'user_b', true);

do $$
begin
  if current_setting('fb.test.user_a')::uuid = current_setting('fb.test.user_b')::uuid then
    raise exception 'TEST_USERS_MUST_DIFFER';
  end if;
  if exists (
    select 1 from public.fb_customer_profiles
    where user_id in (
      current_setting('fb.test.user_a')::uuid,
      current_setting('fb.test.user_b')::uuid
    )
  ) then
    raise exception 'SYNTHETIC_TEST_USER_ALREADY_HAS_PROFILE';
  end if;
  if not (
    select relrowsecurity from pg_class
    where oid = 'public.fb_customer_profiles'::regclass
  ) then
    raise exception 'CUSTOMER_PROFILE_RLS_DISABLED';
  end if;
  if has_table_privilege('anon', 'public.fb_customer_profiles', 'SELECT')
     or has_table_privilege('anon', 'public.fb_customer_profiles', 'INSERT')
     or has_table_privilege('anon', 'public.fb_customer_profiles', 'UPDATE')
     or has_table_privilege('anon', 'public.fb_customer_profiles', 'DELETE') then
    raise exception 'ANONYMOUS_PROFILE_PRIVILEGE_GRANTED';
  end if;
  if has_table_privilege('authenticated', 'public.fb_customer_profiles', 'DELETE')
     or has_column_privilege(
       'authenticated', 'public.fb_customer_profiles', 'user_id', 'UPDATE'
     ) then
    raise exception 'UNNECESSARY_AUTHENTICATED_PROFILE_PRIVILEGE_GRANTED';
  end if;
  if (
    select count(*) from pg_policies
    where schemaname = 'public' and tablename = 'fb_customer_profiles'
  ) <> 3 or exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'fb_customer_profiles'
      and 'anon' = any(roles)
  ) then
    raise exception 'CUSTOMER_PROFILE_POLICY_INVENTORY_MISMATCH';
  end if;
end;
$$;

insert into public.fb_customer_profiles(user_id, full_name, company_name, country)
values (
  current_setting('fb.test.user_b')::uuid,
  'Synthetic User B',
  'Synthetic Company B',
  'DE'
);

set local role anon;
do $$
declare
  denied boolean := false;
begin
  begin
    perform * from public.fb_customer_profiles;
  exception when insufficient_privilege then
    denied := true;
  end;
  if not denied then
    raise exception 'ANONYMOUS_PROFILE_READ_SUCCEEDED';
  end if;
end;
$$;
reset role;

set local role authenticated;
select set_config('request.jwt.claim.sub', :'user_a', true);

do $$
declare
  visible_profiles integer;
  affected_rows integer;
begin
  select count(*) into visible_profiles from public.fb_customer_profiles;
  if visible_profiles <> 0 then
    raise exception 'CROSS_USER_PROFILE_SELECT_SUCCEEDED';
  end if;

  insert into public.fb_customer_profiles(full_name, company_name, country)
  values ('Synthetic User A', 'Synthetic Company A', 'DE');
  get diagnostics affected_rows = row_count;
  if affected_rows <> 1 then
    raise exception 'OWN_PROFILE_INSERT_FAILED';
  end if;

  select count(*) into visible_profiles from public.fb_customer_profiles;
  if visible_profiles <> 1 then
    raise exception 'CUSTOMER_PROFILE_SELECT_SCOPE_FAILED';
  end if;

  update public.fb_customer_profiles
  set full_name = 'Cross-user mutation'
  where user_id = current_setting('fb.test.user_b')::uuid;
  get diagnostics affected_rows = row_count;
  if affected_rows <> 0 then
    raise exception 'CROSS_USER_PROFILE_UPDATE_SUCCEEDED';
  end if;

  update public.fb_customer_profiles
  set full_name = 'Updated Synthetic User A'
  where user_id = auth.uid();
  get diagnostics affected_rows = row_count;
  if affected_rows <> 1 then
    raise exception 'OWN_PROFILE_UPDATE_FAILED';
  end if;

  begin
    update public.fb_customer_profiles
    set user_id = current_setting('fb.test.user_b')::uuid
    where user_id = auth.uid();
    raise exception 'CUSTOMER_PROFILE_OWNER_CHANGE_SUCCEEDED';
  exception
    when insufficient_privilege then null;
  end;
end;
$$;
reset role;

do $$
begin
  if (select full_name from public.fb_customer_profiles
      where user_id = current_setting('fb.test.user_a')::uuid)
     <> 'Updated Synthetic User A' then
    raise exception 'OWN_PROFILE_UPDATE_FAILED';
  end if;
end;
$$;

rollback;
