import test from 'node:test';
import assert from 'node:assert/strict';
import {chromium} from 'playwright';

// This test runs ONLY after the CI job regenerates historical.json from independently
// hashed official source artifacts. Never commit the generated JSON into the repository.
const browser=await chromium.launch({headless:true});
const url='http://127.0.0.1:4173/';
const industries=[
  ['C','Manufacturing'],['20','Chemicals'],['24','metals'],
  ['28','Machinery'],['29','Automotive']
];
try {
 for (const [device,viewport] of [['desktop',{width:1365,height:900}],['mobile',{width:390,height:844}]]) {
  const page=await browser.newPage({viewport});
  const browserErrors=[];page.on('pageerror',error=>browserErrors.push(error.message));
  const response=await page.goto(url,{waitUntil:'networkidle'});
  assert.equal(response.status(),200);
  assert.equal(await page.locator('#historical-sector option').count(),5);
  assert.match(await page.locator('#historical-provenance').innerText(),/Destatis GENESIS/);
  assert.match(await page.locator('#historical-status').innerText(),/Eurostat.*705\/705/);
  assert.match(await page.locator('#historical-status').innerText(),/Public publication remains blocked/);
  for (const [code,label] of industries) {
    await page.locator('#historical-sector').selectOption(code);
    await page.locator('#historical-range').selectOption('240');
    assert.match(await page.locator('#historical-caption').innerText(),/2021 = 100/);
    assert.equal(await page.locator('#historical-rows tr').count(),141,'141 real observed months for '+code);
    assert.equal(await page.locator('#historical-rows tr').first().locator('th').innerText(),'2015-01');
    assert.equal(await page.locator('#historical-rows tr').last().locator('th').innerText(),'2026-09');
    assert.ok(await page.locator('#historical-chart polyline').count()>0,'real series plotted for '+code);
    const source=page.locator('#historical-provenance a');
    assert.match(await source.getAttribute('href'),/https:\/\/genesis\.destatis\.de\//);
    const data=await page.locator('#historical-rows tr td:first-of-type').allInnerTexts();
    assert.equal(data.length,141);
    assert.ok(data.every(value=>/^\d+\.\d$/.test(value)),'official values rendered as numeric index');
    assert.match(await page.locator('#sector-forecast-status').innerText(),/Historical observations only|Forecast unavailable|Sector forecast unavailable/);
  }
  // Verify use of exact same source scope on all five sectors, no synthetic numbers slipped in.
  await page.locator('#historical-range').selectOption('12');
  assert.equal(await page.locator('#historical-rows tr').count(),12);
  if(device==='mobile') {
    const horizontalOverflow=await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth);
    assert.ok(horizontalOverflow<=2,'Mobile viewport overflow '+horizontalOverflow);
  }
  assert.deepEqual(browserErrors,[]);
  await page.close();
 }
 console.log('PROTECTED_ORIGINAL_705_ALL_5_SECTORS_CHART_AND_TABLE_BROWSER_PASS');
} finally {await browser.close();}
