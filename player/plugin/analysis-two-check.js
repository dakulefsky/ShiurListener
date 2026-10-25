/* Shared offline two-check analyzer used by the development player. */
(function(root){
'use strict';
const MODEL_SHA='e193da5676a2fdb7a3702c10fba62aa27d76f64e4534467443811c1a2ff1667d',models=new Map();
function decide(rows){
 if(rows.length!==2)throw Error('Exactly two checks are required');
 for(const r of rows)if(['speech','music','singing'].some(k=>!Number.isFinite(r[k])||r[k]<0||r[k]>1))throw Error('Invalid classifier output');
 const music=rows.filter(r=>Math.max(r.music,r.singing)>=.5).length;
 if(music===2)return {decision:'music_detected_in_samples',reason:'Both checks indicate music or singing'};
 if(rows.some(r=>r.speech>=.8))return {decision:'provisional_speech',reason:'One check strongly indicates speech'};
 if(!music&&rows.every(r=>r.speech>=.5))return {decision:'provisional_speech',reason:'Both checks indicate speech'};
 return {decision:'uncertain',reason:'Insufficient clear speech evidence'};
}
function prepareInput(samples){
 if(!samples||samples.length!==15600)throw Error('Invalid analyzer sample length');
 let dc=0;
 for(const value of samples){if(!Number.isFinite(value))throw Error('Invalid analyzer sample');dc+=value;}
 dc/=samples.length;let power=0,peak=0;
 for(const value of samples){const centered=value-dc;power+=centered*centered;peak=Math.max(peak,Math.abs(centered));}
 const rms=Math.sqrt(power/samples.length);
 // Do not amplify digital silence or force quiet material to pass. Scores still decide.
 // Retain the previous cap when it already reaches RMS .008; avoid overcorrecting those inputs.
 const gainLimit=rms<.0005?128:16;
 const gain=rms>1e-5?Math.max(1,Math.min(gainLimit,.08/rms,.95/Math.max(peak,1e-12))):1;
 const waveform=Float32Array.from(samples,value=>(value-dc)*gain);
 return {waveform,stats:{dcOffset:dc,inputRms:rms,appliedGain:gain,gainLimit}};
}
function abortable(action,signal){
 return new Promise((resolve,reject)=>{
  const aborted=()=>{signal.removeEventListener('abort',aborted);reject(signal.reason||new DOMException('Scan cancelled','AbortError'));};
  signal.addEventListener('abort',aborted,{once:true});
  Promise.resolve(action).then(value=>{signal.removeEventListener('abort',aborted);if(signal.aborted)aborted();else resolve(value);},error=>{signal.removeEventListener('abort',aborted);reject(error);});
  if(signal.aborted)aborted();
 });
}
function loadModel(base){
 if(!models.has(base))models.set(base,(async()=>{
  if(!root.tf||!root.tflite)throw Error('Bundled local model runtime is missing');
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),10000);timer.unref?.();
  try{
   tflite.setWasmPath(base);const response=await fetch(new URL('yamnet.tflite',base),{signal:controller.signal});if(!response.ok)throw Error('Bundled model could not be loaded');
   const reader=response.body.getReader(),chunks=[];let count=0;
   try{while(true){const {done,value}=await abortable(reader.read(),controller.signal);if(done)break;count+=value.length;if(count>16061524)throw Error('Oversized model file');chunks.push(value);}}
   catch(error){await reader.cancel();throw error;}
   if(count!==16061524)throw Error('Truncated model file');
   const bytes=new Uint8Array(count);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.length;}
   const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
   if(hash!==MODEL_SHA)throw Error('Model checksum mismatch');
   return await abortable(tflite.loadTFLiteModel(bytes.buffer,{numThreads:1}),controller.signal);
  }finally{clearTimeout(timer);controller.abort();}
 })().catch(e=>{models.delete(base);throw e;}));
 return models.get(base);
}
async function scan(url,{assetBase=new URL('../../plugin/',document.baseURI).href,duration,budgetMs=5000,signal,onProgress=()=>{}}={}){
 if(!Number.isFinite(budgetMs)||budgetMs<=0||budgetMs>5000)throw Error('Invalid fast-check time budget');
 if(signal?.aborted)throw signal.reason||new DOMException('Scan cancelled','AbortError');
 if(new URL(assetBase).origin!==location.origin)throw Error('Model assets must be local to this page');
 const started=performance.now(),controller=new AbortController(),cancel=()=>controller.abort(),timer=setTimeout(cancel,budgetMs);signal?.addEventListener('abort',cancel,{once:true});if(signal?.aborted)cancel();
 try{
  onProgress('Reading local metadata and loading bundled model');
  const preparedPromise=RangeAudio.prepare(url,{duration,budgetMs,signal:controller.signal}),netPromise=loadModel(assetBase);netPromise.catch(()=>{});const prepared=await abortable(preparedPromise,controller.signal);
  onProgress('Reading two bounded excerpts');const [samples,net]=await abortable(Promise.all([prepared.samples(),netPromise]),controller.signal);prepared.file.check();
  const checks=[];
  for(let i=0;i<samples.length;i++){
   prepared.file.check();onProgress(`Checking excerpt ${i+1}/2`);const preparedInput=prepareInput(samples[i]),input=tf.tensor1d(preparedInput.waveform);let output;
   try{output=net.predict(input);const scores=output.dataSync();checks.push({startSeconds:prepared.times[i],speech:scores[0],music:scores[132],singing:scores[24],inputPreparation:preparedInput.stats});}
   finally{input.dispose();output?.dispose();}
  }
  prepared.file.check();const result=decide(checks);
  return {...result,policy:'two-interior-checks-v2-speech-priority',preprocessing:'dc-quiet-gain-v2',scope:'sampled_only',fullFileApproved:false,checks,encodedBytes:prepared.file.size,sourceBytesRead:prepared.file.bytesRead,sourceRangeRequests:prepared.file.requests,duration:prepared.info.duration,format:prepared.info.kind,positionAccuracy:prepared.info.kind==='mp3'?'approximate MPEG byte seek':'PCM sample position',wallMs:performance.now()-started};
 }finally{clearTimeout(timer);signal?.removeEventListener('abort',cancel);controller.abort();}
}
root.BrowserTwoCheck={scan,decide,prepareInput};
})(globalThis);
