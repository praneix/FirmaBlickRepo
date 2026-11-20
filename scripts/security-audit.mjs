/* Repository-local static safety audit. No API credentials, login or network use. */
import {readFileSync,readdirSync,statSync} from 'node:fs';
import {join,relative,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
const ROOT=fileURLToPath(new URL('../',import.meta.url));
const CLIENT=resolve(ROOT,'site');
const suspiciousNames=/(?:^|\/)(?:\.env(?:\..+)?|id_rsa|id_ed25519|.*\.pem|.*\.p12|.*\.key)$/i;
const sensitiveValues=[
  /-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----/,
  /\b(?:ghp|gho|ghu|ghs|ghr)_[a-zA-Z0-9]{30,}\b/,
  /\bsk-(?:proj-)?[a-zA-Z0-9_-]{20,}\b/,
  /\b(?:GENESIS_TOKEN|SUPABASE_SERVICE_ROLE_KEY|ANTHROPIC_API_KEY|OPENAI_API_KEY)\s*[:=]\s*['"][^'"]{12,}/,
  /https?:\/\/[^/\s]+:[^@\s]+@[^/\s]+/,
];
const riskyApi=/(?:fetch|XMLHttpRequest|sendBeacon)\s*\([^)]*(?:api\.openai|api\.anthropic|api\.perplexity|supabase)/i;
const allowedRemoteOrigins=new Set(['https://fonts.googleapis.com','https://lh3.googleusercontent.com']);
function scan(dir){
  const problems=[],seen=[];
  function descend(p){
    for(const ent of readdirSync(p,{withFileTypes:true})){
      const filename=join(p,ent.name),short=relative(CLIENT,filename).replaceAll('\\','/');
      if(ent.isSymbolicLink()){problems.push('Client symlink prohibited: '+short);continue;}
      if(ent.isDirectory()){descend(filename);continue;}
      if(!ent.isFile())continue;
      seen.push(short);
      if(suspiciousNames.test(short))problems.push('Credential-like public filename: '+short);
      const ext=short.split('.').at(-1).toLowerCase();
      if(!['html','mjs','js','json','css','txt','svg','md'].includes(ext))continue;
      const raw=readFileSync(filename,'utf8');
      for(const p of sensitiveValues)if(p.test(raw))problems.push('Sensitive token pattern in '+short);
      if(riskyApi.test(raw))problems.push('Unexpected private API usage in '+short);
    }
  }
  descend(dir);
  return {files:seen.sort(),problems};
}
export function securityAudit(){
  const {files,problems}=scan(CLIENT);
  const html=readFileSync(join(CLIENT,'index.html'),'utf8');
  for(const source of html.matchAll(/(?:src|href)="(https?:\/\/[^"]+)"/g)){
    try{const origin=new URL(source[1]).origin;
      if(!allowedRemoteOrigins.has(origin))problems.push('Unreviewed third-party resource: '+origin);
    }catch{problems.push('Invalid external resource URL.');}
  }
  const vercel=JSON.parse(readFileSync(join(ROOT,'vercel.json'),'utf8'));
  const headers=Object.fromEntries((vercel.headers||[]).flatMap(rule=>
    rule.headers.map(h=>[h.key.toLowerCase(),h.value])));
  const csp=headers['content-security-policy']||'';
  for(const directive of ["script-src 'self'","connect-src 'self'","object-src 'none'",
                           "frame-ancestors 'none'","form-action 'self'"]){
    if(!csp.includes(directive))problems.push('Required CSP directive missing: '+directive);
  }
  for(const h of ['x-content-type-options','referrer-policy','permissions-policy']){
    if(!headers[h])problems.push('Missing security response header: '+h);
  }
  if(csp.includes("'unsafe-inline'")||csp.includes("'unsafe-eval'"))
    problems.push('CSP permits unsafe inline/eval execution.');
  for(const marker of ['Placeholder pending legal review','Actual Destatis observations now live']){
    if(html.includes(marker))problems.push('Misleading or placeholder public copy: '+marker);
  }
  for(const disclosure of ['external resources','synthetic','legally required identifying information']){
    if(!html.toLowerCase().includes(disclosure))problems.push('Required prototype disclosure absent: '+disclosure);
  }
  return {passed:problems.length===0,problems,files_checked:files.length,
    external_assets:[...allowedRemoteOrigins],telemetry:'no first-party analytics configured',
    mode:'static repository audit, not live penetration test'};
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  const result=securityAudit();process.stdout.write(JSON.stringify(result,null,2)+'\n');
  if(!result.passed)process.exitCode=1;
}
