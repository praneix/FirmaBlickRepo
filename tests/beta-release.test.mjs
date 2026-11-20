import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {assessBeta,currentReport} from '../scripts/beta-release-gate.mjs';
import {securityAudit} from '../scripts/security-audit.mjs';

const from=(path)=>JSON.parse(readFileSync(new URL('../'+path,import.meta.url),'utf8'));
const fixtures=()=>[from('release/beta-manifest.v1.json'),from('site/data/historical.json'),
  from('site/data/sector-forecast-status.json')];
const forgedReview=()=>({
  officialEvidenceVerified:true,forecastEvidenceVerified:true,ciEvidenceVerified:true,
  previewEvidenceVerified:true,manualApprovalVerified:true,securityAuditVerified:true,
});
test('versioned release manifest reflects actual unavailable official source and blocks beta',()=>{
 const [m,h,s]=fixtures();
 assert.equal(m.schema_version,'1.0.0');
 assert.equal(m.release_state,'BLOCKED');
 assert.equal(m.git_sha,null);
 assert.equal(h.status,'unavailable');
 assert.equal(s.publication_approved,false);
 const r=currentReport();
 assert.equal(r.ready,false);assert.equal(r.action,'BLOCK_RELEASE');
 assert.equal(r.productionAuthorized,false);assert.equal(r.dnsAuthorized,false);
 assert.ok(r.blockers.length>=5);
 assert.match(r.blockers.join(' | '),/Historical source|official|Golden/i);
});
test('synthetic fixtures and self-attested approvals do not unlock release',()=>{
 const [m,h,s]=fixtures();
 Object.assign(m,{git_sha:'a'.repeat(40),release_state:'PREVIEW_APPROVED'});
 m.ci={head_sha:m.git_sha,run_url:'https://github.com/praneix/FirmaBlickRepo/actions/runs/1',
 unit_tests:'passed',chromium_desktop:'passed',chromium_mobile:'passed',security_checks:'passed'};
 m.preview={url:'https://example.vercel.app',review_status:'approved',reviewer:'Test Reviewer',
 approved_at:'2026-11-20T00:00:00Z'};
 m.manual_approval={approver:'Test Owner',approved_at:'2026-11-20T00:00:00Z',
 approval_scope:'beta_preview'};
 m.aggregate_forecast={status:'validated',model_id:'fb-manufacturing-seasonal-damped-trend',
 model_version:'1.0.0',holdout_approved:true,publication_approved:true,
 benchmark_evidence:'https://github.com/example/valid'};
 m.historical_data.status='validated';
 const r=assessBeta(m,h,s,forgedReview());
 assert.equal(r.ready,false);
 assert.match(r.blockers.join(' | '),/Historical source|source acquisition/);
});
test('malformed historical data and forged sector release fail closed',()=>{
 const [m,h,s]=fixtures();
 h.status='validated';h.reason='';h.series=[{industry_code:'C',value:100}];
 s.release_flags['28']=true;
 const r=assessBeta(m,h,s);
 assert.equal(r.ready,false);
 assert.ok(r.errors.includes('HISTORICAL_DATA_INVALID'));
 assert.ok(r.errors.includes('SECTOR_RELEASE_INVALID'));
});
test('no CI proof / approver / preview access blocks beta independently',()=>{
 const [m,h,s]=fixtures();
 const r=assessBeta(m,h,s);
 const desc=r.blockers.join(' | ');
 assert.match(desc,/CI head SHA/);
 assert.match(desc,/Vercel preview|preview approval/);
 assert.match(desc,/Named owner/);
 assert.match(desc,/GitHub Environment/);
});
test('production and DNS are explicitly forbidden inside beta preview gate',()=>{
 const [m,h,s]=fixtures();
 m.deploy.production_authorized=true;m.deploy.dns_authorized=true;
 const r=assessBeta(m,h,s,forgedReview());
 assert.equal(r.productionAuthorized,false);
 assert.equal(r.dnsAuthorized,false);
 assert.match(r.blockers.join(' | '),/Production\/DNS authorization/);
});
test('site source is free of secret patterns and has hardened response headers',()=>{
 const r=securityAudit();
 assert.equal(r.passed,true,r.problems.join('; '));
 assert.ok(r.files_checked>=5);
 const v=from('vercel.json');
 const headers=v.headers.flatMap(x=>x.headers);
 assert.ok(headers.find(x=>x.key==='Content-Security-Policy'));
 assert.ok(headers.find(x=>x.key==='X-Content-Type-Options'));
});
test('release manifest captures source/model/approval while making no false success claim',()=>{
 const [m]=fixtures();
 assert.deepEqual(Object.keys(m.sector_forecasts.release_flags).sort(),['20','24','28','29']);
 assert.ok(m.historical_data.golden_spot_checks);
 assert.ok(m.aggregate_forecast.model_version);
 assert.ok(Object.hasOwn(m,'manual_approval'));
 assert.ok(Object.hasOwn(m,'preview'));
 assert.ok(Object.hasOwn(m,'ci'));
 assert.equal(m.manual_approval.approver,null);
 assert.equal(m.preview.url,null);
 assert.equal(m.deploy.production_authorized,false);
});
test('legal notices describe remote resources, demo contact and data distinction',()=>{
 const html=readFileSync(new URL('../site/index.html',import.meta.url),'utf8');
 assert.match(html,/remotely hosted illustrative imagery/);
 assert.match(html,/form does not transmit/);
 assert.match(html,/2030 scenario trajectories are synthetic/);
 assert.match(html,/legally required identifying information/);
 assert.doesNotMatch(html,/Placeholder pending legal review/);
});
