const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const track={id:'a',title:'a.mp3',token:'a'};
function deferred(){let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};}
async function settle(){for(let i=0;i<12;i++)await new Promise(r=>setImmediate(r));}
function fixture(options={}){
 const events={},windowEvents={},store=new Map(),hooks={};let permitted=true,time=0,wanted=0;
 const audio={duration:600,readyState:1,paused:true,muted:false,volume:1,playbackRate:1,seeking:false,autoMetadata:true,delayedSeek:false,
  addEventListener(n,f){(events[n]??=new Set()).add(f)},removeEventListener(n,f){events[n]?.delete(f)},emit(n){for(const f of [...(events[n]||[])])f()},
  pause(){this.paused=true},play(){this.paused=false;return Promise.resolve()},removeAttribute(){this.src=''},
  load(){if(this.src){time=0;this.readyState=0;if(this.autoMetadata)queueMicrotask(()=>{this.readyState=1;this.emit('loadedmetadata')})}},
  finishSeek(){time=wanted;this.seeking=false;this.emit('seeked')}
 };
 Object.defineProperty(audio,'currentTime',{get(){return time},set(value){wanted=value;if(audio.delayedSeek)audio.seeking=true;else time=value}});
 const context=vm.createContext({console,AbortController,performance:options.performance||performance,setTimeout:options.setTimeout||setTimeout,clearTimeout,setInterval:()=>1,clearInterval(){},navigator:{},ShiurCore:{uuid:()=> 'session'},window:{addEventListener(n,f){windowEvents[n]=f}},OfflineSpeechAnalysis:{cancel(){},async analyze(){if(hooks.analyze)return hooks.analyze();return {decision:'provisional_speech',scope:'sampled_only',checks:[{},{}],duration:600}}},Otzaria:{async call(method,args={}){
  if(method==='app.getGrantedPermissions')return {success:true,data:{permissions:permitted?['fs.user_files.read']:[]}};
  if(method==='fs.resolveFileUrl')return {success:true,data:hooks.resolve?await hooks.resolve():{url:'local/a'}};
  if(method==='storage.get')return {success:true,data:store.get(args.key)||null};
  if(method==='storage.set'){store.set(args.key,JSON.parse(JSON.stringify(args.value)));return {success:true,data:true}}
  throw Error(method);
 }}});
 for(const f of ['protocol.js','local-audio.js','playback.js'])vm.runInContext(fs.readFileSync('player/plugin/'+f,'utf8'),context);
 const visible=new context.VisiblePlayback(audio);return {audio,hooks,visible,player:visible.local,store,windowEvents,revoke(){permitted=false},grant(){permitted=true}};
}
test('an asynchronous resume seek cannot overwrite the saved position with zero',async()=>{
 const f=fixture();await f.player.init();f.player.positions.a={positionMs:65432,durationMs:600000};f.audio.delayedSeek=true;
 await f.player.load(track);await f.player.publish();assert.equal(f.player.positions.a.positionMs,65432);
 f.audio.finishSeek();assert.equal(f.player.snapshot().positionMs,65432);
});
test('cancel while resolving a file prevents later approval',async()=>{
 const f=fixture(),gate=deferred();let calls=0;f.hooks.resolve=()=>++calls===1?gate.promise:{url:'local/a'};await f.player.init();
 const load=f.visible.load(track,0);const outcome=load.then(()=>null,e=>e);await settle();f.visible.cancel();gate.resolve({url:'local/a'});await outcome;
 assert.equal(f.player.loaded,false);assert.equal(f.audio.muted,true);assert.equal(f.audio.paused,true);
});
test('cancel during metadata loading prevents analysis and unmuting',async()=>{
 const f=fixture();await f.player.init();f.audio.autoMetadata=false;let scans=0;f.hooks.analyze=async()=>{scans++;return {decision:'provisional_speech'}};
 const load=f.player.load(track);const outcome=load.then(()=>null,e=>e);await settle();f.visible.cancel();f.audio.readyState=1;f.audio.emit('loadedmetadata');await outcome;
 assert.equal(scans,0);assert.equal(f.player.loaded,false);assert.equal(f.audio.muted,true);
});
test('suspending during analysis prevents late approval even if the analyzer ignores cancellation',async()=>{
 const f=fixture(),gate=deferred();await f.player.init();f.hooks.analyze=()=>gate.promise;
 const load=f.player.load(track);const outcome=load.then(()=>null,e=>e);await settle();const suspend=f.player.suspend();gate.resolve({decision:'provisional_speech'});await outcome;await suspend;
 assert.equal(f.player.loaded,false);assert.equal(f.audio.muted,true);assert.equal(f.audio.paused,true);
});
test('revoked file permission during analysis cannot result in a ready recording',async()=>{
 const f=fixture();await f.player.init();f.hooks.analyze=async()=>{f.revoke();return {decision:'provisional_speech'}};
 await f.player.load(track).catch(()=>{});assert.equal(f.player.loaded,false);assert.equal(f.audio.muted,true);
});
test('duration dropping below the minimum during analysis cannot unmute the recording',async()=>{
 const f=fixture();await f.player.init();f.hooks.analyze=async()=>{f.audio.duration=10;return {decision:'provisional_speech'}};
 await f.player.load(track).catch(()=>{});assert.equal(f.player.loaded,false);assert.equal(f.audio.muted,true);
});
test('stop cancels a pending scan rather than waiting for it to finish',async()=>{
 const f=fixture(),gate=deferred();await f.player.init();f.hooks.analyze=()=>gate.promise;
 const pending=f.visible.load(track,0);const outcome=pending.then(()=>null,e=>e);await settle();await f.visible.send('stop');await outcome;
 assert.equal(f.player.loaded,false);assert.equal(f.audio.paused,true);assert.equal(f.audio.muted,true);
});
test('a seek followed immediately by pause preserves the requested place',async()=>{
 const f=fixture();await f.player.init();await f.player.load(track);f.audio.delayedSeek=true;
 await f.player.execute({op:'seek',positionMs:123456});await f.player.execute({op:'pause'});await f.player.publish();
 assert.equal(f.player.positions.a.positionMs,123456);assert.equal(f.player.snapshot().positionMs,123456);
});
test('an unapproved analyzer result cannot unmute playback',async()=>{
 const f=fixture();await f.player.init();f.hooks.analyze=async()=>({decision:'uncertain'});
 await assert.rejects(f.player.load(track),/אושרה/);assert.equal(f.player.loaded,false);assert.equal(f.audio.muted,true);
});
test('suspending an already approved recording preserves readiness and place for resume',async()=>{
 const f=fixture();await f.player.init();await f.player.load(track);await f.player.execute({op:'seek',positionMs:65432});await f.player.play();
 await f.player.suspend();assert.equal(f.audio.paused,true);assert.equal(f.player.loaded,true);assert.equal(f.player.positions.a.positionMs,65432);
 await f.player.resume();assert.equal(f.audio.paused,true);await f.player.play();assert.equal(f.audio.paused,false);assert.equal(f.player.positions.a.positionMs,65432);
});
test('the load deadline also bounds a stalled host-file lookup',async()=>{
 const f=fixture({setTimeout:(fn,ms)=>setTimeout(fn,Math.min(ms,25))});await f.player.init();f.hooks.resolve=()=>new Promise(()=>{});
 await assert.rejects(f.player.load(track),e=>e.name==='TimeoutError');assert.equal(f.player.loaded,false);assert.equal(f.audio.muted,true);
});
test('a suspended uninitialized player does not overwrite stored checkpoints',async()=>{
 const f=fixture();f.store.set('shiur-audio-v1:state',{positions:{a:{positionMs:65432,durationMs:600000}},currentId:'a'});
 await f.player.suspend();assert.equal(f.store.get('shiur-audio-v1:state').positions.a.positionMs,65432);await f.player.resume();assert.equal(f.store.get('shiur-audio-v1:state').positions.a.positionMs,65432);
});
test('permission revoke and regrant can reinitialize without losing the saved place',async()=>{
 const f=fixture();await f.player.init();await f.player.load(track);await f.player.execute({op:'seek',positionMs:65432});f.revoke();f.player.lastPermissionCheck=0;await f.player.tick();
 assert.equal(f.player.ready,false);assert.equal(f.player.loaded,false);assert.equal(f.audio.muted,true);f.grant();await f.visible.init();assert.equal(f.player.ready,true);assert.equal(f.player.loaded,true);assert.equal(f.player.positions.a.positionMs,65432);
});
test('a late result from a superseded load cannot clear or approve the newer recording',async()=>{
 const f=fixture(),gate=deferred();await f.player.init();let scans=0;f.hooks.analyze=()=>++scans===1?gate.promise:Promise.resolve({decision:'provisional_speech'});
 const first=f.player.load(track);const outcome=first.then(()=>null,e=>e);await settle();const second={id:'b',title:'b.mp3',token:'b'};await f.player.load(second);await outcome;
 gate.resolve({decision:'provisional_speech'});await settle();assert.equal(f.player.current.id,'b');assert.equal(f.player.loaded,true);assert.equal(f.audio.muted,false);
});
test('an elapsed load deadline cannot approve before the timer callback is delivered',async()=>{
 let now=0;const f=fixture({performance:{now(){return now}}});await f.player.init();f.hooks.analyze=async()=>{now=6000;return {decision:'provisional_speech'}};
 await assert.rejects(f.player.load(track),e=>e.name==='TimeoutError');assert.equal(f.player.loaded,false);assert.equal(f.audio.muted,true);
});
