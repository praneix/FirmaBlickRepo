-- Run only against ephemeral postgres CI, NEVER the connected IIA project.
-- This test exercises the actual atomic PL/pgSQL authorization state machine.
begin;
insert into public.fb_report_catalog(report_id,slug,title,audience,thesis)
values('FB-ENERGY-DE-2026-01','energy-test','Energy test','Industrial buyers','Fictional CI test');
insert into public.fb_report_versions(report_id,revision,title,full_pdf_sha256,sample_pdf_sha256,object_path)
values('FB-ENERGY-DE-2026-01','V4-TEST','Test',repeat('a',64),repeat('b',64),
 'reports/FB-ENERGY-DE-2026-01/V4-TEST/'||repeat('a',64)||'.pdf');
insert into public.fb_orders(order_id,provider,provider_reference,buyer_email,state,amount_minor,currency)
values ('00000000-0000-0000-0000-000000000001','sandbox','fixture-order-001','qa@example.invalid','pending',14900,'EUR');
insert into public.fb_entitlements(entitlement_id,order_id,report_id,revision)
values('00000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000001','FB-ENERGY-DE-2026-01','V4-TEST');
insert into public.fb_download_tokens(token_sha256,entitlement_id,expires_at)
values (repeat('1',64),'00000000-0000-0000-0000-000000000002',now()+interval '15 min');

do $$
begin
 if has_function_privilege('anon','public.fb_redeem_report_token(text)','EXECUTE') then
   raise exception 'ANON_RPC_EXECUTE_GRANTED';
 end if;
 if has_table_privilege('authenticated','public.fb_orders','SELECT') then
   raise exception 'AUTHENTICATED_ORDER_SELECT_GRANTED';
 end if;
end;
$$;

set local role service_role;
do $$
declare denied boolean := false;
begin
 begin
  perform * from public.fb_redeem_report_token(repeat('1',64));
 exception when sqlstate 'P0001' then denied := true; end;
 if not denied then raise exception 'PENDING_ORDER_WAS_AUTHORIZED'; end if;
end; $$;
reset role;
update public.fb_orders set state='paid_verified',provider_verified_at=now() where provider_reference='fixture-order-001';
set local role service_role;
do $$
declare denied boolean := false;
begin
 begin perform * from public.fb_redeem_report_token(repeat('1',64));
 exception when sqlstate 'P0001' then denied := true; end;
 if not denied then raise exception 'UNAPPROVED_REPORT_WAS_AUTHORIZED'; end if;
end; $$;
reset role;
update public.fb_report_catalog set state='approved' where report_id='FB-ENERGY-DE-2026-01';
update public.fb_report_versions set status='approved',publication_approved=true,
 owner_approved_at=now(),rights_verified_at=now() where report_id='FB-ENERGY-DE-2026-01';
set local role service_role;
do $$
declare denied boolean := false;
begin
 begin perform * from public.fb_redeem_report_token(repeat('1',64));
 exception when sqlstate 'P0001' then denied := true; end;
 if not denied then raise exception 'DISABLED_GLOBAL_RELEASE_WAS_AUTHORIZED'; end if;
end; $$;
reset role;
update public.fb_delivery_release set enabled=true,owner_approved_at=now() where id=1;
set local role service_role;
do $$
declare rec record;
replay_denied boolean := false;
begin
 select * into rec from public.fb_redeem_report_token(repeat('1',64));
 if rec.bucket<>'firmablick-paid-reports' or rec.report_id<>'FB-ENERGY-DE-2026-01' or rec.revision<>'V4-TEST'
    or rec.full_pdf_sha256<>repeat('a',64) then
   raise exception 'WRONG_REPORT_GRANTED';
 end if;
 begin
   perform * from public.fb_redeem_report_token(repeat('1',64));
 exception when sqlstate 'P0001' then replay_denied := true; end;
 if not replay_denied then raise exception 'TOKEN_REPLAY_ACCEPTED'; end if;
end; $$;
reset role;
insert into public.fb_download_tokens(token_sha256,entitlement_id,expires_at)
values (repeat('2',64),'00000000-0000-0000-0000-000000000002',now()+interval '15 min');
update public.fb_orders set state='refunded' where provider_reference='fixture-order-001';
set local role service_role;
do $$
declare denied boolean := false;
begin
 begin perform * from public.fb_redeem_report_token(repeat('2',64));
 exception when sqlstate 'P0001' then denied := true; end;
 if not denied then raise exception 'REFUNDED_ORDER_ACCEPTED'; end if;
end; $$;
reset role;
update public.fb_orders set state='paid_verified' where provider_reference='fixture-order-001';
insert into public.fb_download_tokens(token_sha256,entitlement_id,expires_at)
values (repeat('3',64),'00000000-0000-0000-0000-000000000002',now()-interval '1 min');
set local role service_role;
do $$
declare denied boolean := false;
begin
 begin perform * from public.fb_redeem_report_token(repeat('3',64));
 exception when sqlstate 'P0001' then denied := true; end;
 if not denied then raise exception 'EXPIRED_TOKEN_ACCEPTED'; end if;
end; $$;
reset role;
insert into public.fb_download_tokens(token_sha256,entitlement_id,expires_at)
values (repeat('4',64),'00000000-0000-0000-0000-000000000002',now()+interval '15 min');
update public.fb_entitlements set status='revoked',revoked_at=now()
 where entitlement_id='00000000-0000-0000-0000-000000000002';
set local role service_role;
do $$
declare denied boolean := false;
begin
 begin perform * from public.fb_redeem_report_token(repeat('4',64));
 exception when sqlstate 'P0001' then denied := true; end;
 if not denied then raise exception 'REVOKED_ENTITLEMENT_ACCEPTED'; end if;
end; $$;
reset role;
do $$
declare denied boolean := false;
begin
 begin
 update public.fb_report_versions set full_pdf_sha256=repeat('f',64) where report_id='FB-ENERGY-DE-2026-01';
 exception when sqlstate 'P0001' then denied := true; end;
 if not denied then raise exception 'IMMUTABILITY_GUARD_FAILED'; end if;
end; $$;
rollback;
-- Transactions rolled back. No real customer or content created.
