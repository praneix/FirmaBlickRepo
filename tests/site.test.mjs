import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';

const html = readFileSync(new URL('../site/index.html', import.meta.url),'utf8');
const script = readFileSync(new URL('../site/site.mjs', import.meta.url),'utf8');

function boot() {
  const defaults = {scenario:'Central',productivity:'1',start:'2027',energy:'0',comparison:'Central',topic:'all'};
  const elements = new Map();
  for (const [id,value] of Object.entries(defaults)) elements.set(id,{
    value, listeners:{}, addEventListener(evt,cb){this.listeners[evt]=cb;},
    trigger(){this.listeners.input?.();}
  });
  for (const id of ['productivity-value','energy-value','readout','primary-key','comparison-key','trajectory','chart','contact-status'])
    elements.set(id,{value:'',textContent:'',innerHTML:'',hidden:false});
  const button={disabled:true};
  const contact={listeners:{},addEventListener(evt,cb){this.listeners[evt]=cb;},
    querySelector(){return button;},reset(){this.resetCalled=true;}};
  elements.set('contact-form',contact);
  const reports=['Energy & Transition','Automotive','Supply Chain'].map(topic=>({dataset:{topic},hidden:false}));
  const document={getElementById(id){assert.ok(elements.has(id),'Missing DOM fixture '+id);return elements.get(id);},
    querySelectorAll(){return reports;}};
  runInNewContext(script,{document,console});
  return {elements,contact,button,reports};
}

test('page contains navigation, labelled illustrative scenario and accessible table',()=>{
  for (const id of ['home','intelligence','research','methodology','contact','scenario','productivity','start','energy','comparison','chart','trajectory'])
    assert.ok(html.includes('id="'+id+'"'),id);
  assert.match(html,/Illustrative values only/);
});
test('five years of trajectory and dynamic scenario controls',()=>{
  const {elements:e}=boot();
  assert.equal((e.get('trajectory').innerHTML.match(/<tr>/g)||[]).length,5);
  const before=e.get('readout').textContent;
  e.get('scenario').value='Transformation';
  e.get('productivity').value='3';
  e.get('start').value='2028';
  e.get('energy').value='2';
  e.get('scenario').trigger();
  assert.notEqual(e.get('readout').textContent,before);
  assert.equal(e.get('productivity-value').value,'3%');
  assert.equal(e.get('energy-value').value,'+2%');
  assert.match(e.get('primary-key').textContent,/Transformation/);
  e.get('comparison').value='None';e.get('comparison').trigger();
  assert.equal(e.get('comparison-key').hidden,true);
});
test('changing energy affects output while preserving other assumptions',()=>{
  const {elements:e}=boot();
  const index=()=>Number(e.get('readout').textContent.match(/Adjusted ([0-9.]+)/)?.[1]);
  e.get('energy').value='-3';e.get('energy').trigger();const low=index();
  e.get('energy').value='3';e.get('energy').trigger();const high=index();
  assert.ok(low>high,low+' must exceed '+high);
  assert.equal(e.get('scenario').value,'Central');
});
test('research topics are filtered without removing cards',()=>{
  const {elements:e,reports}=boot();
  e.get('topic').value='Automotive';e.get('topic').trigger();
  assert.deepEqual(reports.map(r=>r.hidden),[true,false,true]);
});
test('contact form clearly behaves as a local preview',()=>{
  const {elements:e,contact,button}=boot();
  assert.equal(button.disabled,false);
  let prevented=false;
  contact.listeners.submit({preventDefault(){prevented=true;}});
  assert.equal(prevented,true);
  assert.equal(contact.resetCalled,true);
  assert.match(e.get('contact-status').textContent,/No enquiry was sent/);
});
