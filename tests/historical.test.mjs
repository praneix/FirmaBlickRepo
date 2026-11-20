import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {INDUSTRIES,verifyHistoricalPayload,filterMonths,latestMonth,plotPoints,svgSegments,sourceAgeDays} from '../site/historical-core.mjs';

const unavailable=JSON.parse(readFileSync(new URL('../site/data/historical.json',import.meta.url),'utf8'));
const source=readFileSync(new URL('../site/index.html',import.meta.url),'utf8');
const sha='e'.repeat(64);
const sample=()=>{
  const data={schema_version:'1.0.0',status:'validated',generated_at:'2026-11-19T12:00:00Z',series:[]};
  for(const i of INDUSTRIES)data.series.push({
    industry_code:i.code,dataset_id:i.dataset,source:'Destatis GENESIS',source_url:'https://genesis.destatis.de/datenbank/online/statistic/42153',
    geo:'DE',frequency:'M',unit:'index',base_year:2021,adjustment:'original',classification:'WZ2008',
    raw_sha256:sha,acquisition_id:'synthetic-only-'+i.code,retrieved_at:'2026-11-19T10:00:00Z',
    official_verification:true,publication_approved:true,
    observations:[{period:'2026-01',value:100.5,source_status_flags:[]},{period:'2026-02',value:null,source_status_flags:['suppressed'],missing_reason:'suppressed'},{period:'2026-03',value:99.5,source_status_flags:['provisional']}]
  });
  return data;
};
test('production bundle contains only deliberately unavailable official data',()=>{
  assert.equal(verifyHistoricalPayload(unavailable).status,'unavailable');
  assert.equal(unavailable.series.length,0);
  assert.match(unavailable.reason,/Official Destatis/);
});
test('historical UI names five industries, exposes controls and accessible table',()=>{
  assert.equal(INDUSTRIES.length,5);
  assert.deepEqual(INDUSTRIES.map(i=>i.code),['C','20','24','28','29']);
  for(const id of ['historical','historical-sector','historical-range','historical-status','historical-chart','historical-rows','historical-provenance','historical-caption'])assert.ok(source.includes('id="'+id+'"'),id);
  assert.match(source,/do not represent company revenue/);
  assert.match(source,/Illustrative values only/);
});
test('validated payload requires complete five-series source metadata and coherent methodology',()=>{
  const input=sample();
  assert.equal(verifyHistoricalPayload(input).series.length,5);
  for(const mutation of [
    p=>{p.series.pop();},p=>{p.series[1].industry_code='C';},
    p=>{p.series[0].raw_sha256='fake';},p=>{p.series[0].publication_approved=false;},
    p=>{p.series[0].official_verification=false;},p=>{p.series[0].base_year=2020;},
    p=>{p.series[0].adjustment='seasonally_adjusted';},
    p=>{p.series[0].source_url='https://example.com/fake';},
    p=>{p.series[0].retrieved_at='2026-11-20T12:00:00Z';},
    p=>{p.series[0].observations[0].period='2026-13';},
    p=>{p.series[0].observations.push({...p.series[0].observations[2]});},
    p=>{p.series[0].observations[1].value=0;},
    p=>{p.series[0].observations[1].missing_reason='';},
    p=>{p.series[0].observations[0].value=Infinity;}
  ]){const mutated=sample();mutation(mutated);assert.throws(()=>verifyHistoricalPayload(mutated));}
});
test('unavailable and invalid source states fail closed without synthetic chart points',()=>{
  assert.throws(()=>verifyHistoricalPayload({...unavailable,series:sample().series}));
  assert.throws(()=>verifyHistoricalPayload({schema_version:'1.0.0',status:'validated',series:[]}));
  assert.deepEqual(plotPoints([{period:'2026-01',value:null}]),[]);
});
test('period range, missing-value breaks and exact table values remain distinguishable',()=>{
  const s=sample().series[0];
  assert.equal(latestMonth(s),'2026-03');
  assert.equal(filterMonths(s,12).length,3);
  assert.throws(()=>filterMonths(s,13));
  const points=plotPoints(s.observations);
  assert.equal(points.length,3);
  assert.equal(points[1],null);
  assert.equal(svgSegments(points).length,2);
  assert.equal(s.observations[0].value,100.5);
});
test('source age makes stale verified releases visible',()=>{
  assert.equal(sourceAgeDays('2026-01-01T00:00:00Z',new Date('2026-05-03T00:00:00Z')),122);
  assert.equal(sourceAgeDays('2026-05-03T00:00:00Z',new Date('2026-05-03T00:00:00Z')),0);
});
