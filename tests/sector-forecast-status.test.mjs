import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {CODES,verifySectorForecastStatus,sectorAvailability} from '../site/sector-forecast-status-core.mjs';
const read=()=>JSON.parse(readFileSync(new URL('../site/data/sector-forecast-status.json',import.meta.url),'utf8'));
test('sector forecast release defaults to explicitly historical-only with zero projections',()=>{
  const p=verifySectorForecastStatus(read());
  assert.deepEqual(CODES,['28','29','24','20']);
  assert.equal(p.publication_approved,false);
  assert.equal(p.aggregate_release_transfer_permitted,false);
  assert.equal(p.sectors.length,4);
  assert.deepEqual(Object.values(p.release_flags),[false,false,false,false]);
  for(const code of CODES)assert.match(sectorAvailability(p,code),/Historical observations only/);
});
test('aggregate status can never authorize machinery or any independent sector',()=>{
  const p=read();
  p.aggregate_release_transfer_permitted=true;
  assert.throws(()=>verifySectorForecastStatus(p));
  assert.match(sectorAvailability(p,'28'),/unavailable/i);
});
test('forged publication status or numeric projections fail closed',()=>{
  for(const change of [
    p=>{p.publication_approved=true;},
    p=>{p.release_flags['28']=true;},
    p=>{p.release_flags['29']='true';},
    p=>{p.sectors[1].mode='forecast';},
    p=>{p.sectors[2].forecast_months=[100.4];},
    p=>{p.sectors[0].projection=101;},
    p=>{p.sectors[0].reason='';},
    p=>{p.sectors[3].industry_code='28';},
    p=>{p.sectors.pop();}
  ]){const p=read();change(p);assert.throws(()=>verifySectorForecastStatus(p));}
});
test('unavailable release metadata preserves historical-only experience',()=>{
  assert.match(sectorAvailability(null,'28'),/unavailable/);
  assert.match(sectorAvailability(null,'C'),/Historical observations only/);
});
test('page includes accessible status and separate release payload',()=>{
  const html=readFileSync(new URL('../site/index.html',import.meta.url),'utf8');
  assert.match(html,/id="sector-forecast-status" role="status"/);
  assert.match(html,/sector-forecast-status\.mjs/);
  const contract=readFileSync(new URL('../site/data/sector-forecast-status.json',import.meta.url),'utf8');
  assert.doesNotMatch(contract,/"index_projection"|"forecast_months"/);
});
