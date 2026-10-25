/* Adapter boundary for a future host-owned audio service. No speculative RPC calls. */
(function(root){
  'use strict';
  class WebAudioPlayback {
    constructor(audio){this.audio=audio;this.supportsBackground=false;this.revision=0;this.cancelPending=null;}
    on(event,callback){this.audio.addEventListener(event,callback);}
    async load(url,position,speed){
      this.cancel();
      const revision=this.revision;
      this.audio.pause();
      return new Promise((resolve,reject)=>{
        const clean=()=>{this.audio.removeEventListener('loadedmetadata',ready);this.audio.removeEventListener('error',failed);clearTimeout(timer);this.cancelPending=null;};
        const ready=()=>{clean();if(revision!==this.revision)return resolve(false);this.audio.playbackRate=speed;this.seek(position);resolve(true);};
        const failed=()=>{clean();reject(new Error('לא ניתן לנגן קובץ זה. ייתכן שהפורמט אינו נתמך במערכת או שהקובץ אינו זמין.'));};
        this.cancelPending=()=>{clean();resolve(false);};
        const timer=setTimeout(()=>{clean();reject(new Error('טעינת השיעור נמשכת זמן רב. בדקו שהקובץ זמין ונסו שוב.'));},20000);
        this.audio.addEventListener('loadedmetadata',ready);
        this.audio.addEventListener('error',failed);
        this.audio.src=url;this.audio.load();
      });
    }
    cancel(){this.revision++;if(this.cancelPending)this.cancelPending();}
    clear(){this.cancel();this.pause();this.audio.removeAttribute('src');this.audio.load();}
    play(){return this.audio.play();}
    pause(){this.audio.pause();}
    seek(seconds){if(Number.isFinite(this.duration)&&this.duration>0)this.audio.currentTime=Math.max(0,Math.min(seconds,this.duration));}
    setSpeed(speed){this.audio.playbackRate=speed;}
    setVolume(volume){this.audio.volume=volume;}
    get position(){return this.audio.currentTime||0;}
    get duration(){return Number.isFinite(this.audio.duration)?this.audio.duration:0;}
    get paused(){return this.audio.paused;}
  }
  root.WebAudioPlayback=WebAudioPlayback;
})(globalThis);
