import test from 'node:test';
import assert from 'node:assert/strict';
import {sandboxOffer,membershipOffer,MEMBERSHIP_PRICES,PUBLICATION_PRICES,ADDITIONAL_LANGUAGE_PRICES,ANNUAL_LANGUAGE_PRICES,ENERGY_SKU} from '../commerce/catalogue.mjs';
test('approved Energy price and unsupported SKU',()=>{
 assert.equal(sandboxOffer(ENERGY_SKU).amountMinor,99000);
 assert.throws(()=>sandboxOffer('FB-M'),/Unsupported/);
});
test('all annual membership prices are correct and disabled',()=>{
 assert.deepEqual(Object.values(MEMBERSHIP_PRICES),[199000,249000,249000,299000,369000,409000,409000,499000]);
 for(const sku of Object.keys(MEMBERSHIP_PRICES)){assert.equal(membershipOffer(sku).enabled,false);assert.equal(membershipOffer(sku).annualPrepaid,true);}
 assert.throws(()=>membershipOffer('toString'),/Unsupported/);
});
test('publication and language schedules match approved amounts',()=>{
 assert.deepEqual(Object.values(PUBLICATION_PRICES),[39000,69000,99000,169000,399000]);
 assert.deepEqual(Object.values(ADDITIONAL_LANGUAGE_PRICES),[3900,5900,8900,16900,39900]);
 assert.deepEqual(Object.values(ANNUAL_LANGUAGE_PRICES),[24900,39900,54900,69900]);
});
