import {INDUSTRIES,verifyHistoricalPayload,latestMonth,filterMonths,plotPoints,svgSegments} from './historical-core.mjs';
const get=(id)=>document.getElementById(id);
const picker=get('historical-sector'),range=get('historical-range'),status=get('historical-status');
const figure=get('historical-chart'),table=get('historical-rows');
const meta=get('historical-provenance'),caption=get('historical-caption');
const notReady=(reason)=>{
  figure.replaceChildren();
  table.replaceChildren();
  status.textContent='Official historical data unavailable. '+reason;
  meta.textContent='Source: Destatis GENESIS · Verification pending · No figures displayed.';
  caption.textContent='No verified monthly production-index observations available.';
};
for(const item of INDUSTRIES){const option=document.createElement('option');option.value=item.code;option.textContent=item.label;picker.append(option);}
function draw(series){
  const rows=filterMonths(series,Number(range.value));
  figure.replaceChildren(); table.replaceChildren();
  const points=plotPoints(rows);
  const ns='http://www.w3.org/2000/svg';
  const element=(tag,attrs={})=>{const el=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))el.setAttribute(k,String(v));return el;};
  const values=rows.filter(r=>r.value!==null);
  if(values.length){
    const desc=element('desc');desc.textContent='Historical monthly production index. Detailed values appear in the following accessible table.';figure.append(desc);
    for(const segment of svgSegments(points)){
      if(segment.length>1) figure.append(element('polyline',{points:segment.map(p=>p.x.toFixed(1)+','+p.y.toFixed(1)).join(' '),class:'historical-line'}));
      else figure.append(element('circle',{cx:segment[0].x,cy:segment[0].y,r:3,class:'historical-point'}));
    }
  }
  for(const o of rows){
    const tr=document.createElement('tr'),th=document.createElement('th'),td=document.createElement('td'),flag=document.createElement('td');
    th.scope='row';th.textContent=o.period;td.textContent=o.value===null?'Unavailable':o.value.toFixed(1);
    flag.textContent=o.missing_reason || o.source_status_flags.join(', ') || 'Published';
    tr.append(th,td,flag);table.append(tr);
  }
  caption.textContent='Monthly production index ('+series.base_year+' = 100), '+series.adjustment.replaceAll('_',' ')+', Germany.';
  status.textContent=values.length? 'Latest source period: '+latestMonth(series)+' · '+values.length+' observed values in selected range.' :
    'The selected months contain no published numeric observations.';
  const link=document.createElement('a');link.href=series.source_url;link.target='_blank';link.rel='noopener noreferrer';link.textContent='Destatis source';
  meta.replaceChildren(document.createTextNode(
    'Source: Destatis GENESIS '+series.dataset_id+' · WZ2008 '+series.industry_code+
    ' · Acquired '+series.retrieved_at+' · Release verified · '),link);
}
let payload;
function update(){
  if(!payload||payload.status!=='validated'){notReady(payload?.reason||'Source verification is pending.');return;}
  const selected=payload.series.find(s=>s.industry_code===picker.value);
  if(!selected){notReady('Selected industry is absent from the validated release.');return;}
  draw(selected);
}
picker.addEventListener('change',update);
range.addEventListener('change',update);
async function load(){
  try{
    const response=await fetch('./data/historical.json',{cache:'no-store'});
    if(!response.ok)throw Error('Data release file unavailable.');
    payload=verifyHistoricalPayload(await response.json());
  }catch(e){payload={status:'unavailable',reason:'Verified source release cannot be loaded.'};}
  update();
}
load();
