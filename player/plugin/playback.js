(function(root){
'use strict';
class VisiblePlayback {
 constructor(audio){
  this.handlesQueue=true;this.supportsBackground=false;this.handlers={};this.state={};this.queue=[];this.visible=true;this.revision=0;
  this.local=new LocalAudioEngine(audio);this.local.onChange=state=>this.apply(state);
 }
 on(name,handler){(this.handlers[name]||=[]).push(handler);}
 emit(name){for(const handler of this.handlers[name]||[])handler();}
 apply(state){
  const old=this.state;if(old.updatedAt>state.updatedAt)return old;this.state=state;
  if(['speed','volume','skipSeconds','autoNext'].some(key=>old[key]!==state[key]))this.emit('statechange');
  if(old.currentId!==state.currentId)this.emit('trackchange');this.emit('timeupdate');
  if(old.status!==state.status){if(state.status==='playing')this.emit('play');else if(state.status==='paused')this.emit('pause');}
  if(state.error){this.error=state.error;this.emit('error');}return state;
 }
 async init(){
  await this.local.init();
  if(this.local.current)await this.local.serial(async()=>{try{await this.local.load(this.local.current);}catch(error){this.local.error='השיעור האחרון אינו זמין: '+error.message;}await this.local.publish();});
  return this.apply(this.local.snapshot());
 }
 async refresh(){return this.apply(this.local.snapshot());}
 send(op,args={}){
  return this.local.serial(async()=>{try{await this.local.execute({op,...args});await this.local.publish();return this.apply(this.local.snapshot());}catch(error){this.error=error.message;this.emit('error');throw error;}});
 }
 load(track,position){
  const revision=++this.revision,queue=this.queue;
  return this.local.serial(async()=>{if(revision!==this.revision)return false;await this.local.execute({op:'load',track,queue,positionMs:Math.round(position*1000)});await this.local.publish();return revision===this.revision;});
 }
 cancel(){this.revision++;globalThis.OfflineSpeechAnalysis?.cancel();}
 clear(){this.cancel();return this.send('clear');}
 play(){
  // Keep audio.play() in the original click handler, before any storage awaits.
  const action=this.local.play();
  return action.then(()=>this.local.serial(async()=>{await this.local.publish();return this.apply(this.local.snapshot());})).catch(error=>{this.error=error.message;this.emit('error');throw error;});
 }
 pause(){this.local.audio.pause();this.local.capture();return this.local.serial(async()=>{await this.local.publish();return this.apply(this.local.snapshot());});}
 suspend(){this.visible=false;return this.local.suspend();}
 async resume(){this.visible=true;await this.local.resume();return this.apply(this.local.snapshot());}
 seek(value){return this.send('seek',{positionMs:Math.round(Math.max(0,value)*1000)});}
 setSpeed(value){return this.send('speed',{value});}setVolume(value){return this.send('volume',{value});}
 setSkip(value){return this.send('skip_interval',{value});}setAutoNext(value){return this.send('autoNext',{value});}
 sleep(minutes){return this.send('sleep_timer',{minutes});}
 get position(){return (this.state.positionMs||0)/1000;}get duration(){return (this.state.durationMs||0)/1000;}get paused(){return this.local.audio.paused;}
}
root.VisiblePlayback=VisiblePlayback;
})(globalThis);
