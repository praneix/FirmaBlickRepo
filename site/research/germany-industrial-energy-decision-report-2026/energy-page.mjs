// CV1-06 owner-reviewed navigation and original-data monthly chart.
// This page contains only open-source, source-attributed monthly aggregates.
// Forecasts, synthetic linework and original unpublished industrial series are excluded.
const chart=document.getElementById('market-monthly-chart');
const ns='http://www.w3.org/2000/svg';
function elt(name,attrs={},content=''){
 const node=document.createElementNS(ns,name);
 for(const [key,value] of Object.entries(attrs))node.setAttribute(key,String(value));
 if(content)node.textContent=content;
 return node;
}
async function renderMonthlyMarket(){
 try{
  const response=await fetch('./energy-2025-monthly.json',{cache:'no-store'});
  if(!response.ok)throw Error('Evidence response unavailable');
  const d=await response.json();
  if(d.publication_state!=='protected_preview_only'||d.year!==2025||d.unit!=='EUR/MWh'||d.geography!=='DE-LU'||
     !Array.isArray(d.months)||d.months.length!==12||Math.abs(d.annual_time_weighted_mean_eur_mwh-89.32172)>0.00001)
      throw Error('Evidence definitions differ from approved preview contract');
  const values=d.months.map((m,i)=>{
    const expect='2025-'+String(i+1).padStart(2,'0');
    if(m.period!==expect||!Number.isFinite(m.mean_eur_mwh)||m.mean_eur_mwh<0||m.mean_eur_mwh>1000)
      throw Error('Invalid monthly series');
    return m.mean_eur_mwh;
  });
  chart.replaceChildren();
  const left=60,right=492,top=42,bottom=257,max=140;
  const px=i=>left+(right-left)*i/11,py=v=>bottom-(v/max)*(bottom-top);
  for(const value of [0,40,80,120]){
    const y=py(value);
    chart.append(elt('line',{x1:left,y1:y,x2:right,y2:y,stroke:'#587383','stroke-width':1,opacity:.58}));
    chart.append(elt('text',{x:left-9,y:y+4,'text-anchor':'end',fill:'#e8dcd6','font-size':13},String(value)));
  }
  for(const i of [0,2,4,6,8,10,11]){
    chart.append(elt('text',{x:px(i),y:bottom+27,'text-anchor':'middle',fill:'#e7d9d2','font-size':13},['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][i]));
  }
  const points=values.map((v,i)=>px(i)+','+py(v)).join(' ');
  const trend=elt('polyline',{points,fill:'none',stroke:'#efb1a5','stroke-width':3,'stroke-linejoin':'round','stroke-linecap':'round'});
  chart.append(trend);
  values.forEach((v,i)=>{
    const p=elt('circle',{cx:px(i),cy:py(v),r:4,fill:'#f3d3c7',stroke:'#10283d','stroke-width':1});
    const label=elt('title',{},d.months[i].period+': '+v.toFixed(2)+' €/MWh');
    p.append(label);chart.append(p);
  });
  chart.append(elt('text',{x:60,y:22,fill:'#f4e3db','font-size':14},'Monthly mean · €/MWh'));
  chart.append(elt('text',{x:492,y:310,'text-anchor':'end',fill:'#f4e3db','font-size':13},'Annual time-weighted average: €89.32/MWh'));
  chart.dataset.sourceVerified='true';
 }catch(error){
  chart.replaceChildren(elt('text',{x:24,y:145,fill:'#f4e3db'},'Source-verified chart temporarily unavailable'));
  chart.dataset.sourceVerified='false';
 }
}
renderMonthlyMarket();

const links=[...document.querySelectorAll('.report-rail-link')];
const sections=[...document.querySelectorAll('[data-report-section]')];
const activate=id=>{
 links.forEach(link=>{
   const selected=link.getAttribute('href')==='#'+id;
   if(selected)link.setAttribute('aria-current','location');
   else link.removeAttribute('aria-current');
 });
};
if('IntersectionObserver' in window){
 const observer=new IntersectionObserver(entries=>{
  const candidates=entries.filter(x=>x.isIntersecting).sort((a,b)=>b.intersectionRatio-a.intersectionRatio);
  if(candidates.length)activate(candidates[0].target.dataset.reportSection);
 },{rootMargin:'-20% 0px -45% 0px',threshold:[0,.15,.3,.6]});
 sections.forEach(s=>observer.observe(s));
}
links.forEach(link=>link.addEventListener('click',()=>{
 const id=link.getAttribute('href').slice(1);
 activate(id);
}));
