-- Nonproduction candidate. Apply only after review; no checkout activation.
begin;
create schema if not exists commercial;
revoke all on schema commercial from public, anon, authenticated;
create table commercial.price_version (
 price_key text not null check (price_key ~ '^[A-Za-z0-9:_-]+$'),
 version text not null,
 currency text not null check (currency = 'EUR'),
 amount_minor bigint not null check (amount_minor between 1 and 9007199254740991),
 effective_from timestamptz not null,
 effective_until timestamptz,
 approval_ref text not null check (length(trim(approval_ref)) > 0),
 recorded_at timestamptz not null default now(),
 recorded_by text not null default current_user,
 primary key(price_key,version),
 check(effective_until is null or effective_until > effective_from)
);
alter table commercial.price_version enable row level security;
revoke all on commercial.price_version from public, anon, authenticated, service_role;
-- Append-only versions; overlapping intervals are rejected at lookup, never resolved silently.
create function commercial.prevent_price_mutation() returns trigger language plpgsql
set search_path = pg_catalog as $$ begin raise exception 'Price versions are immutable'; end; $$;
create trigger price_immutable before update or delete on commercial.price_version
for each row execute function commercial.prevent_price_mutation();
create function public.fb_lookup_price(p_key text) returns table
(price_key text, version text, currency text, amount_minor bigint, approval_ref text)
language plpgsql stable security definer set search_path = pg_catalog as $$
declare n bigint;
begin
 select count(*) into n from commercial.price_version p
 where p.price_key=p_key and p.effective_from<=statement_timestamp()
 and (p.effective_until is null or p.effective_until>statement_timestamp());
 if n<>1 then raise exception 'Price unavailable or ambiguous'; end if;
 return query select p.price_key,p.version,p.currency,p.amount_minor,p.approval_ref
 from commercial.price_version p where p.price_key=p_key and p.effective_from<=statement_timestamp()
 and (p.effective_until is null or p.effective_until>statement_timestamp());
end; $$;
revoke all on function public.fb_lookup_price(text) from public, anon, authenticated;
grant execute on function public.fb_lookup_price(text) to service_role;
-- No seed until approved effective dates and version rollover policy are reconciled.
commit;
