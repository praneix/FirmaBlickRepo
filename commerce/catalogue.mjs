// Approved list prices in EUR minor units. No live checkout authorization.
export const CATALOGUE_VERSION = '2026-11-24';
export const CURRENCY = 'EUR';
export const ENERGY_SKU = 'FB-ENERGY-DE-2026-01';
export const PUBLICATION_PRICES = Object.freeze({brief:39000,outlook:69000,flagship:99000,sectorBundle:169000,libraryBundle:399000});
export const MEMBERSHIP_PRICES = Object.freeze({'FB-M':199000,'FB-MA':249000,'FB-MS':249000,'FB-ME':299000,'FB-MAS':369000,'FB-MEA':409000,'FB-MES':409000,'FB-MEAS':499000});
export const ADDITIONAL_LANGUAGE_PRICES = Object.freeze({brief:3900,outlook:5900,flagship:8900,sectorBundle:16900,libraryBundle:39900});
export const ANNUAL_LANGUAGE_PRICES = Object.freeze({1:24900,2:39900,3:54900,4:69900});
export function sandboxOffer(sku) {
 if(sku!==ENERGY_SKU) throw Error('Unsupported SKU');
 return Object.freeze({sku,currency:CURRENCY,amountMinor:PUBLICATION_PRICES.flagship,catalogueVersion:CATALOGUE_VERSION});
}
export function membershipOffer(sku) {
 if(!Object.hasOwn(MEMBERSHIP_PRICES,sku)) throw Error('Unsupported membership');
 return Object.freeze({sku,currency:CURRENCY,amountMinor:MEMBERSHIP_PRICES[sku],catalogueVersion:CATALOGUE_VERSION,annualPrepaid:true,enabled:false});
}

// Indicative enquiry prices only; no binding quote or checkout.
export const RESEARCH_ENQUIRY_PRICES = Object.freeze({
 sponsored:Object.freeze({brief:149000,outlook:299000,flagship:499000}),
 exclusive:Object.freeze({brief:299000,outlook:599000,flagship:999000}),
 private:Object.freeze({brief:449000,outlook:899000,flagship:1499000})
});
export function researchEnquiryOffer(kind,format) {
 if(!Object.hasOwn(RESEARCH_ENQUIRY_PRICES,kind)||!Object.hasOwn(RESEARCH_ENQUIRY_PRICES[kind],format)) throw Error('Unsupported research enquiry');
 return Object.freeze({kind,format,currency:CURRENCY,amountMinor:RESEARCH_ENQUIRY_PRICES[kind][format],catalogueVersion:CATALOGUE_VERSION,indicative:true,from:kind==='private',checkoutEnabled:false,requiresScopeRightsAndFeasibilityApproval:true});
}
