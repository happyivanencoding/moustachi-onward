import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {annotateFounderInviteCodes} from './prompts.mjs';
export const home=path.resolve(process.env.MOUSTACHI_ONWARD_HOME||path.join(process.env.LOCALAPPDATA||os.homedir(),'MoustachiOnward'));
export const readJson=(file,fallback={})=>{try{return JSON.parse(fs.readFileSync(file,'utf8').replace(/^\uFEFF/,''));}catch{return fallback;}};
export const config=readJson(path.join(home,'config.json'));
const secretFile=config.internalTokenFile||path.join(home,'secrets','ops-agent');
const analyticsHelper=fileURLToPath(new URL('./analytics-aggregate.py',import.meta.url));
const baseUrl=String(config.baseUrl||'https://jobs-v1.thegreatnovel.com').replace(/\/+$/,'');
const endpoint=`${baseUrl}/api/internal/onward-ops`;
const inviteCodeRegistryFile=config.inviteCodeRegistryFile||path.join(home,'secrets','tester-invite-codes.json');
function internalToken(){
 const direct=String(process.env.ONWARD_OPS_INTERNAL_TOKEN||'').trim();
 if(direct)return direct;
 try{return fs.readFileSync(secretFile,'utf8').trim();}catch{return '';}
}
function sshApi(body){
 const user=String(config.sshUser||'ubuntu').trim(),server=String(config.sshServer||'141.95.18.14').trim();
 const key=path.resolve(String(config.sshKey||path.join(os.homedir(),'.ssh','id_ed25519_server_infra')));
 const known=path.resolve(String(config.sshKnownHosts||path.join(os.homedir(),'.ssh','known_hosts_ovh')));
 const result=spawnSync('ssh',['-i',key,'-o',`UserKnownHostsFile=${known}`,'-o','StrictHostKeyChecking=yes','-o','BatchMode=yes',`${user}@${server}`,'sudo -n /srv/server-infra/scripts/jobpilot-v1-ops-proxy.sh'],{input:JSON.stringify(body),encoding:'utf8',windowsHide:true,timeout:30000,maxBuffer:4*1024*1024});
 if(result.error)throw result.error;
 if(result.status!==0)throw new Error(String(result.stderr||result.stdout||'Onward Ops SSH relay failed.').trim().slice(0,4000));
 const raw=String(result.stdout||'').trim();if(!raw)throw new Error('Onward Ops SSH relay returned no JSON.');
 const value=JSON.parse(raw);if(value?.error)throw new Error(String(value.error));return value;
}
function founderInviteCodeRegistry(){
 const value=readJson(inviteCodeRegistryFile,[]),codes=Array.isArray(value)?value:Array.isArray(value?.codes)?value.codes:[];
 return [...new Set(codes.map(code=>String(code||'').trim().toUpperCase()).filter(code=>/^ONWARD\d{3}$/.test(code)))].slice(0,100);
}
function fetchFounderAnalyticsAggregate(){
 if(!fs.existsSync(analyticsHelper))throw new Error(`Founder analytics helper missing: ${analyticsHelper}`);
 const user=String(config.sshUser||'ubuntu').trim(),server=String(config.sshServer||'141.95.18.14').trim();
 const key=path.resolve(String(config.sshKey||path.join(os.homedir(),'.ssh','id_ed25519_server_infra')));
 const known=path.resolve(String(config.sshKnownHosts||path.join(os.homedir(),'.ssh','known_hosts_ovh')));
 const script=fs.readFileSync(analyticsHelper,'utf8');
 const result=spawnSync('ssh',['-i',key,'-o',`UserKnownHostsFile=${known}`,'-o','StrictHostKeyChecking=yes','-o','BatchMode=yes',`${user}@${server}`,'sudo -n python3 -'],{input:script,encoding:'utf8',windowsHide:true,timeout:30000,maxBuffer:2*1024*1024});
 if(result.error)throw result.error;
 if(result.status!==0)throw new Error(String(result.stderr||'Founder analytics aggregate failed.').trim().slice(0,1200));
 const raw=String(result.stdout||'').trim();if(!raw)throw new Error('Founder analytics aggregate returned no JSON.');
 const value=JSON.parse(raw);if(!value||value.available!==true)throw new Error('Founder analytics aggregate is unavailable.');return annotateFounderInviteCodes(value,founderInviteCodeRegistry());
}
async function api(body){
 const token=internalToken();
 if(!token){
  if(config.sshRelay!==false)return sshApi(body);
  throw new Error(`Onward Ops internal token is not configured at ${secretFile}.`);
 }
 const response=await fetch(endpoint,{method:'POST',headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json',Accept:'application/json'},body:JSON.stringify(body),signal:AbortSignal.timeout(25000)});
 const raw=await response.text();let value={};try{value=JSON.parse(raw||'{}');}catch{}
 if(!response.ok)throw new Error(value.error||`Onward Ops API HTTP ${response.status}`);
 return value;
}

export {api,fetchFounderAnalyticsAggregate};
