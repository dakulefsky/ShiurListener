const {test}=require('node:test');const assert=require('node:assert/strict');const vm=require('node:vm');const fs=require('node:fs');const path=require('node:path');
function fixture(duration){
 const events={};const audio={duration,currentTime:0,readyState:1,paused:true,muted:false,volume:1,playbackRate:1,
 addEventListener(name,fn){(events[name]??=new Set()).add(fn)},removeEventListener(name,fn){events[name]?.delete(fn)},
 pause(){this.paused=true},removeAttribute(){this.src=''},load(){if(this.src)queueMicrotask(()=>{for(const fn of [...(events.loadedmetadata||[])])fn()})},play(){this.paused=false;return Promise.resolve()}};
 const context=vm.createContext({console,AbortController,performance,OfflineSpeechAnalysis:{async analyze(){return {decision:"provisional_speech"}}},ShiurCore:{uuid:()=> 'session'},navigator:{},window:{addEventListener(){}},setTimeout,clearTimeout,setInterval:()=>1,clearInterval(){},Otzaria:{async call(method){return {success:true,data:method==='app.getGrantedPermissions'?{permissions:['fs.user_files.read']}:method==='fs.resolveFileUrl'?{url:'local-file'}:null}}}});
 for(const file of ['protocol.js','local-audio.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../plugin',file),'utf8'),context);
 return {audio,events,engine:new context.LocalAudioEngine(audio)};
}
for(const duration of [0,12,299,299.999,NaN,Infinity])test(`blocks ${duration} seconds before playback`,async()=>{
 const {audio,engine}=fixture(duration);await engine.init();await assert.rejects(engine.load({id:'a',title:'test.wav',token:'audio'}),/חמש דקות/);assert.equal(audio.muted,true);assert.equal(audio.paused,true);assert.equal(audio.src,'');assert.equal(engine.loaded,false);
});
for(const duration of [300,300.001,3600])test(`allows ${duration} seconds`,async()=>{const {audio,engine}=fixture(duration);await engine.init();await engine.load({id:'a',title:'test.wav',token:'audio'});await engine.play();assert.equal(audio.paused,false);assert.equal(audio.muted,false)});
test('native controls cannot play unvalidated content',async()=>{const {audio,events,engine}=fixture(20);await engine.init();audio.paused=false;for(const fn of events.play)fn();assert.equal(audio.paused,true);assert.equal(audio.muted,true)});
test('changed duration blocks a previously allowed recording',async()=>{const {audio,events,engine}=fixture(600);await engine.init();await engine.load({id:'a',title:'test.wav',token:'audio'});audio.duration=299;for(const fn of events.durationchange)fn();assert.equal(audio.paused,true);assert.equal(audio.muted,true);assert.equal(engine.loaded,false)});
