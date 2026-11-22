import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';

const url='http://127.0.0.1:4173';
const browser=await chromium.launch({headless:true});
const issues=[];
await mkdir('qa-artifacts',{recursive:true});
try {
  for(const [label,viewport] of [['desktop',{width:1440,height:900}],['mobile',{width:390,height:844}]]) {
    const page=await browser.newPage({viewport,deviceScaleFactor:1});
    page.on('pageerror',e=>issues.push(label+' JavaScript: '+e.message));
    const response=await page.goto(url,{waitUntil:'networkidle'});
    assert.equal(response.status(),200,label+' homepage HTTP status');
    assert.match(await page.title(),/FirmaBlick/);
    await page.locator('#intelligence').scrollIntoViewIfNeeded();
    const baseline=await page.locator('#readout').textContent();
    await page.locator('#scenario').selectOption({label:'Transformation'});
    await page.locator('#productivity').fill('3');
    await page.locator('#start').selectOption('2028');
    await page.locator('#energy').fill('2');
    assert.match(await page.locator('#productivity-value').textContent(),/3%/);
    assert.match(await page.locator('#energy-value').textContent(),/2%/);
    assert.notEqual(await page.locator('#readout').textContent(),baseline);
    await page.locator('#comparison').selectOption('None');
    assert.equal(await page.locator('#comparison-key').isHidden(),true);
    assert.equal(await page.locator('#trajectory tr').count(),5);
    assert.equal(await page.locator('.featured-research').count(),1);
    assert.equal(await page.locator('a[href*="germany-industrial-energy-decision-report-2026/"]').count()>0,true);
    if(label==='mobile'){
      const width=await page.evaluate(()=>({body:document.documentElement.scrollWidth,viewport:innerWidth}));
      assert.ok(width.body<=width.viewport+2,JSON.stringify(width)+' horizontal overflow');
    }
    await page.screenshot({path:'qa-artifacts/'+label+'.png',fullPage:true});
    await page.close();
  }
  assert.deepEqual(issues,[],'Runtime JavaScript errors');
  console.log('BROWSER_QA_PASS: desktop and mobile interaction checks; screenshots saved');
} finally {await browser.close();}
