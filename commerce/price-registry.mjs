// Server-only adapter; no static fallback, no provider or network calls in tests.
export function createPriceLookup(rpc) {
 if(typeof rpc!=='function') throw Error('Price RPC required');
 return async function lookup(key) {
  if(typeof key!=='string'||!/^[A-Za-z0-9:_-]+$/.test(key)) throw Error('Invalid price key');
  const {data,error}=await rpc('fb_lookup_price',{p_key:key});
  if(error||!Array.isArray(data)||data.length!==1) throw Error('Price unavailable');
  const p=data[0];
  if(!p||p.price_key!==key||p.currency!=='EUR'||!Number.isSafeInteger(p.amount_minor)||p.amount_minor<=0||typeof p.version!=='string'||!p.version.trim()||typeof p.approval_ref!=='string'||!p.approval_ref.trim()) throw Error('Invalid price record');
  return Object.freeze({sku:key,currency:p.currency,amountMinor:p.amount_minor,catalogueVersion:p.version,approvalRef:p.approval_ref});
 };
}
