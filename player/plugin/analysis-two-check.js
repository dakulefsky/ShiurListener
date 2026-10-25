/* Offline browser two-check prototype. No connection to released playback. */
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
function loadModel(base){
 if(!models.has(base))models.set(base,(async()=>{
  if(!root.tf||!root.tflite)throw Error('Bundled local model runtime is missing');
  tflite.setWasmPath(base);const response=await fetch(new URL('yamnet.tflite',base));if(!response.ok)throw Error('Bundled model could not be loaded');
  const bytes=await response.arrayBuffer(),hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
  if(hash!==MODEL_SHA)throw Error('Model checksum mismatch');
  return tflite.loadTFLiteModel(bytes,{numThreads:1});
 })().catch(e=>{models.delete(base);throw e;}));
 return models.get(base);
}
async function scan(url,{assetBase=new URL('../../plugin/',document.baseURI).href,duration,budgetMs=5000,signal,onProgress=()=>{}}={}){
 if(new URL(assetBase).origin!==location.origin)throw Error('Model assets must be local to this page');
 const started=performance.now(),controller=new AbortController(),cancel=()=>controller.abort(),timer=setTimeout(cancel,budgetMs);signal?.addEventListener('abort',cancel,{once:true});if(signal?.aborted)cancel();
 try{
  onProgress('Reading local metadata and loading bundled model');
  const preparedPromise=RangeAudio.prepare(url,{duration,budgetMs,signal:controller.signal}),netPromise=loadModel(assetBase);netPromise.catch(()=>{});const prepared=await preparedPromise;
  onProgress('Reading two bounded excerpts');const [samples,net]=await Promise.all([prepared.samples(),netPromise]);prepared.file.check();
  const checks=[];
  for(let i=0;i<samples.length;i++){
   prepared.file.check();onProgress(`Checking excerpt ${i+1}/2`);const input=tf.tensor1d(samples[i]);let output;
   try{output=net.predict(input);const scores=output.dataSync();checks.push({startSeconds:prepared.times[i],speech:scores[0],music:scores[132],singing:scores[24]});}
   finally{input.dispose();output?.dispose();}
  }
  prepared.file.check();const result=decide(checks);
  return {...result,policy:'two-interior-checks-v2-speech-priority',scope:'sampled_only',fullFileApproved:false,checks,encodedBytes:prepared.file.size,sourceBytesRead:prepared.file.bytesRead,sourceRangeRequests:prepared.file.requests,duration:prepared.info.duration,format:prepared.info.kind,positionAccuracy:prepared.info.kind==='mp3'?'approximate MPEG byte seek':'PCM sample position',wallMs:performance.now()-started};
 }finally{clearTimeout(timer);signal?.removeEventListener('abort',cancel);controller.abort();}
}
root.BrowserTwoCheck={scan,decide};
})(globalThis);
