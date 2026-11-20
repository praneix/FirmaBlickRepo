import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import {mkdir} from 'node:fs/promises';
const browser=await chromium.launch({headless:true});
await mkdir('qa-artifacts',{recursive:true});
const base='http://127.0.0.1:4173/';
const checks=[];
try{
 for(const [kind,viewport] of [['desktop',{width:1365,height:900}],['mobile',{width:390,height:844}]]){
  const context=await browser.newContext({viewport});
  const page=await context.newPage();
  const errors=[];const externalApiCalls=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',req=>{
    const u=req.url();
    if(/openai|anthropic|gemini|perplexity|chat\/completions|supabase/.test(u.toLowerCase()))externalApiCalls.push(u);
  });
  const response=await page.goto(base,{waitUntil:'networkidle'});
  assert.equal(response.status(),200);
  assert.equal(await page.locator('#ask-command').isVisible(),true);
  assert.match(await page.locator('#scenario-assumptions').textContent(),/synthetic and uncalibrated/i);
  async function submit(value){
    await page.locator('#ask-command').fill(value);
    await page.locator('#ask-form button').click();
    return page.locator('#ask-result').textContent();
  }
  const original=await page.locator('#readout').textContent();
  const full="Use FirmaBlick's Transformation Case for German industrial production. Assume a 3% annual productivity improvement from 2028. Hold energy prices constant in real terms. Show the resulting 2030 outlook and compare it against the Resilience Case.";
  const confirmation=await submit(full);
  assert.match(confirmation,/Illustrative scenario updated/);
  assert.equal(await page.locator('#scenario').inputValue(),'Transformation');
  assert.equal(await page.locator('#productivity').inputValue(),'3');
  assert.equal(await page.locator('#start').inputValue(),'2028');
  assert.equal(await page.locator('#energy').inputValue(),'0');
  assert.equal(await page.locator('#comparison').inputValue(),'Resilience');
  assert.notEqual(await page.locator('#readout').textContent(),original);
  assert.equal(await page.locator('#trajectory tr').count(),5);
  const previous=await page.locator('#readout').textContent();
  const follow=await submit('set energy to -2%');
  assert.match(follow,/energy -2%/);
  assert.equal(await page.locator('#energy').inputValue(),'-2');
  assert.equal(await page.locator('#productivity').inputValue(),'3');
  assert.notEqual(await page.locator('#readout').textContent(),previous);
  const before=await page.locator('#readout').textContent();
  const conflict=await submit('set productivity to 2% and set productivity to 4%');
  assert.match(conflict,/conflicting/i);
  assert.equal(await page.locator('#readout').textContent(),before);
  assert.equal(await page.locator('#productivity').inputValue(),'3');
  const unsupported=await submit('Forecast company revenues in euro');
  assert.match(unsupported,/cannot safely interpret/i);
  assert.equal(await page.locator('#readout').textContent(),before);
  await page.locator('#energy').fill('1');
  await page.locator('#energy').dispatchEvent('input');
  assert.match(await page.locator('#scenario-assumptions').textContent(),/energy \+1%/);
  assert.equal(await page.locator('#ask-result').getAttribute('role'),'status');
  await page.screenshot({path:'qa-artifacts/scenario-'+kind+'.png',fullPage:true});
  if(kind==='mobile'){
    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth);
    assert.ok(overflow<=2,'Mobile horizontal overflow: '+overflow);
  }
  // A freshly opened tab has default values. No local/session storage used.
  const newPage=await context.newPage();
  await newPage.goto(base,{waitUntil:'networkidle'});
  assert.equal(await newPage.locator('#scenario').inputValue(),'Central');
  assert.equal(await newPage.locator('#productivity').inputValue(),'1');
  await newPage.close();
  assert.deepEqual(errors,[],kind+' JavaScript errors');
  assert.deepEqual(externalApiCalls,[],kind+' unexpected API calls');
  checks.push(kind);
  await context.close();
 }
 console.log('SCENARIO_BROWSER_QA_PASS: '+checks.join(', ')+': updates, table, no mutation on error, fresh tab, privacy and mobile checked');
}finally{await browser.close();}
