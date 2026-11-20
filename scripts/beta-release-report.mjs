/* Generate a non-authorizing CI evidence record for the exact tested SHA. */
import {mkdir,writeFile,readFile} from 'node:fs/promises';
const head=process.env.FIRMABLICK_TESTED_SHA || process.env.GITHUB_SHA || null;
const ref=process.env.GITHUB_REF_NAME||null;
const run=process.env.GITHUB_RUN_ID||null;
const repo=process.env.GITHUB_REPOSITORY||null;
const manifest=JSON.parse(await readFile(new URL('../release/beta-manifest.v1.json',import.meta.url),'utf8'));
const run_url=repo&&run?'https://github.com/'+repo+'/actions/runs/'+run:null;
const candidate={
  ...manifest,
  git_sha:head,
  evidence_record:{
    recorded_at:new Date().toISOString(),
    tested_git_sha:head,
    ci_execution_commit:process.env.GITHUB_SHA||null,
    ref,
    workflow_run_url:run_url,
    pipeline_status_at_generation:'running_not_yet_approved',
    source_manifest_version:'1.0.0',
  },
  ci:{
    ...manifest.ci,
    head_sha:head,
    run_url,
  },
  release_state:'BLOCKED',
};
const output=new URL('../release-artifacts/beta-candidate.json',import.meta.url);
await mkdir(new URL('../release-artifacts/',import.meta.url),{recursive:true});
await writeFile(output,JSON.stringify(candidate,null,2)+'\n',{mode:0o600});
process.stdout.write(JSON.stringify({result:'BETA_CANDIDATE_RECORDED_NOT_RELEASED',
  tested_sha:head,run_url,release_state:candidate.release_state})+'\n');
