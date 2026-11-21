-- CV1-05 proposed FirmaBlick-only database schema.
-- Not applied to any connected Supabase project: only existing project is IIA.
-- Install into a new dedicated FirmaBlick project after account/cost approval.
-- All operational tables are closed to anon/authenticated (RLS + REVOKE).
-- NEVER store raw access tokens, payment card numbers or public full-report URLs.
begin;
create table if not exists public.fb_report_catalog (
 report_id text primary key,
 slug text not null unique,
 title text not null,
 audience text not null,
 thesis text not null,
 state text not null default 'draft' check (state in ('draft','review','approved','retired')),
 created_at timestamptz not null default now()
);
create table if not exists public.fb_report_versions (
 report_id text not null references public.fb_report_catalog(report_id),
 revision text not null,
 title text not null,
 source_vintages jsonb not null default '{}'::jsonb,
 evidence_register jsonb not null default '{}'::jsonb,
 full_pdf_sha256 text not null check (full_pdf_sha256 ~ '^[a-f0-9]{64}$'),
 sample_pdf_sha256 text check (sample_pdf_sha256 ~ '^[a-f0-9]{64}$'),
 object_path text not null unique check (object_path ~ '^reports/[A-Za-z0-9-]+/[A-Za-z0-9._-]+/[a-f0-9]{64}[.]pdf$'),
 constraint report_object_sha_matches_path check(right(object_path,68)=full_pdf_sha256 || '.pdf'),
 rights_basis text not null default 'review_required',
 status text not null default 'review' check (status in ('draft','review','approved','retired')),
 publication_approved boolean not null default false,
 owner_approved_at timestamptz,
 rights_verified_at timestamptz,
 supersedes_revision text,
 correction_notice text,
 created_at timestamptz not null default now(),
 primary key (report_id,revision)
);
create table if not exists public.fb_orders (
 order_id uuid primary key default gen_random_uuid(),
 provider text not null check (provider in ('razorpay','skydo','sandbox')),
 provider_reference text not null unique,
 buyer_email text not null,
 state text not null default 'pending' check (state in ('pending','paid_verified','refunded','disputed','cancelled')),
 provider_verified_at timestamptz,
 amount_minor bigint not null check (amount_minor >= 0),
 currency text not null check (currency ~ '^[A-Z]{3}$'),
 created_at timestamptz not null default now(),
 constraint verified_paid_has_time check (state <> 'paid_verified' or provider_verified_at is not null)
);
create table if not exists public.fb_entitlements (
 entitlement_id uuid primary key default gen_random_uuid(),
 order_id uuid not null references public.fb_orders(order_id),
 report_id text not null,
 revision text not null,
 status text not null default 'active' check (status in ('active','revoked')),
 expires_at timestamptz,
 revoked_at timestamptz,
 created_at timestamptz not null default now(),
 foreign key (report_id,revision) references public.fb_report_versions(report_id,revision),
 unique (order_id,report_id,revision),
 constraint revoked_state_consistent check(status <> 'revoked' or revoked_at is not null)
);
create table if not exists public.fb_download_tokens (
 token_sha256 text primary key check (token_sha256 ~ '^[a-f0-9]{64}$'),
 entitlement_id uuid not null references public.fb_entitlements(entitlement_id),
 expires_at timestamptz not null,
 used_at timestamptz,
 created_at timestamptz not null default now()
);
create index if not exists fb_tokens_entitlement_idx on public.fb_download_tokens(entitlement_id);
create table if not exists public.fb_delivery_events (
 event_id bigint generated always as identity primary key,
 entitlement_id uuid not null references public.fb_entitlements(entitlement_id),
 token_sha256 text not null,
 event_type text not null check (event_type in ('token_redeemed','delivery_error','reissued','revoked')),
 occurred_at timestamptz not null default now()
);
create table if not exists public.fb_delivery_release (
 id integer primary key check(id=1),
 enabled boolean not null default false,
 owner_approved_at timestamptz,
 updated_at timestamptz not null default now()
);
insert into public.fb_delivery_release(id,enabled,owner_approved_at)
values (1,false,null) on conflict(id) do nothing;

-- Defence in depth for every table even if Data API exposed public.
alter table public.fb_report_catalog enable row level security;
alter table public.fb_report_versions enable row level security;
alter table public.fb_orders enable row level security;
alter table public.fb_entitlements enable row level security;
alter table public.fb_download_tokens enable row level security;
alter table public.fb_delivery_events enable row level security;
alter table public.fb_delivery_release enable row level security;
revoke all on public.fb_report_catalog, public.fb_report_versions, public.fb_orders,
 public.fb_entitlements, public.fb_download_tokens, public.fb_delivery_events,
 public.fb_delivery_release from public, anon, authenticated;
grant select, insert, update, delete on public.fb_report_catalog, public.fb_report_versions, public.fb_orders,
 public.fb_entitlements, public.fb_download_tokens, public.fb_delivery_events,
 public.fb_delivery_release to service_role;
grant usage, select on sequence public.fb_delivery_events_event_id_seq to service_role;

-- Never overwrite digest/path of a registered report version. Correct with a new revision.
create or replace function public.fb_immutable_version_artifact()
returns trigger language plpgsql set search_path = '' as $$
begin
 if new.full_pdf_sha256 is distinct from old.full_pdf_sha256
    or new.sample_pdf_sha256 is distinct from old.sample_pdf_sha256
    or new.object_path is distinct from old.object_path
    or new.report_id is distinct from old.report_id
    or new.revision is distinct from old.revision then
   raise exception 'REPORT_VERSION_IMMUTABLE' using errcode='P0001';
 end if;
 return new;
end; $$;
drop trigger if exists fb_version_artifact_immutable on public.fb_report_versions;
create trigger fb_version_artifact_immutable before update on public.fb_report_versions
 for each row execute function public.fb_immutable_version_artifact();
revoke all on function public.fb_immutable_version_artifact() from public, anon, authenticated;

-- A database transaction is the only place where a download token may be consumed.
-- A client cannot provide an order ID, choose a report version or assert payment.
create or replace function public.fb_redeem_report_token(p_token_hash text)
returns table (bucket text, object_path text, full_pdf_sha256 text, report_id text, revision text)
language plpgsql security definer
set search_path = ''
as $$
declare
 v record;
begin
 if p_token_hash is null or p_token_hash !~ '^[a-f0-9]{64}$' then
   raise exception 'ACCESS_DENIED' using errcode = 'P0001';
 end if;
 select t.token_sha256, e.entitlement_id, vrs.object_path, vrs.full_pdf_sha256,
        vrs.report_id, vrs.revision
 into v
 from public.fb_download_tokens t
 join public.fb_entitlements e on e.entitlement_id=t.entitlement_id
 join public.fb_orders o on o.order_id=e.order_id
 join public.fb_report_versions vrs on vrs.report_id=e.report_id and vrs.revision=e.revision
 join public.fb_report_catalog c on c.report_id=vrs.report_id
 join public.fb_delivery_release g on g.id=1
 where t.token_sha256=p_token_hash and t.used_at is null and t.expires_at>now()
   and e.status='active' and e.revoked_at is null
   and (e.expires_at is null or e.expires_at>now())
   and o.state='paid_verified' and o.provider_verified_at is not null
   and vrs.status='approved' and vrs.publication_approved=true
   and vrs.owner_approved_at is not null and vrs.rights_verified_at is not null
   and c.state='approved' and g.enabled=true and g.owner_approved_at is not null
 for update of t;
 if not found then
   raise exception 'ACCESS_DENIED' using errcode='P0001';
 end if;
 update public.fb_download_tokens as t set used_at=now() where t.token_sha256=p_token_hash;
 insert into public.fb_delivery_events (entitlement_id,token_sha256,event_type)
 values(v.entitlement_id,p_token_hash,'token_redeemed');
 return query select 'firmablick-paid-reports'::text,
   v.object_path::text,v.full_pdf_sha256::text,v.report_id::text,v.revision::text;
end;
$$;
revoke all on function public.fb_redeem_report_token(text) from public, anon, authenticated;
grant execute on function public.fb_redeem_report_token(text) to service_role;
commit;

-- Provision private bucket firmablick-paid-reports separately in dedicated project.
-- Leave bucket public=false; never make a storage.objects SELECT policy for anon.
-- Do not execute this file against the connected IIA database.
