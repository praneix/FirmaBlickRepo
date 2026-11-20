/* FirmaBlick V1 deterministic scenario-command grammar.
 * Zero network calls, no storage or LLM. Commands are atomic: any unrecognized
 * or conflicting clause rejects the entire turn and preserves all controls.
 */
export const CASES = Object.freeze(['Central','Resilience','Transformation']);
export const START_YEARS = Object.freeze([2027,2028,2029]);
export const LIMITS = Object.freeze({productivity:[0,5],energy:[-3,3]});
export const ECONOMICS = Object.freeze({
  growthRates:Object.freeze({Central:0.8,Resilience:1.4,Transformation:2.2}),
  energyCoefficient:-0.35,
  baseYear:2026,
  baseIndex:100,
  calibrated:false,
  source:'Illustrative synthetic assumptions; no Destatis-calibrated causal coefficients.'
});

const number='([+-]?(?:\\d+(?:\\.\\d+)?|\\.\\d+))';
const caseName='(central|resilience|transformation)';
const pattern=(x)=>new RegExp('^'+x+'$','i');
const trim=(s)=>s.trim().replace(/\s+/g,' ');

function normalize(text) {
  if (typeof text!=='string') return '';
  return text.trim().replace(/[−–—]/g,'-').replace(/[’]/g,"'")
    .replace(/[%]/g,'%').replace(/\s+/g,' ').toLowerCase();
}
function parseDecimal(raw,name,min,max) {
  if (raw==null || !/^[+-]?(?:\d+(?:\.\d+)?|\.\d+)$/.test(raw)) throw Error('Invalid '+name+' value.');
  const v=Number(raw);
  if (!Number.isFinite(v)||v<min||v>max) throw Error(name+' must be between '+min+'% and +'+max+'%.');
  if (!Number.isInteger(Math.round(v*10)) || Math.abs(Math.round(v*10)/10-v)>1e-9) throw Error(name+' supports 0.1 percentage-point increments.');
  return Math.round(v*10)/10;
}
function canonicalCase(v){return CASES.find(x=>x.toLowerCase()===v.toLowerCase());}
function segments(text){
  return text.replace(/\b(?:and then|then)\b/gi, ';')
    .replace(/\s+and\s+(?=(?:compare|set|use|choose|switch|change|make|assume|start|begin|hold|keep|energy|productivity|the\s+energy|the\s+productivity|show)\b)/gi, ';')
    .split(/(?:\.(?!\d)|[;\n])+|,(?=\s*(?:compare|set|use|choose|switch|change|make|assume|start|begin|hold|keep|energy|productivity|the\s+energy|the\s+productivity|show)\b)/i)
    .map(trim).filter(Boolean);
}
function clauseMatches(raw) {
  let s=normalize(raw);
  if(!s)return null;
  if (/\b(?:don't|do not|never|stop|avoid|ignore|without|except|instead of|rather than|not)\b/.test(s) && !/\bcompare\s+(?:with|against|to)\s+none\b/.test(s))
    return {error:'Negated or conditional commands require explicit clarification; no settings changed.'};
  s=s.replace(/\bplease\b/g,'').replace(/\bfirmablick's\b/g,'')
     .replace(/\bfor german industrial production\b/g,'')
     .replace(/\bin real terms\b/g,'')
     .replace(/\bthe resulting\b/g,'')
     .replace(/\bannual\b/g,'')
     .replace(/\bimprovement\b/g,'')
     .replace(/\bprices?\b/g,'')
     .replace(/\bpercentage points?\b/g,'%')
     .replace(/\bper year\b/g,'')
     .replace(/\bby\b(?=\s+[+-]?\d)/g,'to')
     .replace(/\s+/g,' ').trim();
  let m;
  // A show/read command changes no assumptions, but can coexist with updates.
  if(pattern('(?:show|display|view|plot)(?:\\s+(?:the|my|a))?\\s+(?:(?:2030|current)\\s+)?(?:outlook|trajectory|results?|chart|comparison)(?:\\s+for\\s+2030)?').test(s))
    return {view:true};
  // Compare is recognized BEFORE case to prevent accidental primary-case changes.
  if ((m=s.match(pattern('(?:compare(?:\\s+(?:it|this|the\\s+result))?\\s+(?:with|against|to)|comparison\\s+(?:to|with|against|is|=)|set\\s+comparison\\s+to)\\s+(none|central|resilience|transformation)(?:\\s+case|\\s+scenario)?'))))
    return {field:'comparison',value: m[1]==='none'?'None':canonicalCase(m[1])};
  if ((m=s.match(pattern('(?:use|choose|select|switch\\s+to|set(?:\\s+(?:the|my))?\\s+(?:scenario|case)\\s+(?:to|as|=)|change(?:\\s+(?:the|my))?\\s+(?:scenario|case)\\s+to)\\s+'+caseName+'(?:\\s+case|\\s+scenario)?'))))
    return {field:'scenario',value:canonicalCase(m[1])};
  if ((m=s.match(pattern('(?:scenario|case)(?:\\s+is|\\s*=|\\s+to)?\\s+'+caseName+'(?:\\s+case|\\s+scenario)?'))))
    return {field:'scenario',value:canonicalCase(m[1])};
  // Numeric-first phrase: "assume a 3% productivity improvement from 2028".
  if ((m=s.match(pattern('(?:assume|use|set|make)?\\s*(?:a|an|the)?\\s*'+number+'\\s*%?\\s*productivity(?:\\s+(?:gain|increase))?(?:\\s+(?:from|starting|beginning|starting\\s+in)\\s+(2027|2028|2029))?'))))
    return {field:'productivity',value:m[1],start:m[2]};
  if ((m=s.match(pattern('(?:set|change|move|adjust|make|assume|use)?\\s*(?:the\\s+)?productivity(?:\\s+(?:gain|increase))?\\s*(?:to|at|=|of|is)?\\s*'+number+'\\s*%?(?:\\s+(?:from|starting|beginning|starting\\s+in)\\s+(2027|2028|2029))?'))))
    return {field:'productivity',value:m[1],start:m[2]};
  if((m=s.match(pattern('(?:start|begin)(?:\\s+(?:productivity|the\\s+productivity))?\\s+(?:in|from|at)\\s+(2027|2028|2029)'))))
    return {field:'start',value:Number(m[1])};
  if((m=s.match(pattern('(?:productivity\\s+)?(?:start|starting|beginning)(?:\\s+year)?\\s*(?:to|in|from|=|is)?\\s*(2027|2028|2029)'))))
    return {field:'start',value:Number(m[1])};
  if((m=s.match(pattern('(?:hold|keep|set|make)\\s+(?:the\\s+)?energy\\s+(?:price\\s+)?(?:constant|unchanged|flat|steady|at\\s+0\\s*%)'))))
    return {field:'energy',value:'0'};
  if((m=s.match(pattern('(?:energy(?:\\s+(?:price|deviation|change|fluctuation))?|(?:the\\s+)?energy)\\s*(?:to|at|=|is|of)?\\s*'+number+'\\s*%?'))))
    return {field:'energy',value:m[1]};
  if((m=s.match(pattern('(?:set|change|adjust|make|assume|use)\\s+(?:the\\s+)?energy(?:\\s+(?:price|deviation|change|fluctuation))?\\s*(?:to|at|=|of)?\\s*'+number+'\\s*%?'))))
    return {field:'energy',value:m[1]};
  if((m=s.match(pattern('energy\\s+(?:rise|rises|increase|increases|up)\\s+(?:to|of|at)?\\s*'+number+'\\s*%?'))))
    return {field:'energy',value:m[1]};
  if((m=s.match(pattern('energy\\s+(?:fall|falls|decrease|decreases|down)\\s+(?:to|of|at)?\\s*'+number+'\\s*%?'))))
    return {field:'energy',value:String(-Math.abs(Number(m[1])))};
  return {error:'I cannot safely interpret “'+raw+'”. Specify a scenario, productivity (0–5%), start year (2027–2029), energy (−3% to +3%), or comparison.'};
}
export function validateState(raw){
  if(!raw||typeof raw!=='object')throw Error('Scenario state required.');
  const scenario=canonicalCase(String(raw.scenario??''));
  const comparison=String(raw.comparison)==='None'?'None':canonicalCase(String(raw.comparison??''));
  const start=Number(raw.start);
  if(!scenario||!comparison||!START_YEARS.includes(start))throw Error('Invalid scenario/start/comparison.');
  return {scenario,comparison,start,
    productivity:parseDecimal(String(raw.productivity),'Productivity',0,5),
    energy:parseDecimal(String(raw.energy),'Energy',-3,3)};
}
export function interpret(text,current) {
  let previous;
  try{previous=validateState(current);}
  catch(error){return {ok:false,question:'Scenario controls are invalid. Reset the controls before issuing a command.',changes:{}};}
  if(typeof text!=='string'||!text.trim())return {ok:false,question:'Enter a supported scenario instruction.',changes:{}};
  if(text.length>450)return {ok:false,question:'Please use a shorter command (up to 450 characters).',changes:{}};
  const clauses=segments(text);
  if(!clauses.length)return {ok:false,question:'Enter a scenario instruction.',changes:{}};
  const changes={};
  for(const clause of clauses){
    const parsed=clauseMatches(clause);
    if(parsed?.error||!parsed)return {ok:false,question:parsed?.error||'Please clarify the instruction.',changes:{}};
    if(parsed.view)continue;
    let value=parsed.value;
    try{
      if(parsed.field==='productivity')value=parseDecimal(String(value),'Productivity',0,5);
      if(parsed.field==='energy')value=parseDecimal(String(value),'Energy',-3,3);
      if(parsed.field==='start')value=Number(value);
      if(parsed.start && !START_YEARS.includes(Number(parsed.start)))throw Error('Productivity start must be 2027, 2028 or 2029.');
    }catch(error){return {ok:false,question:error.message,changes:{}};}
    if(Object.hasOwn(changes,parsed.field)&&changes[parsed.field]!==value)
      return {ok:false,question:'Conflicting '+parsed.field+' instructions. Specify one value.',changes:{}};
    changes[parsed.field]=value;
    if(parsed.start){
      const start=Number(parsed.start);
      if(Object.hasOwn(changes,'start')&&changes.start!==start)
        return {ok:false,question:'Conflicting productivity start years. Specify one year.',changes:{}};
      changes.start=start;
    }
  }
  const next={...previous,...changes};
  return {ok:true,changes,state:next,
    updatedFields:Object.keys(changes),
    confirmation:'Illustrative scenario updated. '+formatState(next)+'. No calibrated economic forecast has been changed.'};
}
export function formatState(s) {
  return s.scenario+' case; productivity '+s.productivity+'% from '+s.start+
    '; energy '+(s.energy>0?'+':'')+s.energy+'%; compare with '+s.comparison;
}
export function calculateIllustrative(state){
  const s=validateState(state);
  const years=[2026,2027,2028,2029,2030];
  let index=ECONOMICS.baseIndex;
  return years.map(year=>{
    if(year>ECONOMICS.baseYear)index*=1+(ECONOMICS.growthRates[s.scenario]+
      (year>=s.start?s.productivity:0)+ECONOMICS.energyCoefficient*s.energy)/100;
    return {year,index};
  });
}
