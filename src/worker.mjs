import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {api,config,home,readJson} from './business.mjs';
import {core,wait} from './client.mjs';
const workerId=`${os.hostname().toLowerCase()}-moustachi-onward`,stateFile=path.join(home,'worker-state.json');
const state=readJson(stateFile,{feedbackRuns:{}});
const save=()=>{fs.mkdirSync(home,{recursive:true});const tmp=`${stateFile}.${process.pid}.tmp`;fs.writeFileSync(tmp,JSON.stringify(state,null,2),'utf8');fs.renameSync(tmp,stateFile);};
async function bridge(method,pathname,body){
  const response=await fetch(`${config.whatsappBridgeUrl||'http://127.0.0.1:39177'}${pathname}`,{method,headers:{Authorization:`Bearer ${fs.readFileSync(config.whatsappBridgeTokenFile,'utf8').trim()}`,...(body?{'Content-Type':'application/json'}:{})},body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(pathname==='/send'?120000:6000)});
  const value=await response.json();if(!response.ok)throw new Error(value.error||`Bridge ${response.status}`);return value;
}
async function analysis(){
  const {event}=await api({action:'claim',stage:'analysis',workerId,leaseMs:12*60*1000});if(!event)return false;
  try{
    let run=state.feedbackRuns[event.id]?await core('get',{runId:state.feedbackRuns[event.id]}):await core('submit',{channel:'onward-feedback',externalId:event.id,message:`Analyze Onward tester feedback ${event.id}.`,payload:{event}});
    // Explicit retry is safe for this read-only analysis stage; delivery stays in the product outbox.
    if(['failed','cancelled','interrupted'].includes(run.status))run=await core('retry',{runId:run.id});
    state.feedbackRuns[event.id]=run.id;save();const result=await wait(run.id);
    await api({action:'analysis-complete',eventId:event.id,workerId,agentMessage:result.output,acpSessionId:result.result.agentSessionId,acpRunId:result.id});
    console.log(`analyzed ${event.id}`);return true;
  }catch(e){try{await api({action:'release',stage:'analysis',eventId:event.id,workerId,error:String(e.message).slice(0,2000),retrySeconds:60});}catch{}throw e;}
}
async function delivery(){
  let health;try{health=await bridge('GET','/health');}catch{return false;}if(!health.connected||!health.groupConfigured)return false;
  const {event}=await api({action:'claim',stage:'delivery',workerId,leaseMs:4*60*1000});if(!event)return false;
  try{if(!event.agentMessage)throw new Error('Ready event has no answer.');await bridge('POST','/send',{message:event.agentMessage,idempotencyKey:event.id});await api({action:'delivery-complete',eventId:event.id,workerId});console.log(`delivered ${event.id}`);return true;}
  catch(e){try{await api({action:'release',stage:'delivery',eventId:event.id,workerId,error:String(e.message).slice(0,2000),retrySeconds:60});}catch{}throw e;}
}
async function main(){
  if(process.argv.includes('--status')){console.log(JSON.stringify(await core('status')));return;}
  const max=process.argv.includes('--drain')?6:1;let work=false;
  for(let i=0;i<max;i++){if(!await analysis())break;work=true;}
  for(let i=0;i<max;i++){if(!await delivery())break;work=true;}
  if(!work&&process.argv.includes('--verbose'))console.log('no pending Onward Ops events');
}
main().catch(e=>{console.error(`[moustachi-onward] ${e.message}`);process.exitCode=1;});
