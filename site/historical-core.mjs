/* Browser/Node shared read-only source-certified historical view contract. */
export const INDUSTRIES = Object.freeze([
  { code:'C', label:'Manufacturing aggregate', dataset:'42153-0001' },
  { code:'20', label:'Chemicals and chemical products', dataset:'42153-0002' },
  { code:'24', label:'Basic metals', dataset:'42153-0002' },
  { code:'28', label:'Machinery and equipment', dataset:'42153-0002' },
  { code:'29', label:'Motor vehicles and parts', dataset:'42153-0002' }
]);
export const MAX_POINTS = 240;
const isMonth = (s) => typeof s === 'string' && /^\d{4}-(0[1-9]|1[0-2])$/.test(s);
const isUTC = (s) => typeof s === 'string' && /^\d{4}-\d\d-\d\dT/.test(s) && s.endsWith('Z') && !Number.isNaN(Date.parse(s));
const known = Object.fromEntries(INDUSTRIES.map(i=>[i.code,i]));
const validSha = (s) => typeof s === 'string' && /^[a-f0-9]{64}$/.test(s);
export function verifyHistoricalPayload(payload) {
  if (!payload || payload.schema_version !== '1.0.0' || !['unavailable','validated'].includes(payload.status)) throw Error('Invalid historical data status.');
  if (payload.status === 'unavailable') {
    if (!Array.isArray(payload.series) || payload.series.length || typeof payload.reason !== 'string' || !payload.reason.trim()) throw Error('Unverified series must not carry data.');
    return payload;
  }
  if (!isUTC(payload.generated_at) || !Array.isArray(payload.series) || payload.series.length !== 5) throw Error('Missing source-certified five-series release.');
  const seen=new Set();
  for (const s of payload.series) {
    const meta=known[s.industry_code];
    if (!meta || seen.has(s.industry_code) || s.dataset_id !== meta.dataset ||
        s.source !== 'Destatis GENESIS' || s.geo !== 'DE' || s.frequency !== 'M' ||
        s.unit !== 'index' || s.classification !== 'WZ2008' ||
        !['original','calendar_adjusted','seasonally_adjusted','seasonal_calendar_adjusted'].includes(s.adjustment) ||
        !Number.isInteger(s.base_year) || s.base_year < 1990 || s.base_year > 2100 ||
        !isUTC(s.retrieved_at) || !validSha(s.raw_sha256) || !s.acquisition_id ||
        s.official_verification !== true || s.publication_approved !== true ||
        typeof s.source_url !== 'string' || !s.source_url.startsWith('https://genesis.destatis.de/') ||
        !Array.isArray(s.observations) || !s.observations.length || s.observations.length > MAX_POINTS) throw Error('Historical series source certification incomplete.');
    seen.add(s.industry_code);
    const periods=new Set();
    let latest='';
    for(const item of s.observations){
      if(!isMonth(item.period) || periods.has(item.period) || (latest && item.period <= latest) ||
         !(item.value === null || (typeof item.value === 'number' && Number.isFinite(item.value) && item.value >= 0)) ||
         !Array.isArray(item.source_status_flags) || item.source_status_flags.some(f=>typeof f!=='string') ||
         (item.value === null && (!item.missing_reason || !item.missing_reason.trim())) ||
         (item.value !== null && item.missing_reason)) throw Error('Historical observation malformed or duplicated.');
      periods.add(item.period);latest=item.period;
    }
  }
  return payload;
}
export function latestMonth(series){return series.observations.at(-1)?.period ?? 'Unavailable';}
export function filterMonths(series, lastN){
  if(![12,24,60,120,240].includes(lastN)) throw Error('Unsupported range');
  return series.observations.slice(-lastN);
}
export function plotPoints(observations, width=700, height=230){
  const valid=observations.filter(o=>o.value!==null);
  if(!valid.length)return [];
  const min=Math.min(...valid.map(o=>o.value)),max=Math.max(...valid.map(o=>o.value));
  const span=Math.max(1,max-min);
  return observations.map((o,i)=>o.value===null?null:{
    x:38+(i* (width-56)/Math.max(1,observations.length-1)),
    y:height-32-((o.value-min)/span)*(height-55),
    period:o.period,value:o.value
  });
}
export function svgSegments(points){
  const lines=[];let segment=[];
  for(const point of points){
    if(point){segment.push(point);}else if(segment.length){lines.push(segment);segment=[];}
  }
  if(segment.length)lines.push(segment);
  return lines;
}
