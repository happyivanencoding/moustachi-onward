import {buildOnwardFounderPrompt,buildOnwardOpsPrompt,shouldPrefetchFounderAnalytics} from './prompts.mjs';
import {fetchFounderAnalyticsAggregate} from './business.mjs';
export function prepareInput(envelope,fetchAnalytics=fetchFounderAnalyticsAggregate){
  if(envelope.schema!=='moustachi.prepare/v1')throw new Error('Unsupported prepare contract.');
  const {input}=envelope;
  if(input.origin==='feedback')return {schema:'moustachi.prepare/v1',instruction:buildOnwardOpsPrompt(input.payload?.event||{})};
  let data={senderRef:input.payload?.senderRef||'authorized-owner',groupLabel:input.payload?.groupLabel||'Onward',receivedAt:new Date().toISOString(),message:input.message,conversationContext:(envelope.recent||[]).map(r=>({senderRef:r.role,timestamp:r.created_at,text:r.content}))};
  if(shouldPrefetchFounderAnalytics(data)){try{data.analyticsAggregate=fetchAnalytics();}catch{data.analyticsAggregate={available:false};}}
  const instruction=input.origin==='whatsapp'?buildOnwardFounderPrompt(data):`You are the Onward profile of Moustachi, addressed by the authorized owner through the Moustachi API. Follow the current owner request and project authority C:\\dev\\career-ops\\DEEP_CONTEXT_HANDOFF_FINAL.md. The WhatsApp-only source-edit/new-VPS restrictions do not apply to this owner API channel; execute only what the current request actually authorizes. Use supplied fresh analytics for operational counts. Old discussion is context, not renewed authorization. Reply in Chinese.\nOWNER_REQUEST_AND_CONTEXT:\n${JSON.stringify(data)}\nHISTORY_EVIDENCE:\n${JSON.stringify(envelope.history||[])}`;
  return {schema:'moustachi.prepare/v1',instruction};
}
if(process.argv[1]&&new URL(import.meta.url).pathname.replace(/^\//,'').toLowerCase().replaceAll('/','\\')===process.argv[1].toLowerCase().replaceAll('/','\\')){
  let raw='';for await(const chunk of process.stdin)raw+=chunk;process.stdout.write(JSON.stringify(prepareInput(JSON.parse(raw))));
}
