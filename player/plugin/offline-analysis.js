(function(root){
'use strict';
const VERSION='yamnet-offline-1-balanced',MAX_BYTES=40*1024*1024;
let modelPromise,generation=0;
function message(text){const node=document.getElementById('analysis-status');if(node)node.textContent=text;}
function decide(rows){
 let total=0,music=0,speech=0,run=0,longest=0;const segments=[];let active=null;
 for(const row of rows){
  if(![row.seconds,row.speech,row.music,row.singing].every(Number.isFinite))throw Error('תוצאת בדיקת שמע לא תקינה');
  total+=row.seconds;speech+=row.seconds*(row.speech>=.5);
  if(Math.max(row.music,row.singing)>=.5){music+=row.seconds;run+=row.seconds;if(!active)active={start:row.start,end:row.start+row.seconds};else active.end=row.start+row.seconds;}
  else{run=0;if(active){segments.push(active);active=null;}}
  longest=Math.max(longest,run);
 }
 if(active)segments.push(active);
 return {version:VERSION,seconds:total,decision:!total?'uncertain':music/total>=.1||longest>=2.9?'block':speech/total>=.5?'allow':'uncertain',musicFraction:total?music/total:0,speechFraction:total?speech/total:0,segments};
}
async function model(){
 if(!modelPromise)modelPromise=(async()=>{
  if(!root.tf||!root.tflite)throw Error('רכיבי הבדיקה המקומית חסרים. התקינו מחדש את התוסף.');
  tflite.setWasmPath(new URL('./',document.baseURI).href);
  const response=await fetch(new URL('yamnet.tflite',document.baseURI));if(!response.ok)throw Error('המודל המקומי אינו זמין');
  const bytes=await response.arrayBuffer();const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
  if(hash!=='e193da5676a2fdb7a3702c10fba62aa27d76f64e4534467443811c1a2ff1667d')throw Error('קובץ מודל הבדיקה פגום');
  return tflite.loadTFLiteModel(bytes,{numThreads:1});
 })().catch(e=>{modelPromise=null;throw e;});
 return modelPromise;
}
async function read(url){
 const response=await fetch(url);if(!response.ok)throw Error('לא ניתן לקרוא את ההקלטה לבדיקה מקומית');
 if(Number(response.headers.get('content-length'))>MAX_BYTES)throw Error('בדיקת השמע תומכת בקבצים עד 40MB בגרסה זו');
 const reader=response.body?.getReader();if(!reader)throw Error('קריאת קבצים מדורגת אינה נתמכת בגרסת אוצריא זו');
 let count=0;const chunks=[];
 try{while(true){const {done,value}=await reader.read();if(done)break;count+=value.length;if(count>MAX_BYTES)throw Error('ההקלטה גדולה מדי לבדיקה מקומית (40MB)');chunks.push(value);}}
 catch(e){await reader.cancel();throw e;}
 const bytes=new Uint8Array(count);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.length;}return bytes.buffer;
}
async function analyze(url){
 const revision=generation;message('בודק שמע במכשיר בלבד…');
 const bytes=await read(url);const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
 const cached=await ShiurProtocol.rpc('storage.get',{key:'audio-analysis:'+VERSION+':'+hash});
 if(cached?.version===VERSION&&cached.decision==='allow'&&Number.isFinite(cached.seconds)&&cached.seconds>=300){message('בדיקת שמע מקומית קודמת: דיבור');return cached;}
 const context=new OfflineAudioContext(1,1,16000);let buffer;
 try{buffer=await context.decodeAudioData(bytes);}catch{throw Error('לא ניתן לפענח את ההקלטה לבדיקה מקומית');}
 if(!Number.isFinite(buffer.duration)||buffer.duration<300)throw Error('ניתן לנגן רק הקלטות באורך חמש דקות ומעלה');
 if(buffer.duration>5400||buffer.length*buffer.numberOfChannels>48000000)throw Error('ההקלטה ארוכה מדי לבדיקה מקומית בגרסה זו');
 const net=await model(),rows=[],frame=15600;let last=0;
 for(let start=0;start<buffer.length;start+=frame){
  if(revision!==generation)throw Error('בדיקת השמע בוטלה');
  const count=Math.min(frame,buffer.length-start),data=new Float32Array(frame);
  for(let channel=0;channel<buffer.numberOfChannels;channel++){const a=buffer.getChannelData(channel);for(let i=0;i<count;i++)data[i]+=a[start+i]/buffer.numberOfChannels;}
  const input=tf.tensor1d(data);let output;
  try{output=net.predict(input);const scores=output.dataSync();rows.push({start:start/16000,seconds:count/16000,speech:scores[0],music:scores[132],singing:scores[24]});}
  finally{input.dispose();output?.dispose();}
  const percent=Math.floor((start+count)/buffer.length*100);if(percent!==last){message('בדיקת שמע מקומית: '+percent+'%');last=percent;await new Promise(resolve=>setTimeout(resolve,0));}
 }
 const result=decide(rows);if(result.decision==='allow')await ShiurProtocol.rpc('storage.set',{key:'audio-analysis:'+VERSION+':'+hash,value:result});
 message(result.decision==='allow'?'בדיקת שמע מקומית: דיבור. הזיהוי אינו מושלם.':result.decision==='block'?'ההקלטה חסומה: זוהתה מוזיקה או שירה.':'ההקלטה חסומה: לא ניתן לקבוע שמדובר בדיבור.');
 if(result.decision!=='allow')throw Error(result.decision==='block'?'זוהתה מוזיקה או שירה בהקלטה. הניגון נחסם.':'בדיקת השמע אינה ודאית. הניגון נחסם.');
 return result;
}
root.OfflineSpeechAnalysis={analyze,decide,cancel(){generation++;}};
})(globalThis);
