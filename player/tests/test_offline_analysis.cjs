const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function api(extra={}){const c=vm.createContext({console,setTimeout,clearTimeout,URL,AbortController,performance,document:{baseURI:'http://local/',getElementById(){return null}},...extra});for(const file of ['analysis-two-check.js','offline-analysis.js'])vm.runInContext(fs.readFileSync('player/plugin/'+file,'utf8'),c);return {context:c,api:c.OfflineSpeechAnalysis};}
const row=(speech,music=0,singing=0)=>({speech,music,singing});
test('both music samples block even with speech',()=>assert.equal(api().api.decide([row(.9,.9),row(.9,.9)]).decision,'music_detected_in_samples'));
test('strong speech plus a pause passes',()=>assert.equal(api().api.decide([row(.95),row(.01)]).decision,'provisional_speech'));
test('strong speech plus one music-like sample passes',()=>assert.equal(api().api.decide([row(.99),row(.01,.8)]).decision,'provisional_speech'));
test('silence and invalid scores never pass',()=>{const a=api().api;assert.equal(a.decide([row(0),row(0)]).decision,'uncertain');assert.throws(()=>a.decide([row(NaN),row(.9)]));assert.throws(()=>a.decide([row(.9)]));});
test('missing runtime fails rather than allowing playback',async()=>await assert.rejects(api().api.analyze('http://local/file'),/רכיבי/));
test('cancelling the adapter aborts an in-progress scan',async()=>{
 const f=api({tf:{},tflite:{}});let receivedSignal;
 f.context.BrowserTwoCheck={scan:async(url,{signal})=>{receivedSignal=signal;await new Promise((resolve,reject)=>signal.addEventListener('abort',()=>reject(Error('aborted'))));}};
 const pending=f.api.analyze('http://local/file',{duration:600});f.api.cancel();await assert.rejects(pending,/הבדיקה/);assert.equal(receivedSignal.aborted,true);
});
test('adapter keeps sampled result and forwards duration',async()=>{
 const f=api({tf:{},tflite:{}});let duration;
 f.context.BrowserTwoCheck={scan:async(url,options)=>{duration=options.duration;return {decision:'provisional_speech',scope:'sampled_only',fullFileApproved:false,checks:[row(.99),row(.5)]};}};
 const result=await f.api.analyze('http://local/file',{duration:600});assert.equal(result.scope,'sampled_only');assert.equal(result.fullFileApproved,false);assert.equal(duration,600);
});


test('quiet speech input gets bounded gain and constant offset is removed',()=>{
 const f=api(),samples=Float32Array.from({length:15600},(_,i)=>.05+.001*Math.sin(i*.1));
 const result=f.context.BrowserTwoCheck.prepareInput(samples);
 assert.ok(Math.abs(result.stats.dcOffset-.05)<.00001);assert.equal(result.stats.appliedGain,16);
 assert.ok(Math.abs(result.waveform.reduce((a,b)=>a+b,0)/15600)<1e-7);
});
test('preparation preserves silence and limits boost at peaks',()=>{
 const prepare=api().context.BrowserTwoCheck.prepareInput;
 const silence=prepare(new Float32Array(15600).fill(.05));assert.equal(silence.stats.appliedGain,1);assert.equal(silence.waveform.some(v=>v!==0),false);
 const peaks=new Float32Array(15600);peaks[20]=.8;peaks[21]=-.8;const result=prepare(peaks);
 assert.ok(Math.max(...result.waveform.map(Math.abs))<=.950001);
 assert.throws(()=>prepare(new Float32Array(3)),/length/);
 const invalid=new Float32Array(15600);invalid[1]=NaN;assert.throws(()=>prepare(invalid),/sample/);
});
