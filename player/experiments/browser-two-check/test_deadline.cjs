const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
test('deadline rejects even after model initialization starts and never settles',async()=>{
 const hash=Uint8Array.from(Buffer.from('e193da5676a2fdb7a3702c10fba62aa27d76f64e4534467443811c1a2ff1667d','hex')),timers=[];let initialized;
 const started=new Promise(resolve=>initialized=resolve);
 const c=vm.createContext({console,AbortController,DOMException,URL,setTimeout(fn,ms){const t={fn,ms,unref(){}};timers.push(t);return t},clearTimeout(t){t.cancelled=true},performance,Uint8Array,document:{baseURI:'http://local/'},location:{origin:'http://local'},crypto:{subtle:{async digest(){return hash.buffer}}},fetch:async()=>new Response(new Uint8Array(16061524)),RangeAudio:{async prepare(){return {file:{check(){}},async samples(){return [new Float32Array(15600),new Float32Array(15600)]}}}},tf:{},tflite:{setWasmPath(){},loadTFLiteModel(){initialized(true);return new Promise(()=>{})}}});
 vm.runInContext(fs.readFileSync('player/plugin/analysis-two-check.js','utf8'),c);
 const outcome=c.BrowserTwoCheck.scan('http://local/audio',{assetBase:'http://local/',budgetMs:5000}).then(()=> 'approved',e=>e.name);
 assert.equal(await Promise.race([started,new Promise(resolve=>setTimeout(()=>resolve('not-started'),1000))]),true);
 timers.find(t=>t.ms===5000).fn(); // Fire the scan deadline while the model promise is still pending.
 const result=await Promise.race([outcome,new Promise(resolve=>setTimeout(()=>resolve('hung'),100))]);assert.notEqual(result,'hung');assert.notEqual(result,'approved');
});
