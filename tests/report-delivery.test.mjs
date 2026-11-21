import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFileSync} from 'node:fs';
const require=createRequire(import.meta.url);
const {SKU,REPORT_BUCKET,TTL_SECONDS,hashToken,validStoragePath,releaseReady,requireEnv,handle}=require('../server/report-delivery.cjs');
const reg=JSON.parse(readFileSync(new URL('../product/registry/energy-v4.review.json',import.meta.url),'utf8'));
const env={FB_DELIVERY_ENABLED:'true',FB_OWNER_PUBLICATION_APPROVED:'true',FB_SUPABASE_URL:'https://exampleproj.supabase.co',FB_SUPABASE_SECRET_KEY:'test-key-private'};
const raw='A'.repeat(43);
const digest=hashToken(raw);
const path=reg.versions[0].object_path;
const sha=reg.versions[0].full_pdf_sha256;
function makeResponse(){
 const h={};
 return {headers:h,statusCode:200,body:null,setHeader(k,v){h[k.toLowerCase()]=v;},end(data){this.body=data;}}
}
const req=(access_token=raw)=>({method:'POST',headers:{'content-type':'application/json','content-length':'60'},body:{access_token}});
async function perform({request=req(),config=env,fetchImpl=()=>{throw Error('Unexpected network request');}}={}){
 const res=makeResponse();
 await handle(request,res,{env:config,fetchImpl});
 return {status:res.statusCode,headers:res.headers,body:JSON.parse(res.body)};
}
test('review candidate remains unequivocally unpublished and digest-pinned',()=>{
 assert.equal(reg.report_id,SKU);
 assert.equal(reg.status,'review');
 assert.equal(reg.publication_approved,false);
 assert.equal(reg.price_approved,false);
 assert.equal(reg.versions.length,1);
 assert.equal(reg.versions[0].publication_approved,false);
 assert.equal(reg.versions[0].private_bucket,REPORT_BUCKET);
 assert.equal(reg.versions[0].full_pdf_sha256,sha);
 assert.equal(reg.versions[0].object_path.split('/').at(-1),sha+'.pdf');
 assert.equal(validStoragePath(path),true);
 const v={report_id:SKU,status:'review',publication_approved:false,rights_verified_at:null,owner_approved_at:null,full_pdf_sha256:sha,object_path:path};
 assert.equal(releaseReady(v,{enabled:false,owner_approved_at:null}),false);
 assert.equal(releaseReady({...v,status:'approved',publication_approved:true,rights_verified_at:'2026-11-21',owner_approved_at:'2026-11-21'},{enabled:true,owner_approved_at:'2026-11-21'}),true);
 assert.equal(releaseReady({...v,status:'approved',publication_approved:true,rights_verified_at:'2026-11-21',owner_approved_at:'2026-11-21'},{enabled:false,owner_approved_at:'2026-11-21'}),false);
});
test('storage paths block traversal and cross-bucket injection',()=>{
 for(const x of ['reports/../../secret.pdf','https://example.com/file.pdf','reports/FB-ENERGY-DE-2026-01/V4/x.pdf','reports/FB-ENERGY-DE-2026-01/V4/'+sha+'.pdf?public=true'])assert.equal(validStoragePath(x),false,x);
});
test('token must be 32-byte base64url and hashing is repeatable',()=>{
 assert.match(digest,/^[0-9a-f]{64}$/);
 assert.equal(hashToken(raw),digest);
 assert.equal(hashToken('abc'),null);
 assert.equal(hashToken(raw+'='),null);
});
test('closed by default even with valid access token',async()=>{
 const r=await perform({config:{...env,FB_DELIVERY_ENABLED:'false'}});
 assert.equal(r.status,503);assert.equal(r.body.error,'delivery_unavailable');
 assert.equal(r.headers['cache-control'],'no-store, max-age=0');
 assert.equal(requireEnv({}),null);
});
test('method, content-type, body and lengths fail closed',async()=>{
 let r=await perform({request:{...req(),method:'GET'}});assert.equal(r.status,405);
 r=await perform({request:{...req(),headers:{'content-type':'text/plain'}}});assert.equal(r.status,415);
 r=await perform({request:{...req(),body:{access_token:raw,report_id:SKU}}});assert.equal(r.status,400);
 r=await perform({request:req('bad')});assert.equal(r.status,400);
 r=await perform({request:{...req(),headers:{'content-type':'application/json','content-length':'999999'}}});assert.equal(r.status,413);
});
test('valid one-time token returns only 60 second private URL after RPC entitlement check',async()=>{
 const calls=[];
 const fetchImpl=async(url,options)=>{
  calls.push({url,options});
  if(url.includes('/rpc/'))return {ok:true,json:async()=>[{bucket:REPORT_BUCKET,report_id:SKU,revision:reg.versions[0].revision,full_pdf_sha256:sha,object_path:path}]};
  return {ok:true,json:async()=>({signedURL:'/storage/v1/object/sign/'+REPORT_BUCKET+'/'+path+'?token=server-issued'})};
 };
 const r=await perform({fetchImpl});
 assert.equal(r.status,200);
 assert.equal(r.body.sha256,sha);
 assert.equal(r.body.expires_in_seconds,TTL_SECONDS);
 assert.equal(calls.length,2);
 assert.equal(JSON.parse(calls[0].options.body).p_token_hash,digest);
 assert.ok(!calls[0].options.body.includes(raw));
 assert.equal(JSON.parse(calls[1].options.body).expiresIn,60);
 assert.ok(r.body.download_url.startsWith('https://exampleproj.supabase.co/storage/v1/object/sign/'));
 assert.equal(r.headers['cache-control'],'no-store, max-age=0');
});
test('unauthorized or replayed token cannot get signed link',async()=>{
 let times=0;
 const fetchImpl=async(url)=>{
  if(url.includes('/rpc/'))return ++times===1?
   {ok:true,json:async()=>[{bucket:REPORT_BUCKET,report_id:SKU,revision:'V4',full_pdf_sha256:sha,object_path:path}]}:
   {ok:false,status:400,json:async()=>({error:'ACCESS_DENIED'})};
  return {ok:true,json:async()=>({signedURL:'/storage/v1/object/sign/'+REPORT_BUCKET+'/'+path+'?token=x'})};
 };
 assert.equal((await perform({fetchImpl})).status,200);
 assert.equal((await perform({fetchImpl})).status,403);
});
test('wrong bucket, report, unsafe object, missing signed token or network outage fail closed',async()=>{
 for(const result of [
 {bucket:'public',report_id:SKU,object_path:path,full_pdf_sha256:sha},
 {bucket:REPORT_BUCKET,report_id:'other',object_path:path,full_pdf_sha256:sha},
 {bucket:REPORT_BUCKET,report_id:SKU,object_path:'../../secret',full_pdf_sha256:sha}
 ]){
  const r=await perform({fetchImpl:async()=>({ok:true,json:async()=>[result]})});
  assert.equal(r.status,403);
 }
 const failSign=async(url)=> url.includes('/rpc/')?
  {ok:true,json:async()=>[{bucket:REPORT_BUCKET,report_id:SKU,revision:'V4',full_pdf_sha256:sha,object_path:path}]}:
  {ok:true,json:async()=>({signedURL:'https://attacker.example/steal?token=x'})};
 assert.equal((await perform({fetchImpl:failSign})).status,503);
 assert.equal((await perform({fetchImpl:async()=>{throw Error('upstream');}})).status,503);
});
