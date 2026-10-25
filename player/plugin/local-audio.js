(function(root){
'use strict';
const P=ShiurProtocol,K=P.keys;
class LocalAudioEngine {
 constructor(audio){
  this.audio=audio;this.audio.muted=true;this.session=ShiurCore.uuid();this.queue=[];this.current=null;this.loaded=false;this.positions=Object.create(null);this.savedPositions=Object.create(null);this.savedAt=0;this.restored=false;
  this.speed=1;this.volume=1;this.skipSeconds=15;this.autoNext=false;this.sleepUntil=0;this.error='';this.storageError='';
  this.tail=Promise.resolve();this.ready=false;this.running=false;this.closed=false;this.visible=true;this.lastAccess=0;
 }
 serial(action){const next=this.tail.then(action);this.tail=next.catch(error=>{this.error=error.message;});return next;}
 capture(){
  if(this.current&&this.loaded&&this.audio.readyState>0){
   const positionMs=Math.round(this.audio.currentTime*1000),durationMs=Number.isFinite(this.audio.duration)?Math.round(this.audio.duration*1000):0;
   const old=this.positions[this.current.id];
   if(!old||old.positionMs!==positionMs||old.durationMs!==durationMs||old.completed!==this.audio.ended){
    this.positions[this.current.id]={positionMs,durationMs,completed:this.audio.ended,lastListenedAt:Date.now()};
   }
  }
 }
 snapshot(){
  this.capture();const progress=this.positions[this.current?.id]||{};
  return {session:this.session,ready:this.ready,savedAt:this.savedAt,savedPositionMs:this.savedPositions[this.current?.id]?.positionMs??null,updatedAt:Date.now(),currentId:this.current?.id||null,status:this.error?'error':!this.current?'empty':!this.loaded?'paused':this.audio.ended?'ended':this.audio.paused?'paused':'playing',
   positionMs:progress.positionMs||0,durationMs:progress.durationMs||0,positions:this.positions,speed:this.speed,volume:this.volume,skipSeconds:this.skipSeconds,autoNext:this.autoNext,
   sleepRemaining:Math.max(0,Math.ceil((this.sleepUntil-Date.now())/1000)),error:this.error||this.storageError};
 }
 checkpoint(){
  return {version:1,currentId:this.current?.id||null,positions:JSON.parse(JSON.stringify(this.positions)),speed:this.speed,volume:this.volume,skipSeconds:this.skipSeconds,autoNext:this.autoNext};
 }
 async publish(){
  try{
   this.capture();
   if(this.restored){
    const checkpoint=this.checkpoint(),fingerprint=JSON.stringify(checkpoint);
    if(fingerprint!==this.lastCheckpoint){
     const savedAt=Date.now();
     await P.rpc('storage.set',{key:K.progress,value:{...checkpoint,savedAt}});
     this.savedAt=savedAt;this.savedPositions=P.positions(checkpoint.positions);this.lastCheckpoint=fingerprint;
    }
   }
   this.storageError='';const state=this.snapshot();await P.rpc('storage.set',{key:K.state,value:state});this.onChange?.(state);
  }catch(error){this.audio.pause();this.storageError='שמירת ההתקדמות נכשלה: '+error.message;throw error;}
 }
 async restore(){
  const live=await P.rpc('storage.get',{key:K.state});
  const durable=await P.rpc('storage.get',{key:K.progress});
  const hasDurable=durable?.version===1&&durable.positions&&typeof durable.positions==='object'&&!Array.isArray(durable.positions);
  const saved=hasDurable?durable:live;
  this.positions=P.positions(saved?.positions);
  if(!hasDurable){
   const library=await P.rpc('storage.get',{key:'library-v1'});
   for(const track of library?.version===1&&Array.isArray(library.tracks)?library.tracks:[]){
    if(typeof track.id==='string'&&!Object.hasOwn(this.positions,track.id)&&Number.isFinite(track.position)&&track.position>=0){
     const legacy=P.positions({[track.id]:{positionMs:track.position*1000,durationMs:(track.duration||0)*1000}});
     Object.assign(this.positions,legacy);
    }
   }
  }
  this.speed=P.rates.includes(saved?.speed)?saved.speed:1;
  this.volume=Number.isFinite(saved?.volume)?Math.max(0,Math.min(1,saved.volume)):1;
  this.skipSeconds=[10,15,60].includes(saved?.skipSeconds)?saved.skipSeconds:15;this.autoNext=saved?.autoNext===true;
  const queue=await P.rpc('storage.get',{key:K.queue});
  if(Array.isArray(queue)){
   this.queue=[];const seen=new Set();
   for(const entry of queue.slice(0,2000)){
    try{const track=P.source(entry);if(!seen.has(track.id)){this.queue.push(track);seen.add(track.id);}}
    catch{this.restoreWarning='חלק מהפריטים השמורים אינם זמינים. הספרייה ומיקומי ההאזנה נשמרו; אפשר לבחור שיעור אחר.';}
   }
  }
  this.current=this.queue.find(t=>t.id===saved?.currentId)||null;
  if(hasDurable){this.savedAt=durable.savedAt||0;this.savedPositions=P.positions(durable.positions);this.lastCheckpoint=JSON.stringify(this.checkpoint());}
  this.restored=true;
 }
 async init(){
  if(this.ready)return;
  if(!this.restored)await this.restore();
  const {permissions=[]}=await P.rpc('app.getGrantedPermissions');
  if(!permissions.includes('fs.user_files.read')){throw Error('יש לאשר לתוסף קריאת קבצים בהגדרות אוצריא');}
  this.audio.playbackRate=this.speed;this.audio.volume=this.volume;
  if(!this.listenersAttached){this.listenersAttached=true;
  this.audio.addEventListener('contextmenu',event=>event.preventDefault());
  this.audio.addEventListener('volumechange',()=>{this.volume=this.audio.volume;if(this.ready&&!this.closed)this.serial(()=>this.publish());});
  this.audio.addEventListener('ratechange',()=>{if(P.rates.includes(this.audio.playbackRate))this.speed=this.audio.playbackRate;if(this.ready&&!this.closed)this.serial(()=>this.publish());});
  this.audio.addEventListener('ended',()=>this.serial(async()=>{this.capture();await this.expireSleep();if(this.autoNext&&!this.sleepExpired&&this.visible)await this.advance(1);await this.publish();}));
  this.audio.addEventListener('error',()=>{this.audio.pause();this.error='לא ניתן לנגן את קובץ השמע. בדקו את הפורמט ואת הרשאת הקובץ.';this.serial(()=>this.publish());});
  this.audio.addEventListener('pause',()=>{this.capture();if(!this.closed)this.serial(()=>this.publish());});
  this.audio.addEventListener('durationchange',()=>{if(this.loaded&&!this.allowedDuration())this.blockShortAudio();});
  this.audio.addEventListener('play',()=>{if(!this.visible||!this.ready||!this.loaded||!this.allowedDuration()){this.audio.pause();return;}this.error='';this.serial(()=>this.publish());});
  this.audio.addEventListener('seeked',()=>{this.capture();if(this.ready&&!this.closed)this.serial(()=>this.publish());});
  }
  this.ready=true;this.setupMediaSession();try{await this.publish();}catch(error){this.ready=false;throw error;}
  this.timer=setInterval(()=>this.tick(),250);
  window.addEventListener('pagehide',()=>{this.closed=true;this.audio.pause();this.capture();this.publish().catch(error=>console.error(error.message));});
 }
 setupMediaSession(){
  if(!navigator.mediaSession)return;
  const handlers={play:()=>this.execute({op:'play'}),pause:()=>this.execute({op:'pause'}),stop:()=>this.execute({op:'stop'}),previoustrack:()=>this.execute({op:'previous'}),nexttrack:()=>this.execute({op:'next'}),seekbackward:()=>this.execute({op:'skip',direction:-1}),seekforward:()=>this.execute({op:'skip',direction:1}),seekto:event=>this.execute({op:'seek',positionMs:Math.round(event.seekTime*1000)})};
  for(const [name,handler] of Object.entries(handlers)){
   try{navigator.mediaSession.setActionHandler(name,event=>this.serial(async()=>{await handler(event);await this.publish();}));}catch(error){if(error.name!=='NotSupportedError')console.error(error.message);}
  }
 }
 async resolve(track){
  const file=track.folderToken?await P.rpc('fs.openFolderFile',{folderToken:track.folderToken,path:track.path}):await P.rpc('fs.resolveFileUrl',{token:track.token});
  if(typeof file?.url!=='string')throw Error('לא התקבלה גישה לקובץ השמע');
  return file.url;
 }
 allowedDuration(){return Number.isFinite(this.audio.duration)&&this.audio.duration>=300;}
 blockShortAudio(){
  this.loaded=false;this.audio.muted=true;this.audio.pause();
  this.error='ניתן לנגן רק הקלטות באורך חמש דקות ומעלה. הקלטה קצרה או שאורכה אינו ידוע חסומה.';
  this.audio.removeAttribute('src');this.audio.load();
  return Error(this.error);
 }
 async load(track,initial=0){
  const url=await this.resolve(track);
  this.audio.pause();this.capture();await this.publish();this.audio.muted=true;
  this.current=track;this.loaded=false;this.error='';this.sleepExpired=false;
  const start=this.positions[track.id]?.positionMs??P.position(initial);
  await new Promise((resolve,reject)=>{
   const clean=()=>{clearTimeout(timer);this.audio.removeEventListener('loadedmetadata',ready);this.audio.removeEventListener('error',failed);};
   const ready=()=>{clean();if(!this.allowedDuration()){reject(this.blockShortAudio());return;}resolve();};
   const failed=()=>{clean();reject(Error(this.audio.error?.code===4?'פורמט השמע אינו נתמך בנגן של אוצריא. נסו קובץ MP3 או WAV.':'לא ניתן לקרוא את השיעור. בדקו שהקובץ קיים ושהגישה אליו מאושרת.'));};
   const timer=setTimeout(()=>{clean();reject(Error('טעינת השיעור ארכה זמן רב מדי'));},15000);
   this.audio.addEventListener('loadedmetadata',ready,{once:true});this.audio.addEventListener('error',failed,{once:true});
   this.audio.src=url;this.audio.load();
  });
  this.audio.playbackRate=this.speed;this.audio.volume=this.volume;
  this.audio.currentTime=Math.min(start/1000,Number.isFinite(this.audio.duration)?this.audio.duration:start/1000);
  this.loaded=true;this.audio.muted=false;this.capture();this.lastAccess=Date.now();
  if(navigator.mediaSession&&root.MediaMetadata)navigator.mediaSession.metadata=new MediaMetadata({title:track.title,artist:'נגן שיעורים — אוצריא'});
 }
 play(){
  if(!this.ready||!this.visible||this.closed)return Promise.reject(Error('פתחו את נגן השיעורים כדי להפעיל את השמע'));
  if(!this.current||!this.loaded)return Promise.reject(Error('בחרו שיעור והמתינו לטעינה, ואז לחצו על ניגון'));
  if(!this.allowedDuration())return Promise.reject(this.blockShortAudio());
  this.error='';this.sleepExpired=false;
  return this.audio.play().catch(error=>{
   this.audio.pause();
   throw Error(error.name==='NotAllowedError'?'השיעור מוכן. לחצו על כפתור הניגון בפס השמע שמתחת לפקדים.':error.message);
  });
 }
 async advance(delta){const index=this.queue.findIndex(t=>t.id===this.current?.id)+delta;if(index>=0&&index<this.queue.length){await this.load(this.queue[index]);await this.play();}}
 async expireSleep(){if(this.sleepUntil&&Date.now()>=this.sleepUntil){this.sleepUntil=0;this.sleepExpired=true;this.audio.pause();this.capture();}}
 async execute(args){
  if(!this.ready||this.closed)throw Error('הנגן אינו פעיל או שהרשאת הקבצים בוטלה');
  const op=args.op==='toggle'?(this.audio.paused?'play':'pause'):args.op;
  await this.expireSleep();
  switch(op){
   case 'load':{
    const track=P.source(args.track);
    if(!Array.isArray(args.queue)||args.queue.length>2000)throw Error('תור השמעה לא תקין');
    const queue=args.queue.map(P.source);
    if(new Set(queue.map(t=>t.id)).size!==queue.length)throw Error('מזהים כפולים בתור');
    const index=queue.findIndex(t=>t.id===track.id);if(index<0){if(queue.length>=2000)throw Error('תור ההשמעה מלא');queue.push(track);}else queue[index]=track;
    P.position(args.positionMs??0);await this.resolve(track);
    await this.load(track,args.positionMs??0);this.queue=queue;
    await P.rpc('storage.set',{key:K.queue,value:queue});break;
   }
   case 'play':await this.play();break;
   case 'pause':this.audio.pause();this.capture();break;
   case 'stop':this.audio.pause();this.capture();this.sleepUntil=0;break;
   case 'clear':this.audio.pause();this.capture();this.current=null;this.loaded=false;this.queue=[];this.sleepUntil=0;this.audio.removeAttribute('src');this.audio.load();await P.rpc('storage.set',{key:K.queue,value:[]});break;
   case 'reset_progress':{
    if(typeof args.id!=='string'||!Object.hasOwn(this.positions,args.id))throw Error('לא נמצא מיקום שמור לשיעור');
    if(this.current?.id===args.id){this.audio.pause();if(this.loaded)this.audio.currentTime=0;}
    this.positions[args.id]={...this.positions[args.id],positionMs:0,completed:false,lastListenedAt:Date.now()};
    break;
   }
   case 'seek':{
    const value=P.position(args.positionMs);if(!this.current)throw Error('יש לבחור שיעור');if(!this.loaded)await this.load(this.current);
    this.audio.currentTime=Math.min(value/1000,Number.isFinite(this.audio.duration)?this.audio.duration:value/1000);this.capture();break;
   }
   case 'skip':if(![-1,1].includes(args.direction))throw Error('כיוון דילוג לא תקין');await this.execute({op:'seek',positionMs:Math.max(0,this.snapshot().positionMs+args.direction*this.skipSeconds*1000)});break;
   case 'speed':if(!P.rates.includes(args.value))throw Error('מהירות לא תקינה');this.speed=args.value;this.audio.playbackRate=this.speed;break;
   case 'speed_step':if(![-1,1].includes(args.direction))throw Error('כיוון לא תקין');this.speed=P.rates[Math.max(0,Math.min(P.rates.length-1,P.rates.indexOf(this.speed)+args.direction))];this.audio.playbackRate=this.speed;break;
   case 'volume':if(!Number.isFinite(args.value)||args.value<0||args.value>1)throw Error('עוצמה לא תקינה');this.volume=args.value;this.audio.volume=this.volume;break;
   case 'skip_interval':if(![10,15,60].includes(args.value))throw Error('משך דילוג לא תקין');this.skipSeconds=args.value;break;
   case 'autoNext':if(typeof args.value!=='boolean')throw Error('ערך לא תקין');this.autoNext=args.value;break;
   case 'sleep_timer':if(!Number.isFinite(args.minutes)||args.minutes<0||args.minutes>180)throw Error('טיימר לא תקין');this.sleepUntil=args.minutes?Date.now()+args.minutes*60000:0;this.sleepExpired=false;break;
   case 'next':await this.advance(1);break;
   case 'previous':await this.advance(-1);break;
   default:throw Error('פקודת שמע לא מוכרת');
  }
  this.capture();return this.snapshot();
 }
 async tick(){
  if(this.running||this.closed||!this.ready)return;this.running=true;
  try{await this.serial(async()=>{
   await this.expireSleep();
   if(Date.now()-(this.lastPermissionCheck||0)>5000){
    this.lastPermissionCheck=Date.now();const {permissions=[]}=await P.rpc('app.getGrantedPermissions');
    if(!permissions.includes('fs.user_files.read')){this.audio.pause();this.capture();this.ready=false;clearInterval(this.timer);this.timer=null;this.error='הרשאת קריאת הקבצים בוטלה';await this.publish();return;}
   }
   if(this.current&&this.loaded&&Date.now()-this.lastAccess>5000){this.lastAccess=Date.now();try{await this.resolve(this.current);}catch(error){this.audio.pause();this.error='הגישה לקובץ בוטלה: '+error.message;}}
   if(Date.now()-(this.lastPublished||0)>=(this.audio.paused?2000:500)){await this.publish();this.lastPublished=Date.now();}
  });}catch(error){this.audio.pause();this.error=error.message;console.error(error.message);}
  finally{this.running=false;}
 }
 resume(){
  this.visible=true;if(this.ready&&!this.closed&&!this.timer)this.timer=setInterval(()=>this.tick(),250);
  return this.serial(()=>this.publish());
 }
 suspend(){
  this.visible=false;this.audio.pause();this.capture();clearInterval(this.timer);this.timer=null;
  return this.serial(()=>this.publish());
 }
}
root.LocalAudioEngine=LocalAudioEngine;
})(globalThis);
