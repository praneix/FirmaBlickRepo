/* Ephemeral, accessible rule-based controls. No browser storage or outbound requests. */
import {interpret, formatState} from './scenario-command-core.mjs';
const byId=id=>document.getElementById(id);
const fields=['scenario','productivity','start','energy','comparison'];
const form=byId('ask-form');
const input=byId('ask-command');
const result=byId('ask-result');
const assumptions=byId('scenario-assumptions');
const summary=()=>Object.fromEntries(fields.map(id=>[id,byId(id).value]));
function showAssumptions(){
  const s=summary();
  assumptions.textContent='Current illustrative assumptions: '+formatState({
    scenario:s.scenario,productivity:Number(s.productivity),
    start:Number(s.start),energy:Number(s.energy),comparison:s.comparison
  })+'. 2026=100; scenario annual rates Central 0.8%, Resilience 1.4%, Transformation 2.2%; hypothetical energy sensitivity −0.35 index-growth percentage points per 1% energy change. All sensitivities are synthetic and uncalibrated.';
}
for(const id of fields) byId(id).addEventListener('input',showAssumptions);
showAssumptions();
form.addEventListener('submit',event=>{
  event.preventDefault();
  const instruction=input.value;
  const parsed=interpret(instruction,summary());
  if(!parsed.ok){
    result.textContent=parsed.question+' No values were changed.';
    result.dataset.result='clarification';
    input.focus();
    return;
  }
  for(const [field,value] of Object.entries(parsed.changes)){
    const control=byId(field);
    control.value=String(value);
  }
  // One synchronous input event refreshes all dependent chart/readout values
  // and the explicit assumptions label via the existing simulator path.
  byId('scenario').dispatchEvent(new Event('input',{bubbles:true}));
  result.textContent=parsed.confirmation;
  result.dataset.result='confirmed';
  // Only the currently displayed output is retained; no conversation history,
  // sessionStorage, localStorage, cookies, fetch or analytics calls.
});
