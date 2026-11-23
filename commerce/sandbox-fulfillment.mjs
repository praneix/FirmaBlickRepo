// FirmaBlick sandbox-only checkout/fulfilment reference engine.
// Inject durable transactional store, private object storage and verified provider
// adapter before enabling any deployed purchase path. No real payment calls.
import {createHmac, randomUUID, timingSafeEqual} from 'node:crypto';

export const SKU='FB-ENERGY-DE-2026-01';
export const AMOUNT_MINOR=14900;
const equal=(a,b)=>{
 const x=Buffer.from(String(a)),y=Buffer.from(String(b));
 return x.length===y.length && timingSafeEqual(x,y);
};
const mac=(secret,text)=>createHmac('sha256',secret).update(text).digest('hex');
export function signWebhook(secret,body){return mac(secret,body);}
export function verifyWebhook(secret,body,signature){
 return typeof signature==='string' && /^[a-f0-9]{64}$/.test(signature) && equal(mac(secret,body),signature);
}
export class SandboxFulfillment {
 constructor({secret,clock=()=>Date.now(),ttlMs=15*60*1000,assetStore,store}={}){
  if(typeof secret!=='string'||secret.length<32)throw Error('Sandbox signing secret must be at least 32 characters');
  if(!assetStore||typeof assetStore.read!=='function')throw Error('Private asset adapter required');
  this.secret=secret;this.clock=clock;this.ttlMs=ttlMs;this.assetStore=assetStore;
  // Memory store is for isolated tests only. Production requires a durable,
  // transactional implementation with unique event/order keys.
  this.store=store??{orders:new Map(),events:new Set()};
 }
 createOrder({email,sku=SKU}){
  if(sku!==SKU)throw Error('Unsupported SKU');
  if(typeof email!=='string'||email.length>254||!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))throw Error('Invalid buyer email');
  const id=randomUUID();
  const order={id,sku,email:email.trim().toLowerCase(),amountMinor:AMOUNT_MINOR,currency:'EUR',state:'pending',entitlement:false,createdAt:this.clock(),paidAt:null,refundedAt:null};
  this.store.orders.set(id,order);
  return {orderId:id,sku,currency:'EUR',amountMinor:AMOUNT_MINOR,state:'pending'};
 }
 // Caller must verify raw provider signature before this state transition.
 // Sandbox events emulate provider states; production must verify actual captured
 // amount/currency/order ownership using provider API before entitlement.
 webhook(rawBody,signature){
  if(!verifyWebhook(this.secret,rawBody,signature))throw Error('Invalid webhook signature');
  let event;try{event=JSON.parse(rawBody);}catch{throw Error('Malformed webhook payload');}
  if(!event||typeof event.id!=='string'||event.id.length>128||typeof event.orderId!=='string')throw Error('Invalid webhook event');
  if(!['captured','failed','cancelled','refunded'].includes(event.type))throw Error('Unsupported event type');
  if(this.store.events.has(event.id))return {duplicate:true};
  const order=this.store.orders.get(event.orderId);
  if(!order)throw Error('Unknown order');
  if(event.type==='captured'){
   if(event.amountMinor!==order.amountMinor||event.currency!==order.currency||event.sku!==order.sku)throw Error('Payment reconciliation failed');
   if(order.state!=='pending')throw Error('Cannot capture nonpending order');
   order.state='paid';order.entitlement=true;order.paidAt=this.clock();
  }else if(event.type==='refunded'){
   if(order.state!=='paid')throw Error('Cannot refund unpaid order');
   order.state='refunded';order.entitlement=false;order.refundedAt=this.clock();
  }else{
   if(order.state!=='pending')throw Error('Cannot change settled order');
   order.state=event.type;
  }
  this.store.events.add(event.id);
  return {duplicate:false,orderId:order.id,state:order.state};
 }
 issueLink(orderId){
  const order=this.store.orders.get(orderId);
  if(!order||order.state!=='paid'||!order.entitlement)throw Error('No valid entitlement');
  const expiry=this.clock()+this.ttlMs;
  const nonce=randomUUID();
  const payload=Buffer.from(JSON.stringify({orderId,sku:order.sku,expiry,nonce})).toString('base64url');
  return payload+'.'+mac(this.secret,payload);
 }
 async redeem(token){
  if(typeof token!=='string'||token.length>2048)throw Error('Invalid access token');
  const [payload,sig,...extra]=token.split('.');
  if(!payload||!sig||extra.length||!equal(mac(this.secret,payload),sig))throw Error('Invalid access token');
  let claim;try{claim=JSON.parse(Buffer.from(payload,'base64url').toString('utf8'));}catch{throw Error('Invalid access claim');}
  if(!Number.isSafeInteger(claim.expiry)||this.clock()>=claim.expiry)throw Error('Expired access token');
  const order=this.store.orders.get(claim.orderId);
  if(!order||order.state!=='paid'||!order.entitlement||order.sku!==claim.sku)throw Error('Access revoked');
  const asset=await this.assetStore.read(order.sku);
  if(!asset||!Buffer.isBuffer(asset.bytes)||asset.bytes.subarray(0,5).toString()!=='%PDF-')throw Error('Approved private PDF unavailable');
  return {bytes:asset.bytes,contentType:'application/pdf',fileName:asset.fileName};
 }
 getOrder(id){const o=this.store.orders.get(id);if(!o)throw Error('Unknown order');return {orderId:o.id,sku:o.sku,currency:o.currency,amountMinor:o.amountMinor,state:o.state,entitlement:o.entitlement};}
}
