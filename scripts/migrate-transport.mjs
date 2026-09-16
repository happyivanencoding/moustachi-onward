import fs from 'node:fs';import path from 'node:path';
import {MoustachiClient,homePath,readJson,writeJson} from './migration-io.mjs';
const home=homePath(),legacy=path.join(process.env.LOCALAPPDATA,'OnwardOps'),target=path.join(home,'transports','whatsapp');
if(fs.existsSync(path.join(target,'migration.json')))throw new Error('Migration already applied. Do not overwrite live transport state.');
const current=readJson(path.join(legacy,'whatsapp-bridge','config.json')),oldState=readJson(path.join(legacy,'whatsapp-bridge','state.json'));
const coreConfig=readJson(path.join(home,'config.json'));
const bridgeTokenFile=current.tokenFile||path.join(legacy,'secrets','whatsapp-bridge');
// Keep provider-owned credentials in place by an authDir reference. Never export/copy login files.
const config={port:39177,profileId:'onward',channel:'onward-founders',groupJid:current.groupJid,groupLabel:current.groupLabel,pairedAt:current.pairedAt,authDir:path.join(legacy,'whatsapp-bridge','auth'),tokenFile:bridgeTokenFile,coreUrl:'http://127.0.0.1:39178',coreTokenFile:coreConfig.clients.find(c=>c.id==='whatsapp').tokenFile};
const {founderContext,...state}=oldState;const next={...state,chatContext:founderContext||[],incomingSpool:[],pendingTurns:{}};
writeJson(path.join(target,'config.json'),config);writeJson(path.join(target,'state.json'),next);
const businessFile=path.join(process.env.LOCALAPPDATA,'MoustachiOnward','config.json'),business=readJson(businessFile);writeJson(businessFile,{...business,whatsappBridgeTokenFile:bridgeTokenFile});
const owner=coreConfig.clients.find(c=>c.id==='owner');const client=new MoustachiClient({tokenFile:owner.tokenFile,profileId:'onward'});
let imported=0;
for(const item of founderContext||[]){await client.call('observe',{channel:config.channel,messageId:item.id||`legacy-${imported}`,message:`${item.senderRef||'member'}: ${item.text}`,timestamp:item.timestamp});imported++;}
const report={schema:'moustachi.migration/v1',at:new Date().toISOString(),source:'JPilot dc5b94c installed OnwardOps',rollingMessagesImported:imported,processedIdsPreserved:(state.processedIds||[]).length,outboundReceiptsPreserved:Object.keys(state.outbound||{}).length,credentials:'Provider-owned original authDir referenced; no credential copy',legacyAcp:'Original Runtime/Codex files retained, not parsed/imported',authDirReference:true};
writeJson(path.join(target,'migration.json'),report);console.log(JSON.stringify(report));
