import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import {mkdir} from 'node:fs/promises';

const base='http://127.0.0.1:4173/';
const slug='research/germany-industrial-energy-decision-report-2026/';
const browser=await chromium.launch({headless:true});
await mkdir('qa-artifacts',{recursive:true});
try{
 for(const [device,viewport] of [
   ['desktop',{width:1440,height:900}],
   ['mobile',{width:390,height:844}],
   ['small-mobile',{width:320,height:700}]
 ]){
  const page=await browser.newPage({viewport,deviceScaleFactor:1});
  const exceptions=[];page.on('pageerror',err=>exceptions.push(err.message));
  const home=await page.goto(base,{waitUntil:'networkidle'});
  assert.equal(home.status(),200,device+' homepage');
  assert.equal(await page.locator('.featured-research').count(),1,device+' exactly one legitimate report');
  assert.equal(await page.locator('[data-topic]').count(),0);
  assert.match(await page.locator('#research').innerText(),/Publication pending/i);
  const link=page.locator('.featured-research a[href*="germany-industrial-energy-decision-report-2026/"]').first();
  assert.ok(await link.isVisible());
  await link.click();
  await page.waitForLoadState('networkidle');
  assert.match(page.url(),/research\/germany-industrial-energy-decision-report-2026\/?$/);
  assert.match(await page.title(),/Industrial Power-Cost Decision/);
  assert.equal(await page.locator('meta[name="robots"]').getAttribute('content'),'noindex,nofollow');
  assert.equal(await page.locator('main#main').count(),1);
  assert.equal(await page.locator('nav[aria-label="Main navigation"]').count(),1);
  assert.equal(await page.locator('h1').count(),1);
  assert.equal(await page.locator('.report-rail-link').count(),6,'Six shortcuts for the report');
  assert.equal(await page.locator('.report-breadcrumbs a').count(),2,'Navigable breadcrumbs');
  assert.equal(await page.locator('#market-monthly-chart').getAttribute('data-source-verified'),'true','Plot actually verified monthly prices');
  assert.equal(await page.locator('#market-monthly-chart circle').count(),12,'Twelve source months plotted');
  assert.match(await page.locator('.market-chart-foot').innerText(),/ACTUAL 2025 MONTHLY AVERAGES/);
  assert.match(await page.locator('.report-scope-aside').innerText(),/EXECUTIVE READING GUIDE/);
  assert.equal(await page.locator('.scope-lens').count(),3);
  assert.match(await page.locator('.report-sources-heading small').innerText(),/Assumptions you can challenge/i);
  const snap=await page.evaluate(()=>getComputedStyle(document.body).scrollSnapType);
  if(device==='desktop')assert.match(snap,/^y(?: proximity)?$/,'Controlled desktop section snap');
  else assert.match(snap,/none/,'Avoid forced scroll snapping on small screens');
  await page.locator('.report-rail-link[href="#scope"]').click();
  assert.equal(await page.locator('.report-rail-link[href="#scope"]').getAttribute('aria-current'),'location');
  await page.locator('.report-rail-link[href="#preview"]').click();
  assert.equal(await page.locator('.report-rail-link[href="#preview"]').getAttribute('aria-current'),'location');
  assert.match(await page.locator('.report-approval').innerText(),/No orders are being accepted/);
  assert.equal(await page.locator('.report-insight').count(),4);
  assert.equal(await page.locator('.report-chapters article').count(),5);
  assert.match(await page.locator('#preview').innerText(),/€89.32\/MWh/);
  assert.match(await page.locator('#preview').innerText(),/€69,938/);
  assert.match(await page.locator('#exhibit-title').innerText(),/assumption-sensitive/i);
  assert.equal(await page.locator('#access button').isDisabled(),true,'No simulated checkout');
  assert.match(await page.locator('#access').innerText(),/Sample PDF: Pending/);
  assert.match(await page.locator('#access').innerText(),/No|not active|disabled/i);
  assert.equal(await page.locator('a[href$=".pdf"]').count(),0,'No unreleased PDF link');
  assert.equal(await page.locator('a[href*="/checkout/"]').count(),0,'No unapproved checkout URL');
  assert.doesNotMatch(await page.locator('#access').innerText(),/€149/,'No unapproved public price');
  assert.ok(await page.locator('a[href*="eurostat"]').count()>0);
  assert.ok(await page.locator('a[href*="smard.de"]').count()>0);
  const outbound=await page.locator('a[href*="smard.de"]').first().getAttribute('rel');
  assert.match(outbound,/noopener/);
  assert.match(await page.locator('.report-enquiry-link').innerText(),/advisory enquiry status/i);
  assert.match(await page.locator('.report-small').innerText(),/demonstration/i);
  const prices=await page.locator('.report-exhibit-bar').evaluateAll(els=>els.map(x=>({
   width:x.getBoundingClientRect().width,parent:x.parentElement.getBoundingClientRect().width
  })));
  assert.ok(prices.every(x=>x.width>0 && x.width<x.parent),'illustrative exhibit bars visible');
  const body=await page.locator('body').innerText();
  assert.doesNotMatch(body,/Example report|Logistical Chokepoints|European Automotive Supply Chains/);
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth);
  assert.ok(overflow<=2,device+' horizontal overflow: '+overflow);
  assert.deepEqual(exceptions,[],device+' page exceptions');
  if(device!=='small-mobile')await page.screenshot({path:'qa-artifacts/energy-landing-'+device+'.png',fullPage:true});
  await page.close();
 }
 console.log('ENERGY_REPORT_CATALOGUE_PASS: factual listing, protected preview, disabled purchase, source links, desktop/mobile screenshots');
}finally{await browser.close();}
