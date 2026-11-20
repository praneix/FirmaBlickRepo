/* Beta release evaluation. Never deploys and never alters evidence.
 * Declarative manifest fields alone cannot approve release.
 */
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {verifyHistoricalPayload} from '../site/historical-core.mjs';
import {verifySectorForecastStatus} from '../site/sector-forecast-status-core.mjs';

const ROOT=fileURLToPath(new URL('../',import.meta.url));
const SHA=/^[0-9a-f]{40}$/;
const DIGEST=/^[0-9a-f]{64}$/;
const ISO=/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z$/;
const VALID_STATES=new Set(['BLOCKED','REVIEW_PENDING','PREVIEW_APPROVED']);
const sourced=(x)=>typeof x==='string' && x.startsWith('https://') && !x.includes(' ');
const validTime=(value)=>typeof value==='string' && ISO.test(value) && !Number.isNaN(Date.parse(value));
function safeJson(path){return JSON.parse(readFileSync(resolve(ROOT,path),'utf8'));}
function add(blockers,cond,message){if(!cond)blockers.push(message);}

export function assessBeta(manifest,historical,sectorRelease,options={}){
  const blockers=[],errors=[];
  if(!manifest || manifest.schema_version!=='1.0.0'||!VALID_STATES.has(manifest.release_state))
    return {ready:false,blockers:['Release manifest invalid or absent.'],errors:['MANIFEST_INVALID'],verified:false};
  const data=manifest.historical_data||{}, model=manifest.aggregate_forecast||{};
  const ci=manifest.ci||{},preview=manifest.preview||{},manual=manifest.manual_approval||{};
  const deploy=manifest.deploy||{},privacy=manifest.privacy||{};
  add(blockers,typeof manifest.release_id==='string'&&manifest.release_id.length>3,'Release identifier missing.');
  add(blockers,SHA.test(manifest.git_sha||''),'Versioned Git commit SHA not pinned.');
  add(blockers,manifest.branch==='agent/prototype-2-44525788542','Unexpected release branch.');
  let series=null;
  try{
    const verified=verifyHistoricalPayload(historical);
    if(verified.status==='validated')series=verified.series;
    else blockers.push('Historical source acquisition and validation outstanding.');
  }catch(e){errors.push('HISTORICAL_DATA_INVALID');blockers.push('Historical source contract failed: '+e.message);}
  if(series){
    add(blockers,data.status==='validated','Manifest does not attest validated historical data.');
    const hashes=new Set(series.map(s=>s.raw_sha256));
    add(blockers,Array.isArray(data.original_source_sha256) && hashes.size===data.original_source_sha256.length
      && data.original_source_sha256.every(x=>DIGEST.test(x)&&hashes.has(x)),'Manifest source hashes do not match release.');
    add(blockers,validTime(data.source_vintage_utc),'Historical acquisition vintage absent.');
    if(validTime(data.source_vintage_utc)){
      add(blockers,series.every(s=>Date.parse(s.retrieved_at)<=Date.parse(data.source_vintage_utc)),
        'Source vintage earlier than one or more acquisitions.');
    }
    const spot=data.golden_spot_checks||{};
    add(blockers,spot.status==='verified'&&Array.isArray(spot.checks)&&spot.checks.length>=5 &&
      typeof spot.independent_reviewer==='string'&&spot.independent_reviewer.trim().length>2,
      'Independent five-series official golden-file review missing.');
    if(Array.isArray(spot.checks)){
      for(const x of spot.checks){
        add(blockers,!!x && sourced(x.source_url) && DIGEST.test(x.raw_sha256||'') &&
          Number.isFinite(x.source_value) && x.source_value===x.normalized_value &&
          typeof x.period==='string' && /^\d{4}-(0[1-9]|1[0-2])$/.test(x.period) &&
          ['C','20','24','28','29'].includes(x.industry_code),
          'Malformed golden-file comparison evidence.');
      }
      add(blockers,new Set(spot.checks.map(x=>x.industry_code)).size===5,
        'Official value spot checks do not cover all five industries.');
    }
    // Even apparent parity needs a separately trustworthy signed evidence pipeline;
    // static JSON alone cannot independently prove authenticated external provenance.
    add(blockers,options.officialEvidenceVerified===true,
      'Independent official-source attestation has not been performed by trusted release workflow.');
  }
  try{
    const sectors=verifySectorForecastStatus(sectorRelease);
    add(blockers,JSON.stringify(manifest.sector_forecasts?.release_flags)===JSON.stringify(sectors.release_flags),
      'Sector release state conflicts with independently pinned site release flags.');
  }catch(e){errors.push('SECTOR_RELEASE_INVALID');blockers.push('Sector publication isolation invalid: '+e.message);}
  add(blockers,model.model_id==='fb-manufacturing-seasonal-damped-trend'&&model.model_version==='1.0.0',
    'Aggregate model/version not pinned.');
  // Beta flagships require genuine model validation; the current engine is blocked.
  add(blockers,model.status==='validated'&&model.holdout_approved===true&&model.publication_approved===true &&
      sourced(model.benchmark_evidence),
      'Flagship forecast has not passed independent holdout and publication review.');
  add(blockers,options.forecastEvidenceVerified===true,
    'Trusted independent forecast-evaluation attestation missing.');
  add(blockers,SHA.test(ci.head_sha||'')&&ci.head_sha===manifest.git_sha,
    'CI head SHA does not match pinned release.');
  add(blockers,ci.unit_tests==='passed'&&ci.chromium_desktop==='passed'&&ci.chromium_mobile==='passed'&&
    ci.security_checks==='passed'&&sourced(ci.run_url),
    'Required CI, browser or security proof missing.');
  add(blockers,options.ciEvidenceVerified===true,
    'CI evidence has not been independently verified against the exact commit.');
  add(blockers,sourced(preview.url)&&preview.review_status==='approved'&&
    typeof preview.reviewer==='string'&&preview.reviewer.trim().length>2&&
    validTime(preview.approved_at),
    'Protected Vercel preview approval missing.');
  add(blockers,options.previewEvidenceVerified===true,
    'Vercel preview not independently tested with authorized access.');
  add(blockers,typeof manual.approver==='string'&&manual.approver.trim().length>2&&
    validTime(manual.approved_at)&&manual.approval_scope==='beta_preview',
    'Named owner has not approved beta preview release.');
  add(blockers,options.manualApprovalVerified===true,
    'Manual approval has not been established through a trusted GitHub Environment.');
  add(blockers,privacy.no_customer_data===true&&privacy.no_api_credentials_in_client===true&&privacy.analytics_enabled===false,
    'Privacy/security assurances incomplete.');
  add(blockers,options.securityAuditVerified===true,'Independent client-secret and privacy audit not verified.');
  // Production release is categorically outside this beta-preview gate.
  add(blockers,deploy.production_authorized===false&&deploy.dns_authorized===false,
    'Production/DNS authorization must remain false in beta assessment.');
  return {ready:blockers.length===0,blockers,errors,verified:blockers.length===0,
    action:blockers.length===0?'BETA_PREVIEW_REVIEW_ONLY':'BLOCK_RELEASE',
    productionAuthorized:false,dnsAuthorized:false};
}

export function currentReport(options={}){
  return assessBeta(safeJson('release/beta-manifest.v1.json'),
    safeJson('site/data/historical.json'),
    safeJson('site/data/sector-forecast-status.json'),options);
}
if(process.argv[1] && resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  const report=currentReport();
  process.stdout.write(JSON.stringify(report,null,2)+'\n');
  if(process.argv.includes('--assert-blocked')){
    if(report.ready||report.action!=='BLOCK_RELEASE'||report.blockers.length<3)
      process.exitCode=1;
  }else if(process.argv.includes('--require-preview-approved')){
    if(!report.ready)process.exitCode=2;
  }else if(!process.argv.includes('--report')){
    process.stderr.write('Use --report, --assert-blocked or --require-preview-approved.\n');
    process.exitCode=2;
  }
}
