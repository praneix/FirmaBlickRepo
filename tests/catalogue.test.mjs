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

import {researchEnquiryOffer,RESEARCH_ENQUIRY_PRICES,CATALOGUE_VERSION} from '../commerce/catalogue.mjs';
test('all research enquiry prices are indicative and checkout disabled',()=>{
 const expected={sponsored:[149000,299000,499000],exclusive:[299000,599000,999000],private:[449000,899000,1499000]};
 for(const [kind,prices] of Object.entries(expected)){
  assert.deepEqual(Object.values(RESEARCH_ENQUIRY_PRICES[kind]),prices);
  for(const [i,format] of ['brief','outlook','flagship'].entries()){
   const offer=researchEnquiryOffer(kind,format);
   assert.equal(offer.amountMinor,prices[i]);assert.equal(offer.currency,'EUR');
   assert.equal(offer.catalogueVersion,CATALOGUE_VERSION);assert.equal(offer.indicative,true);
   assert.equal(offer.checkoutEnabled,false);assert.equal(offer.from,kind==='private');
   assert.equal(offer.requiresScopeRightsAndFeasibilityApproval,true);
  }
 }
 assert.throws(()=>researchEnquiryOffer('toString','brief'),/Unsupported/);
 assert.throws(()=>researchEnquiryOffer('sponsored','toString'),/Unsupported/);
});
