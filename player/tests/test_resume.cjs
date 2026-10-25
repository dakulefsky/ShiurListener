const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const {randomUUID}=require('node:crypto');
const root=path.resolve(__dirname,'../plugin');
const clone=value=>JSON.parse(JSON.stringify(value));
function fixture({granted=true,entries={}}={}){
 const store=new Map(Object.entries(clone(entries)));
 const audio={currentTime:0,duration:600,readyState:0,paused:true,ended:false,playbackRate:1,volume:1,addEventListener(){},pause(){this.paused=true;}};
 let failKey=null;
 const context=vm.createContext({console,OfflineSpeechAnalysis:{async analyze(){return {decision:"allow"}}},crypto:{randomUUID},navigator:{},window:{addEventListener(){}},document:{addEventListener(){}},setInterval:()=>1,clearInterval(){},setTimeout,clearTimeout,Otzaria:{on(){},async call(method,args={}){
  if(method==='app.getGrantedPermissions')return {success:true,data:{permissions:granted?['fs.user_files.read']:[]}};
  if(method==='storage.get')return {success:true,data:store.has(args.key)?clone(store.get(args.key)):null};
  if(method==='storage.remove'){store.delete(args.key);return {success:true,data:true};}
  if(method==='storage.set'){if(args.key===failKey)return {success:false,error:{message:'disk write failed'}};store.set(args.key,clone(args.value));return {success:true,data:true};}
  throw Error(method);
 }}});
 for(const file of ['protocol.js','local-audio.js','playback.js','core.js'])vm.runInContext(fs.readFileSync(path.join(root,file),'utf8'),context);
 return {context,store,audio,engine:new context.LocalAudioEngine(audio),keys:context.ShiurProtocol.keys,fail(key){failKey=key;}};
}
const track={id:'a',title:'Shiur A',token:'file_a'};
const legacy={session:'old',currentId:'a',positions:{a:{positionMs:65432,durationMs:120000}},speed:1.5,volume:.8,skipSeconds:15,autoNext:false};
const prefix='shiur-audio-v1:';

test('missing file permission never erases a saved listening position',async()=>{
 const f=fixture({granted:false,entries:{[prefix+'state']:legacy,[prefix+'queue']:[track]}});
 await assert.rejects(f.engine.init(),/קריאת קבצים/);
 assert.equal(f.store.get(f.keys.state).positions.a?.positionMs,65432);
 assert.equal(f.engine.ready,false);
 assert.equal(f.audio.paused,true);
});

test('one invalid saved queue entry cannot prevent recovery of valid recordings and progress',async()=>{
 const f=fixture({entries:{[prefix+'progress']:{version:1,...legacy},[prefix+'queue']:[null,{id:'broken',title:'Bad',url:'https://example.com/audio.mp3'},track]}});
 await f.engine.init();
 assert.equal(f.engine.ready,true);
 assert.equal(f.engine.queue.length,1);
 assert.equal(f.engine.current.id,'a');
 assert.equal(f.engine.positions.a.positionMs,65432);
});

test('durable checkpoints take precedence over stale UI/live state',async()=>{
 const f=fixture({entries:{
  [prefix+'progress']:{version:1,...legacy,savedAt:100},
  [prefix+'state']:{...legacy,positions:{a:{positionMs:0,durationMs:0}}},
  [prefix+'queue']:[track],
  'library-v1':{version:1,tracks:[{id:'a',position:1,duration:120}]},
 }});
 await f.engine.init({app:{runMode:'background'}});
 assert.equal(f.engine.positions.a.positionMs,65432);
 assert.equal(f.engine.savedPositions.a.positionMs,65432);
 assert.equal(f.audio.paused,true);
 assert.equal(f.engine.loaded,false);
});

test('upgrade recovers library-only progress without overwriting newer checkpoints',async()=>{
 const f=fixture({entries:{'library-v1':{version:1,tracks:[{id:'a',position:65.432,duration:120}]},[prefix+'queue']:[track]}});
 await f.engine.init({app:{runMode:'background'}});
 assert.equal(f.store.get(f.keys.progress).positions.a.positionMs,65432);
 assert.equal(f.store.get(f.keys.progress).positions.a.completed,false);
});

test('disk failure prevents save confirmation and retains the last checkpoint',async()=>{
 const f=fixture({entries:{[prefix+'state']:legacy,[prefix+'queue']:[track]}});
 await f.engine.init({app:{runMode:'background'}});
 const original=clone(f.store.get(f.keys.progress));
 f.fail(f.keys.progress);
 await f.engine.execute({op:'volume',value:.25});
 await assert.rejects(f.engine.publish(),/disk write failed/);
 assert.deepEqual(f.store.get(f.keys.progress),original);
 assert.equal(f.audio.paused,true);
});

test('resetting one shiur pauses it, saves zero, and preserves other shiurim',async()=>{
 const f=fixture({entries:{[prefix+'state']:{...legacy,positions:{...legacy.positions,b:{positionMs:23789,durationMs:120000}}},[prefix+'queue']:[track]}});
 await f.engine.init({app:{runMode:'background'}});
 f.audio.readyState=1;f.audio.currentTime=65.432;f.audio.paused=false;f.engine.loaded=true;
 await f.engine.execute({op:'reset_progress',id:'a'});await f.engine.publish();
 const positions=f.store.get(f.keys.progress).positions;
 assert.equal(f.audio.paused,true);
 assert.equal(f.audio.currentTime,0);
 assert.equal(positions.a.positionMs,0);
 assert.equal(positions.a.completed,false);
 assert.equal(positions.b.positionMs,23789);
 assert.equal(f.store.get(f.keys.state).savedPositionMs,0);
});

test('delayed snapshots cannot move the visible player backwards',()=>{
 const f=fixture();const player=new f.context.VisiblePlayback(f.audio);
 player.apply({session:'new',updatedAt:200,currentId:'a',positionMs:65432,status:'paused'});
 player.apply({session:'old',updatedAt:100,currentId:'b',positionMs:0,status:'paused'});
 assert.equal(player.state.currentId,'a');assert.equal(player.position,65.432);
});

test('continue listening retains near-end progress and sorts recent shiurim first',()=>{
 const f=fixture(),C=f.context.ShiurCore;
 const state=C.normalize({version:1,tracks:[
  {id:'near',name:'Near end',position:119.987,duration:120,lastListenedAt:5},
  {id:'recent',name:'Recent',position:10,duration:120,lastListenedAt:10},
  {id:'finished',name:'Finished',position:120,duration:120,lastListenedAt:20},
 ]});
 assert.deepEqual(Array.from(C.viewTracks(state,'continue'),t=>t.id),['recent','near']);
 assert.equal(C.progressLabel(state.tracks[2]),'ההאזנה הושלמה');
});
