import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import {mkdir} from 'node:fs/promises';
const browser=await chromium.launch({headless:true});
await mkdir('qa-artifacts',{recursive:true});
const base='http://127.0.0.1:4173/';
const historicalSynthetic=()=>{
  const names=[['C','42153-0001'],['20','42153-0002'],['24','42153-0002'],['28','42153-0002'],['29','42153-0002']];
  return {schema_version:'1.0.0',status:'validated',generated_at:'2026-11-19T12:00:00Z',
    series:names.map(([industry_code,dataset_id])=>({
      industry_code,dataset_id,source:'Destatis GENESIS',
      source_url:'https://genesis.destatis.de/datenbank/online/statistic/42153',
      geo:'DE',frequency:'M',unit:'index',base_year:2021,adjustment:'original',
      classification:'WZ2008',raw_sha256:'a'.repeat(64),acquisition_id:'mock-'+industry_code,
      retrieved_at:'2026-11-19T10:00:00Z',official_verification:true,publication_approved:true,
      observations:[{period:'2026-01',value:101.2,source_status_flags:[]},
        {period:'2026-02',value:null,missing_reason:'suppressed',source_status_flags:['suppressed']},
        {period:'2026-03',value:100.5,source_status_flags:['provisional']}],
    }))
  };
};
try{
  for(const [mode,viewport] of [['desktop',{width:1365,height:900}],['mobile',{width:390,height:844}]]){
    const page=await browser.newPage({viewport});
    const exceptions=[];page.on('pageerror',e=>exceptions.push(e.message));
    await page.goto(base,{waitUntil:'networkidle'});
    // Fragment navigation & accessible landmark checks.
    assert.equal(await page.locator('nav[aria-label="Main navigation"]').count(),1);
    assert.equal(await page.locator('a.skip[href="#main"]').count(),1);
    assert.equal(await page.locator('main#main').count(),1);
    assert.ok(await page.locator('nav a[href="#historical"]').count()===1);
    await page.locator('nav a[href="#historical"]').click();
    assert.equal(new URL(page.url()).hash,'#historical');
    assert.equal(await page.locator('#historical-sector option').count(),5);
    assert.match(await page.locator('#historical-status').innerText(),/unavailable/i);
    assert.equal(await page.locator('#historical-rows tr').count(),0);
    assert.equal(await page.locator('#historical-chart polyline').count(),0);
    assert.match(await page.locator('#sector-forecast-status').textContent(),/historical observations only/i);
    const footer=page.locator('footer');
    assert.match(await footer.textContent(),/remotely hosted illustrative imagery/i);
    assert.match(await footer.textContent(),/jurisdiction-specific privacy notice/i);
    const form=page.locator('#contact-form');
    await page.locator('nav a[href="#contact"]').click();
    assert.equal(new URL(page.url()).hash,'#contact');
    assert.equal(await form.locator('input[type=email]').count(),1);
    // Browser's native email validation must prevent malformed demo input.
    await page.locator('#contact-name').fill('Test Only');
    await page.locator('#contact-email').fill('invalid-mail');
    await page.locator('#message').fill('Sample only');
    assert.equal(await page.locator('#contact-email').evaluate(el=>el.checkValidity()),false);
    // Invalid official dataset must never display manufactured numeric chart content.
    await page.route('**/data/historical.json',route=>route.fulfill({
      status:200,contentType:'application/json',body:JSON.stringify({
        ...historicalSynthetic(),series:[{industry_code:'C',dataset_id:'bad',value:999}]
      })
    }));
    await page.reload({waitUntil:'networkidle'});
    assert.match(await page.locator('#historical-status').textContent(),/unavailable/i);
    assert.equal(await page.locator('#historical-rows tr').count(),0);
    assert.equal(await page.locator('#historical-chart polyline').count(),0);
    // Mocked valid fixture tests citation link and semantic data table; NEVER committed.
    await page.unroute('**/data/historical.json');
    await page.route('**/data/historical.json',route=>route.fulfill({
      status:200,contentType:'application/json',body:JSON.stringify(historicalSynthetic())
    }));
    await page.reload({waitUntil:'networkidle'});
    await page.locator('#historical-sector').selectOption('28');
    assert.equal(await page.locator('#historical-rows tr').count(),3);
    const citation=page.locator('#historical-provenance a');
    assert.equal(await citation.count(),1);
    assert.match(await citation.getAttribute('href'),/^https:\/\/genesis\.destatis\.de\//);
    assert.equal(await citation.getAttribute('rel'),'noopener noreferrer');
    assert.equal(await page.locator('#historical-rows tr').nth(1).locator('td').first().textContent(),'Unavailable');
    assert.equal(await page.locator('#historical-rows tr').nth(0).locator('th').getAttribute('scope'),'row');
    // Source citation and invalid-data user experience are verified at both sizes.
    if(mode==='mobile'){
      const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth);
      assert.ok(overflow<=2,'Mobile horizontal overflow '+overflow);
    }
    await page.screenshot({path:'qa-artifacts/beta-'+mode+'.png',fullPage:true});
    assert.deepEqual(exceptions,[],mode+' page errors');
    await page.close();
  }
  console.log('BETA_BROWSER_QA_PASS: mobile navigation, accessible tables, citation, blocked invalid data, form validation, disclosures');
}finally{await browser.close();}
