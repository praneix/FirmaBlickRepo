import test from 'node:test';
import assert from 'node:assert/strict';
import {createPriceLookup} from '../commerce/price-registry.mjs';
const key='FB-ENERGY-DE-2026-01';
const row={price_key:key,currency:'EUR',amount_minor:99000,version:'v1',approval_ref:'owner-approved'};
test('server lookup propagates changes and preserves prior snapshot',async()=>{
 let current=row;
 const lookup=createPriceLookup(async(name,args)=>{assert.equal(name,'fb_lookup_price');assert.equal(args.p_key,key);return {data:[current]};});
 const old=await lookup(key);current={...row,amount_minor:109000,version:'synthetic-v2'};
 assert.equal((await lookup(key)).amountMinor,109000);assert.equal(old.amountMinor,99000);assert.ok(Object.isFrozen(old));
});
test('fails closed on unavailable, ambiguous or invalid records',async()=>{
 for(const response of [{error:'offline'},{data:[]},{data:[row,row]},{data:[{...row,price_key:'other'}]},{data:[{...row,currency:'USD'}]},{data:[{...row,amount_minor:1.5}]},{data:[{...row,approval_ref:''}]}]){
  await assert.rejects(createPriceLookup(async()=>response)(key));
 }
});
