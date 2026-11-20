import test from 'node:test';
import assert from 'node:assert/strict';
import {CASES, START_YEARS, LIMITS, ECONOMICS, validateState, interpret, calculateIllustrative, formatState} from '../site/scenario-command-core.mjs';
const base=()=>({scenario:'Central',productivity:1,start:2027,energy:0,comparison:'Central'});
const command=(text,s=base())=>interpret(text,s);
function accept(input,expected){const r=command(input);assert.equal(r.ok,true,input+': '+r.question);for(const [k,v] of Object.entries(expected))assert.equal(r.state[k],v,input+': '+k);return r;}
function reject(input,expected){const r=command(input);assert.equal(r.ok,false,input);assert.deepEqual(r.changes,{});if(expected)assert.match(r.question,expected);return r;}
test('source sensitivity is fixed, synthetic and bounded',()=>{
 assert.deepEqual(CASES,['Central','Resilience','Transformation']);
 assert.deepEqual(START_YEARS,[2027,2028,2029]);
 assert.deepEqual(LIMITS.productivity,[0,5]);assert.deepEqual(LIMITS.energy,[-3,3]);
 assert.equal(ECONOMICS.calibrated,false);assert.equal(ECONOMICS.baseIndex,100);assert.equal(ECONOMICS.energyCoefficient,-.35);
});
test('long executive instruction sets all fields without inference',()=>{
 const r=accept("Use FirmaBlick's Central Case for German industrial production. Assume a 3% annual productivity improvement from 2028. Hold energy prices constant in real terms. Show the resulting 2030 outlook and compare it against the Resilience Case.",{scenario:'Central',productivity:3,start:2028,energy:0,comparison:'Resilience'});
 assert.deepEqual(r.updatedFields.sort(),['comparison','energy','productivity','scenario','start']);
 assert.match(r.confirmation,/Illustrative scenario/);assert.match(r.confirmation,/No calibrated economic forecast/);
});
test('follow-ups preserve unnamed choices only in the same current tab state',()=>{
 let r=accept('Use Transformation case',{scenario:'Transformation'});
 r=command('Set productivity to 2.5%',r.state);assert.equal(r.ok,true,r.question);
 r=command('start in 2029',r.state);assert.equal(r.ok,true,r.question);
 r=command('energy -2.5%',r.state);assert.equal(r.ok,true,r.question);
 r=command('compare with None',r.state);assert.equal(r.ok,true,r.question);
 assert.deepEqual(r.state,{scenario:'Transformation',productivity:2.5,start:2029,energy:-2.5,comparison:'None'});
 assert.equal(command('show chart',base()).state.scenario,'Central');
});
test('comparison never overrides the selected primary case',()=>{
 accept('compare against Transformation',{scenario:'Central',comparison:'Transformation'});
 accept('set comparison to Resilience',{scenario:'Central',comparison:'Resilience'});
 accept('comparison to Central',{scenario:'Central',comparison:'Central'});
 accept('compare with none',{scenario:'Central',comparison:'None'});
});
test('supported field commands and decimal inputs',()=>{
 const examples=[
 ['scenario resilience',{scenario:'Resilience'}],
 ['set case to Transformation',{scenario:'Transformation'}],
 ['set productivity to 5%',{productivity:5}],
 ['assume a 0% productivity from 2027',{productivity:0,start:2027}],
 ['set the energy to -3%',{energy:-3}],
 ['energy +3%',{energy:3}],
 ['hold energy prices constant',{energy:0}],
 ['energy rises by 2%',{energy:2}],
 ['energy falls by 2%',{energy:-2}],
 ['start year 2028',{start:2028}],
 ['set energy to 2.1% and compare against Central',{energy:2.1,comparison:'Central'}]];
 for(const [text,expected] of examples)accept(text,expected);
});
test('unsupported requests are rejected without fabricating data',()=>{
 for(const text of ['Forecast German manufacturing revenue in euros','Summarize the latest Destatis statistics','Use an LLM to write the outlook','change the unemployment rate to 3%','raise interest rates','what happens next?','compare it with last year','set productivity from next month','make this more optimistic'])reject(text);
});
test('bounds and unsupported start years fail atomically',()=>{
 for(const text of ['set productivity to 5.1%','productivity -0.1%','energy 3.1%','energy -3.1%','start in 2030','start in 2026','productivity 2.25%','energy 0.05%','set productivity to 4% and energy 12%'])reject(text);
});
test('conflicting instructions abort entire turn',()=>{
 for(const text of ['set productivity to 2% and set productivity to 3%','use Central case and use Transformation case','energy -2% and energy +2%','set productivity to 2% from 2027 and start in 2029','compare with Central and compare with Resilience'])reject(text,/conflict/i);
});
test('negated and conditional statements never modify any parameter',()=>{
 for(const text of ["do not change productivity to 3%","don't change energy",'set productivity to 2% but not energy','never use Transformation','set productivity to 4% instead of 2%'])reject(text);
});
test('unknown trailing clauses reject the whole command',()=>{
 reject('Set productivity to 3%. Please do some complex macroeconomic modelling.');
 assert.deepEqual(command('show the 2030 outlook').changes,{});
 assert.equal(command('show the 2030 outlook').ok,true);
 assert.equal(command('please').ok,false);
 accept('set energy to 2%, set productivity to 3%',{energy:2,productivity:3});
});
test('human-readable confirmation matches the final controls',()=>{
 const r=accept('set productivity to 3% from 2028 and set energy to -1%',{productivity:3,start:2028,energy:-1});
 assert.match(r.confirmation,/productivity 3% from 2028/);assert.match(r.confirmation,/energy -1%/);
 assert.match(formatState(r.state),/compare with Central/);
});
test('pure illustrative engine changes index but never reports official data',()=>{
 const initial=calculateIllustrative(base());
 const growth=calculateIllustrative({...base(),productivity:4,start:2028});
 const high=calculateIllustrative({...base(),energy:3});
 const low=calculateIllustrative({...base(),energy:-3});
 assert.equal(initial.length,5);assert.equal(initial[0].index,100);
 const sameStart=calculateIllustrative({...base(),start:2028});
 assert.equal(sameStart[1].index,growth[1].index);
 assert.ok(growth[4].index>initial[4].index);
 assert.ok(low[4].index>high[4].index);
 assert.deepEqual(calculateIllustrative(base()),initial);
});
test('input validation blocks malformed control states and oversized messages',()=>{
 assert.throws(()=>validateState({...base(),start:2030}));
 assert.throws(()=>validateState({...base(),productivity:6}));
 assert.throws(()=>validateState({...base(),energy:5}));
 reject('set energy to 2% '+ 'x'.repeat(451));
 assert.equal(command('').ok,false);
});
