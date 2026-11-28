-- Nonproduction candidate. Apply only after review; no checkout activation.
begin;
create schema if not exists commercial;
revoke all on schema commercial from public, anon, authenticated;
create extension if not exists btree_gist;
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
 check(effective_until is null or effective_until > effective_from),
 exclude using gist (price_key with =, tstzrange(effective_from,effective_until,'[)') with &&)
);
alter table commercial.price_version enable row level security;
revoke all on commercial.price_version from public, anon, authenticated, service_role;
-- Preserve price payloads; only a previously open interval may be closed by the owner.
create function commercial.prevent_price_mutation() returns trigger language plpgsql
set search_path = pg_catalog as $$ begin
 if TG_OP = 'UPDATE' then
  if old.effective_until is null and new.effective_until > old.effective_from
   and (to_jsonb(new) - 'effective_until') = (to_jsonb(old) - 'effective_until') then return new; end if;
 end if;
 raise exception 'Price versions are immutable';
end; $$;
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
-- Owner-only atomic rollover; no API role can execute or write directly.
create function commercial.rollover_price(p_key text,p_version text,p_amount bigint,p_from timestamptz,p_approval text) returns void
language plpgsql set search_path = pg_catalog as $$
begin
 if p_from is null or p_from < statement_timestamp() then raise exception 'Retroactive rollover forbidden'; end if;
 perform pg_advisory_xact_lock(hashtextextended(p_key,0));
 update commercial.price_version set effective_until=p_from where price_key=p_key and effective_until is null and effective_from<p_from;
 if not found then raise exception 'No open predecessor'; end if;
 insert into commercial.price_version(price_key,version,currency,amount_minor,effective_from,approval_ref) values(p_key,p_version,'EUR',p_amount,p_from,p_approval);
end; $$;
revoke all on function commercial.rollover_price(text,text,bigint,timestamptz,text) from public, anon, authenticated, service_role;
-- No seed until approved effective dates and SKU mapping are reconciled.
commit;
