'use strict';
const { createHash, timingSafeEqual } = require('node:crypto');

const SKU = 'FB-ENERGY-DE-2026-01';
const SHA256 = /^[0-9a-f]{64}$/;
const TOKEN = /^[A-Za-z0-9_-]{43}$/;
const REPORT_BUCKET = 'firmablick-paid-reports';
const TTL_SECONDS = 60;

function validDigest(value) { return typeof value === 'string' && SHA256.test(value); }
function validStoragePath(value) {
  return typeof value === 'string' && value.length >= 20 && value.length <= 240 &&
    /^reports\/[A-Za-z0-9-]+\/[A-Za-z0-9._-]+\/[0-9a-f]{64}\.pdf$/.test(value) &&
    !value.includes('..');
}
function releaseReady(version, globalControl) {
  return !!version && !!globalControl &&
    version.report_id === SKU &&
    version.status === 'approved' &&
    version.publication_approved === true &&
    version.rights_verified_at !== null &&
    version.rights_verified_at !== undefined &&
    version.owner_approved_at !== null &&
    version.owner_approved_at !== undefined &&
    validDigest(version.full_pdf_sha256) &&
    validStoragePath(version.object_path) &&
    globalControl.enabled === true &&
    globalControl.owner_approved_at !== null &&
    globalControl.owner_approved_at !== undefined;
}
function requireEnv(env) {
  if (env.FB_DELIVERY_ENABLED !== 'true' || env.FB_OWNER_PUBLICATION_APPROVED !== 'true') return null;
  const url = env.FB_SUPABASE_URL;
  const key = env.FB_SUPABASE_SECRET_KEY;
  if (typeof url !== 'string' || typeof key !== 'string' || !key || !/^https:\/\/[a-z0-9-]+\.supabase\.co\/?$/.test(url)) return null;
  return { url: url.replace(/\/$/, ''), key };
}
function hashToken(token) {
  if (typeof token !== 'string' || !TOKEN.test(token)) return null;
  return createHash('sha256').update(token, 'utf8').digest('hex');
}
function secretMatchesDigest(a, b) {
  if (!validDigest(a) || !validDigest(b)) return false;
  return timingSafeEqual(Buffer.from(a,'hex'), Buffer.from(b,'hex'));
}
function noCache(res) {
  res.setHeader('Cache-Control','no-store, max-age=0');
  res.setHeader('Pragma','no-cache');
  res.setHeader('Referrer-Policy','no-referrer');
  res.setHeader('X-Content-Type-Options','nosniff');
}
function reply(res,status,message) { res.statusCode=status; res.end(JSON.stringify({error:message})); }
async function handle(req,res,{env=process.env,fetchImpl=globalThis.fetch}={}) {
  res.setHeader('Content-Type','application/json; charset=utf-8');
  noCache(res);
  if(req.method !== 'POST'){res.setHeader('Allow','POST');return reply(res,405,'method_not_allowed');}
  const config=requireEnv(env);
  if(!config) return reply(res,503,'delivery_unavailable');
  const contentLength=Number(req.headers?.['content-length'] ?? 0);
  if(!Number.isFinite(contentLength) || contentLength>2048) return reply(res,413,'invalid_request');
  const type=(req.headers?.['content-type']??'').toLowerCase();
  if(!type.startsWith('application/json')) return reply(res,415,'invalid_request');
  const body=req.body;
  if(!body || Array.isArray(body) || typeof body!=='object' || Object.keys(body).length!==1) return reply(res,400,'invalid_request');
  const digest=hashToken(body.access_token);
  if(!digest) return reply(res,400,'invalid_request');
  try {
    // This single DB call atomically checks paid-provider verification, both
    // publication approvals, unexpired entitlement and single-use access token.
    const verify=await fetchImpl(config.url+'/rest/v1/rpc/fb_redeem_report_token',{
      method:'POST',headers:{'apikey':config.key,'Authorization':'Bearer '+config.key,'Content-Type':'application/json'},
      body:JSON.stringify({p_token_hash:digest}),signal:AbortSignal.timeout(6000)
    });
    if(!verify.ok) return reply(res,403,'access_unavailable');
    const values=await verify.json();
    if(!Array.isArray(values) || values.length!==1) return reply(res,403,'access_unavailable');
    const item=values[0];
    if(item.bucket!==REPORT_BUCKET || item.report_id!==SKU ||
       !validDigest(item.full_pdf_sha256) || !validStoragePath(item.object_path)) return reply(res,403,'access_unavailable');
    // Supabase signed download links are time-limited and cannot be individually
    // revoked. Keep the TTL short and never return a public object URL.
    const encoded=item.object_path.split('/').map(encodeURIComponent).join('/');
    const response=await fetchImpl(config.url+'/storage/v1/object/sign/'+REPORT_BUCKET+'/'+encoded,{
      method:'POST',headers:{'apikey':config.key,'Authorization':'Bearer '+config.key,'Content-Type':'application/json'},
      body:JSON.stringify({expiresIn:TTL_SECONDS}),signal:AbortSignal.timeout(6000)
    });
    if(!response.ok) return reply(res,503,'delivery_unavailable');
    const data=await response.json();
    if(typeof data.signedURL!=='string' || !data.signedURL.startsWith('/storage/v1/object/sign/'+REPORT_BUCKET+'/') ||
       !data.signedURL.includes('token=')) return reply(res,503,'delivery_unavailable');
    res.statusCode=200;
    res.end(JSON.stringify({download_url:config.url+data.signedURL,expires_in_seconds:TTL_SECONDS,report_id:item.report_id,revision:item.revision,sha256:item.full_pdf_sha256}));
  } catch {
    return reply(res,503,'delivery_unavailable');
  }
}
module.exports={SKU, REPORT_BUCKET, TTL_SECONDS,hashToken,validDigest,validStoragePath,releaseReady,requireEnv,handle};
