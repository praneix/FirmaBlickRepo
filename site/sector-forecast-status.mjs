import {verifySectorForecastStatus,sectorAvailability} from './sector-forecast-status-core.mjs';

const select=document.getElementById('historical-sector');
const message=document.getElementById('sector-forecast-status');
let contract=null;
function display(){
  message.textContent=sectorAvailability(contract,select.value);
}
select.addEventListener('change',display);
async function initialize(){
  try{
    const response=await fetch('./data/sector-forecast-status.json',{cache:'no-store'});
    if(!response.ok)throw Error('Sector release metadata unavailable.');
    contract=verifySectorForecastStatus(await response.json());
  }catch{contract=null;}
  display();
}
initialize();
