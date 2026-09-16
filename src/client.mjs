import fs from 'node:fs';
import {config} from './business.mjs';
// Wire contract only. No import from a moustachi checkout/package, no Runtime calls.
export async function core(op,args={}){
  const response=await fetch(`${config.coreUrl||'http://127.0.0.1:39178'}/v1`,{method:'POST',headers:{Authorization:`Bearer ${fs.readFileSync(config.coreTokenFile,'utf8').trim()}`,'Content-Type':'application/json'},body:JSON.stringify({profileId:'onward',origin:'feedback',...args,op}),signal:AbortSignal.timeout(15000)});
  const value=await response.json();if(!response.ok)throw new Error(value.error||`Moustachi HTTP ${response.status}`);return value;
}
export async function wait(runId){const end=Date.now()+650000;while(Date.now()<end){const run=await core('get',{runId});if(run.status==='completed')return run;if(['failed','cancelled','interrupted'].includes(run.status))throw new Error(run.error||run.status);await new Promise(r=>setTimeout(r,700));}throw new Error(`Moustachi wait expired; inspect run ${runId} before retry.`);}
