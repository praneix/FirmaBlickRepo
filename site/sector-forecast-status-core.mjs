/* Historical-only sector forecast availability. No numerical forecasts are loaded. */
export const CODES=Object.freeze(['28','29','24','20']);
export function verifySectorForecastStatus(payload){
  if(!payload||payload.schema_version!=='1.0.0'||payload.status!=='historical_only'||
      payload.publication_approved!==false||payload.aggregate_release_transfer_permitted!==false||
      !payload.release_flags||!Array.isArray(payload.sectors)||payload.sectors.length!==4)
    throw Error('Sector publication contract missing or unsafe.');
  if(Object.keys(payload.release_flags).length!==4 ||
      CODES.some(code=>payload.release_flags[code]!==false))
    throw Error('A sector forecast cannot be automatically authorized.');
  const seen=new Set();
  for(const row of payload.sectors){
    if(!CODES.includes(row.industry_code)||seen.has(row.industry_code)||
        row.mode!=='historical_only'||typeof row.reason!=='string'||!row.reason.trim()||
        Object.hasOwn(row,'forecasts')||Object.hasOwn(row,'forecast_months')||
        Object.hasOwn(row,'projection'))
      throw Error('Unapproved or ambiguous sector release.');
    seen.add(row.industry_code);
  }
  return payload;
}
export function sectorAvailability(payload,code){
  if(code==='C')return 'Manufacturing aggregate: official forecast certification is pending. Historical observations only.';
  if(!CODES.includes(code))return 'Official forecast unavailable.';
  try{
    const approved=verifySectorForecastStatus(payload);
    return approved.sectors.find(s=>s.industry_code===code).reason+' Historical observations only; no sector projections published.';
  }catch{
    return 'Sector forecast unavailable: source or release approval cannot be verified. Historical observations only.';
  }
}
