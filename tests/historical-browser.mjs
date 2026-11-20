import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import {mkdir} from 'node:fs/promises';

const base='http://127.0.0.1:4173/';
const browser=await chromium.launch({headless:true});
await mkdir('qa-artifacts',{recursive:true});
const fixture=()=>{
  const sectors=[['C','42153-0001'],['20','42153-0002'],['24','42153-0002'],['28','42153-0002'],['29','42153-0002']];
  return {schema_version:'1.0.0',status:'validated',generated_at:'2026-11-19T12:00:00Z',
    series:sectors.map(([industry_code,dataset_id])=>({industry_code,dataset_id,
      source:'Destatis GENESIS',source_url:'https://genesis.destatis.de/datenbank/online/statistic/42153',
      geo:'DE',frequency:'M',unit:'index',base_year:2021,adjustment:'original',classification:'WZ2008',
      raw_sha256:'f'.repeat(64),acquisition_id:'mock-test-only-'+industry_code,
      retrieved_at:'2026-11-19T10:00:00Z',official_verification:true,publication_approved:true,
      observations:[{period:'2025-12',value:102.2,source_status_flags:[]},
        {period:'2026-01',value:null,source_status_flags:['suppressed'],missing_reason:'suppressed'},
        {period:'2026-02',value:101.6,source_status_flags:['provisional']}]
    }))};
};
try {
  for(const [mode,viewport] of [['desktop',{width:1365,height:900}],['mobile',{width:390,height:844}]]){
    const page=await browser.newPage({viewport});
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    // Exercise the actual committed release: no verified data, no fabricated rows.
    let res=await page.goto(base,{waitUntil:'networkidle'});
    assert.equal(res.status(),200);
    assert.equal(await page.locator('#historical-sector option').count(),5);
    assert.match(await page.locator('#historical-status').innerText(),/unavailable/i);
    assert.equal(await page.locator('#historical-rows tr').count(),0);
    assert.match(await page.locator('#sector-forecast-status').innerText(),/Historical observations only/i);
    await page.locator('#historical-sector').selectOption('28');
    assert.match(await page.locator('#sector-forecast-status').innerText(),/Machinery|Sector forecast unavailable/);
    await page.locator('#historical-sector').selectOption('29');
    assert.match(await page.locator('#sector-forecast-status').innerText(),/Automotive|Sector forecast unavailable/);
    await page.locator('#historical-sector').selectOption('24');
    assert.match(await page.locator('#sector-forecast-status').innerText(),/Basic metals|Sector forecast unavailable/);
    await page.locator('#historical-sector').selectOption('20');
    assert.match(await page.locator('#sector-forecast-status').innerText(),/Chemicals|Sector forecast unavailable/);
    assert.equal(await page.locator('#historical-chart polyline').count(),0);
    assert.equal(await page.locator('#historical-chart polyline').count(),0);
    await page.locator('#historical-sector').selectOption('28');
    await page.locator('#historical-range').selectOption('12');
    assert.equal(await page.locator('#historical-rows tr').count(),0);
    await page.screenshot({path:'qa-artifacts/historical-'+mode+'-empty.png',fullPage:true});

    // Intercept only in browser QA; synthetic values NEVER enter site/data.
    await page.route('**/data/historical.json',route=>route.fulfill({
      status:200,contentType:'application/json',body:JSON.stringify(fixture())
    }));
    await page.reload({waitUntil:'networkidle'});
    await page.locator('#historical-sector').selectOption('28');
    await page.locator('#historical-range').selectOption('12');
    assert.equal(await page.locator('#historical-rows tr').count(),3);
    assert.match(await page.locator('#historical-caption').innerText(),/2021 = 100/);
    assert.match(await page.locator('#historical-provenance').innerText(),/Destatis GENESIS/);
    assert.equal(await page.locator('#historical-rows tr').nth(1).locator('td').first().innerText(),'Unavailable');
    assert.equal(await page.locator('#historical-rows tr').nth(0).locator('td').first().innerText(),'102.2');
    assert.ok((await page.locator('#historical-chart polyline').count())===0,'No line connecting across missing month');
    assert.equal(await page.locator('#historical-chart circle').count(),2);
    if(mode==='mobile'){
      const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth);
      assert.ok(overflow<=2,'Mobile horizontal overflow '+overflow);
    }
    await page.screenshot({path:'qa-artifacts/historical-'+mode+'-mock-validated.png',fullPage:true});
    assert.deepEqual(errors,[],mode+' browser exceptions');
    await page.close();
  }
  console.log('HISTORICAL_BROWSER_QA_PASS: empty + synthetic-mocked five-industry views on desktop and mobile');
}finally{await browser.close();}
