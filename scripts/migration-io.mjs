// One-time migration I/O. Stable HTTP contract only; no agent runtime.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
export const homePath=()=>path.resolve(process.env.MOUSTACHI_HOME || path.join(process.env.LOCALAPPDATA || os.homedir(),'Moustachi'));
export const readJson=(file)=>JSON.parse(fs.readFileSync(file,'utf8').replace(/^\uFEFF/,''));
export function writeJson(file,value){fs.mkdirSync(path.dirname(file),{recursive:true});const tmp=`${file}.${process.pid}.tmp`;fs.writeFileSync(tmp,JSON.stringify(value,null,2)+'\n','utf8');fs.renameSync(tmp,file);}
export const bounded=(text,max)=>{text=String(text||'');if(text.length<=max)return text;const tail=Math.min(1000,Math.floor(max/4));return text.slice(0,max-tail-60)+'\n...[omitted; full record retained in history]...\n'+text.slice(-tail);};
export function requiredString(value,name,max=12000){if(typeof value!=='string'||!value.trim()||value.length>max)throw Object.assign(new Error(`${name} must contain 1..${max} characters.`),{status:400});return value.trim();}
export function profileId(value){if(!/^[a-z0-9][a-z0-9_-]{0,63}$/.test(value||''))throw Object.assign(new Error('Invalid profile id.'),{status:400});return value;}
export const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));



export class MoustachiClient {
  constructor({url='http://127.0.0.1:39178',tokenFile,profileId,origin='owner'}){this.url=url.replace(/\/$/,'');this.tokenFile=tokenFile;this.profileId=profileId;this.origin=origin;}
  async call(op,args={}){const response=await fetch(`${this.url}/v1`,{method:'POST',headers:{Authorization:`Bearer ${fs.readFileSync(this.tokenFile,'utf8').trim()}`,'Content-Type':'application/json'},body:JSON.stringify({profileId:this.profileId,origin:this.origin,...args,op}),signal:AbortSignal.timeout(15000)});const data=await response.json();if(!response.ok)throw Object.assign(new Error(data.error||`HTTP ${response.status}`),{status:response.status});return data;}
  async wait(runId,{timeoutMs=650000,onPending}={}){const end=Date.now()+timeoutMs;while(Date.now()<end){const run=await this.call('get',{runId});if(run.status==='completed')return run;if(['failed','cancelled','interrupted'].includes(run.status))throw Object.assign(new Error(run.error||run.status),{run});if(run.status==='awaiting_permission')await onPending?.(run);await sleep(700);}throw new Error(`Wait timed out for run ${runId}; check its status before retrying.`);}
}
