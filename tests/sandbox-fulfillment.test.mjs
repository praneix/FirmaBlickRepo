import test from 'node:test';
import assert from 'node:assert/strict';
import {SandboxFulfillment,SKU,AMOUNT_MINOR,signWebhook,verifyWebhook} from '../commerce/sandbox-fulfillment.mjs';
const secret='firmablick-sandbox-unique-key-32-characters-minimum';
let now=1732000000000;
const pdf=Buffer.from('%PDF-1.4\n% sandbox fixture only\n');
const create=()=>new SandboxFulfillment({secret,clock:()=>now,ttlMs:3000,assetStore:{read:async sku=>sku===SKU?{bytes:pdf,fileName:'test-fixture.pdf'}:null}});
const event=(engine,body)=>{const raw=JSON.stringify(body);return engine.webhook(raw,signWebhook(secret,raw));};
const capture=(engine,orderId,id='event-capture')=>event(engine,{id,orderId,type:'captured',sku:SKU,amountMinor:AMOUNT_MINOR,currency:'EUR'});
test('happy path: paid -> secure PDF, correct SKU and exact price',async()=>{
 const engine=create();const order=engine.createOrder({email:'finance@example.org'});
 assert.equal(order.amountMinor,99000);assert.equal(order.state,'pending');
 assert.throws(()=>engine.issueLink(order.orderId),/entitlement/);
 assert.equal(capture(engine,order.orderId).state,'paid');
 const link=engine.issueLink(order.orderId);const asset=await engine.redeem(link);
 assert.equal(asset.contentType,'application/pdf');assert.deepEqual(asset.bytes,pdf);
 assert.equal(engine.getOrder(order.orderId).entitlement,true);
 assert.deepEqual(capture(engine,order.orderId),{duplicate:true});
});
test('fail closed: bad signature, incorrect amount, unsupported SKU',()=>{
 const engine=create(),order=engine.createOrder({email:'finance@example.org'});
 const raw=JSON.stringify({id:'bad',orderId:order.orderId,type:'captured',sku:SKU,amountMinor:14900,currency:'EUR'});
 assert.equal(verifyWebhook(secret,raw,'0'.repeat(64)),false);
 assert.throws(()=>engine.webhook(raw,'0'.repeat(64)),/signature/);
 assert.throws(()=>event(engine,{id:'wrong',orderId:order.orderId,type:'captured',sku:SKU,amountMinor:14900,currency:'EUR'}),/reconciliation/);
 assert.equal(engine.getOrder(order.orderId).state,'pending');
 assert.throws(()=>engine.createOrder({email:'x@y.org',sku:'OTHER'}),/SKU/);
});
test('cancelled/failed orders never get access',()=>{
 for(const type of ['cancelled','failed']){
  const engine=create(),order=engine.createOrder({email:'finance@example.org'});
  assert.equal(event(engine,{id:type,orderId:order.orderId,type}).state,type);
  assert.throws(()=>engine.issueLink(order.orderId),/entitlement/);
  assert.throws(()=>capture(engine,order.orderId,'late-capture'),/nonpending/);
 }
});
test('refund immediately revokes previously issued link',async()=>{
 const engine=create(),order=engine.createOrder({email:'finance@example.org'});
 capture(engine,order.orderId);const link=engine.issueLink(order.orderId);
 assert.equal(event(engine,{id:'refund',orderId:order.orderId,type:'refunded'}).state,'refunded');
 await assert.rejects(engine.redeem(link),/revoked/);
});
test('expiry, tampering, missing private PDF and invalid buyer rejected',async()=>{
 const engine=create(),order=engine.createOrder({email:'finance@example.org'});
 assert.throws(()=>engine.createOrder({email:'bad'}),/email/);
 capture(engine,order.orderId);const link=engine.issueLink(order.orderId);
 await assert.rejects(engine.redeem(link+'x'),/token/);
 now+=3000;await assert.rejects(engine.redeem(link),/Expired/);
 now-=3000;
 const missing=new SandboxFulfillment({secret,clock:()=>now,assetStore:{read:async()=>null},store:engine.store});
 await assert.rejects(missing.redeem(link),/private PDF unavailable/);
});
test('a duplicate event id cannot be applied to a second order',()=>{
 const engine=create(),a=engine.createOrder({email:'a@b.org'}),b=engine.createOrder({email:'c@d.org'});
 capture(engine,a.orderId,'same-event');
 assert.deepEqual(capture(engine,b.orderId,'same-event'),{duplicate:true});
 assert.equal(engine.getOrder(b.orderId).state,'pending');
});

test('legacy pending order cannot settle at superseded price',()=>{
 const engine=create(),order=engine.createOrder({email:'finance@example.org'});
 const stored=engine.store.orders.get(order.orderId);stored.amountMinor=14900;delete stored.catalogueVersion;
 assert.throws(()=>event(engine,{id:'legacy',orderId:order.orderId,type:'captured',sku:SKU,amountMinor:14900,currency:'EUR'}),/reconciliation/);
 assert.equal(engine.getOrder(order.orderId).entitlement,false);
});
test('wrong currency and SKU fail closed at approved price',()=>{
 const engine=create(),order=engine.createOrder({email:'finance@example.org'});
 for(const [sku,currency] of [[SKU,'USD'],['OTHER','EUR']])assert.throws(()=>event(engine,{id:'mismatch',orderId:order.orderId,type:'captured',sku,amountMinor:99000,currency}),/reconciliation/);
 assert.equal(engine.getOrder(order.orderId).state,'pending');
});
