/* Development decoder: bounded local byte ranges, never a full-file fetch. */
(function(root){
'use strict';
const MAX_FILE=2*1024**3,FRAME=15600,RATE=16000;
const ascii=(a,p,n)=>String.fromCharCode(...a.subarray(p,p+n));
class RangeFile {
 constructor(url,{signal,budgetMs=5000}={}){this.url=url;this.signal=signal;this.deadline=performance.now()+budgetMs;this.bytesRead=0;this.requests=0;this.size=null;this.etag=null;}
 check(){if(this.signal?.aborted)throw new DOMException('Scan cancelled','AbortError');if(performance.now()>this.deadline)throw Error('Fast-check time budget exceeded');}
 async read(start,length){
  this.check();if(!Number.isSafeInteger(start)||start<0||!Number.isSafeInteger(length)||length<1||length>262144)throw Error('Invalid byte range');
  const end=this.size===null?start+length-1:Math.min(this.size-1,start+length-1);
  if(end<start)throw Error('Range outside file');
  const response=await fetch(this.url,{headers:{Range:`bytes=${start}-${end}`},signal:this.signal});this.requests++;
  if(response.status!==206){await response.body?.cancel();throw Error('Local file server must support byte ranges; full-file fallback is disabled');}
  const match=/^bytes (\d+)-(\d+)\/(\d+)$/.exec(response.headers.get('content-range')||'');
  if(!match||Number(match[1])!==start||Number(match[2])!==Math.min(end,Number(match[3])-1)||Number(match[3])>MAX_FILE){await response.body?.cancel();throw Error('Invalid or oversized partial response');}
  const size=Number(match[3]),tag=response.headers.get('etag');
  if(size<=0||(this.size!==null&&this.size!==size)||(this.etag&&this.etag!==tag)){await response.body?.cancel();throw Error('File changed during check');}
  this.size=size;if(tag)this.etag=tag;
  const reader=response.body.getReader(),chunks=[];let count=0;const expected=Number(match[2])-start+1;
  try{while(true){this.check();const {done,value}=await reader.read();if(done)break;count+=value.length;if(count>expected)throw Error('Oversized partial body');chunks.push(value);}}
  catch(e){await reader.cancel();throw e;}
  if(count!==expected)throw Error('Truncated partial body');
  this.bytesRead+=count;this.check();const out=new Uint8Array(count);let offset=0;for(const chunk of chunks){out.set(chunk,offset);offset+=chunk.length;}return out;
 }
}
function mp3Header(a,p){
 if(p+4>a.length||a[p]!==255||(a[p+1]&224)!==224)return null;
 const version=(a[p+1]>>3)&3,layer=(a[p+1]>>1)&3,bi=a[p+2]>>4,si=(a[p+2]>>2)&3;
 if(version===1||layer!==1||bi===0||bi===15||si===3)return null;
 const mpeg1=version===3,rate=[44100,48000,32000][si]/(mpeg1?1:version===2?2:4);
 const kbps=(mpeg1?[0,32,40,48,56,64,80,96,112,128,160,192,224,256,320]:[0,8,16,24,32,40,48,56,64,80,96,112,128,144,160])[bi];
 return {rate,samples:mpeg1?1152:576,length:Math.floor((mpeg1?144:72)*kbps*1000/rate)+((a[p+2]>>1)&1),version,mono:(a[p+3]>>6)===3,kbps};
}
function firstFrame(a){
 for(let p=0;p<a.length-12;p++){
  const h=mp3Header(a,p);if(!h)continue;const b=mp3Header(a,p+h.length),c=b&&mp3Header(a,p+h.length+b.length);
  if(b&&c&&b.rate===h.rate&&c.rate===h.rate&&b.version===h.version&&c.version===h.version)return {offset:p,...h};
 }
 throw Error('No supported MPEG Layer III audio frames');
}
async function probe(file,hostDuration){
 const head=await file.read(0,65536);
 if(ascii(head,0,4)==='RIFF'&&ascii(head,8,4)==='WAVE'){
  const riffEnd=new DataView(head.buffer,head.byteOffset,head.byteLength).getUint32(4,true)+8;
  if(riffEnd<12||riffEnd>file.size)throw Error('Invalid RIFF container size');
  let pos=12,format=null;
  for(let i=0;i<128&&pos+8<=riffEnd;i++){
   let bytes=pos+8<=head.length?head.subarray(pos,Math.min(head.length,pos+64)):await file.read(pos,64),view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength),id=ascii(bytes,0,4),size=view.getUint32(4,true);
   if(pos+8+size+(size&1)>riffEnd)throw Error('Invalid WAV chunk length');
   if(id==='fmt '){
    if(format)throw Error('Duplicate WAV format chunk');
    const needed=Math.min(64,8+size);if(bytes.length<needed){bytes=await file.read(pos,needed);view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);}
    if(size<16||bytes.length<24)throw Error('Invalid WAV format');
    let codec=view.getUint16(8,true);const channels=view.getUint16(10,true),rate=view.getUint32(12,true),align=view.getUint16(20,true),bits=view.getUint16(22,true);
    if(codec===65534){
     const suffix=[0,0,16,0,128,0,0,170,0,56,155,113];
     if(size<40||bytes.length<48||view.getUint16(24,true)<22||view.getUint16(26,true)<1||view.getUint16(26,true)>bits||suffix.some((v,i)=>bytes[36+i]!==v))throw Error('Unsupported extensible WAV format');
     codec=view.getUint32(32,true);
    }
    if(![1,3].includes(codec)||channels<1||channels>2||rate<8000||rate>192000||![16,24,32].includes(bits)||codec===3&&bits!==32||align!==channels*bits/8||view.getUint32(16,true)!==rate*align)throw Error('Unsupported WAV encoding');
    format={codec,channels,rate,align,bits};
   }
   if(id==='data'){
    if(!format||size%format.align)throw Error('Invalid WAV audio layout');
    return {kind:'wav',...format,dataStart:pos+8,dataBytes:size,duration:size/format.align/format.rate,head};
   }
   pos+=8+size+(size&1);
  }
  throw Error('WAV audio chunk not found');
 }
 let start=0,initial=head;
 for(let tags=0;ascii(initial,0,3)==='ID3';tags++){
  if(tags>=8||initial.length<10||![2,3,4].includes(initial[3])||[6,7,8,9].some(p=>initial[p]&128))throw Error('Invalid ID3 tag');
  start+=10+initial[6]*2097152+initial[7]*16384+initial[8]*128+initial[9]+((initial[3]===4&&(initial[5]&16))?10:0);
  if(start>16*1024**2||start>=file.size)throw Error('Unsupported metadata size');
  initial=start<head.length-16?head.subarray(start):await file.read(start,65536);
 }
 const h=firstFrame(initial);
 if(initial.subarray(0,h.offset).some(value=>value!==0))throw Error('Unsupported file prefix; expected MPEG audio');
 start+=h.offset;
 // Xing/Info frame count supplies a bounded metadata duration for VBR/CBR.
 const view=new DataView(initial.buffer,initial.byteOffset,initial.byteLength);let duration=hostDuration,toc=null,streamBytes=file.size-start,durationSource='host-metadata';
 // Xing/Info follows the MPEG header and side-info (same layout as FFmpeg's parser).
 const p=h.offset+4+(h.version===3?(h.mono?17:32):(h.mono?9:17)),frameEnd=h.offset+h.length;
 if(p+8<=frameEnd&&['Xing','Info'].includes(ascii(initial,p,4))){
  const flags=view.getUint32(p+4,false);let at=p+8;
  const requireBytes=count=>{if(at+count>frameEnd)throw Error('Truncated MPEG metadata');};
  if(flags&1){requireBytes(4);duration=view.getUint32(at,false)*h.samples/h.rate;durationSource='mpeg-frame-count';at+=4;}
  if(flags&2){requireBytes(4);streamBytes=view.getUint32(at,false);at+=4;if(streamBytes<=0||streamBytes>file.size-start)throw Error('Invalid MPEG stream length');}
  if(flags&4){requireBytes(100);toc=initial.slice(at,at+100);at+=100;if(toc.some((v,i)=>i>0&&v<toc[i-1]))throw Error('Invalid MPEG seek table');}
  if(flags&8)requireBytes(4);
 }
 if(!Number.isFinite(duration))throw Error('MP3 requires a finite metadata duration');
 return {kind:'mp3',...h,dataStart:start,dataBytes:streamBytes,duration,durationSource,toc,head};
}
function toMono(channels){
 if(!channels.length||channels.length>2||channels.some(a=>a.length!==channels[0].length))throw Error('Unsupported channel layout');
 const output=new Float32Array(channels[0].length);let left=0,right=0,mixed=0;
 for(let i=0;i<output.length;i++){
  const a=channels[0][i],b=channels.length===2?channels[1][i]:a;if(!Number.isFinite(a)||!Number.isFinite(b))throw Error('Invalid PCM sample');
  output[i]=(a+b)/2;left+=a*a;right+=b*b;mixed+=output[i]*output[i];
 }
 const strongest=Math.max(left,right),weakest=Math.min(left,right);
 // Preserve normal averaging, but avoid cancelling speech or halving a lone active channel.
 if(strongest>0&&(mixed<strongest*.05||weakest<strongest*.0001))return channels[right>left?1:0].slice();
 return output;
}
async function wavSamples(file,info,seconds){
 const first=Math.floor(seconds*info.rate),frames=Math.ceil(FRAME/RATE*info.rate),length=frames*info.align,bytes=new Uint8Array(length);
 for(let offset=0;offset<length;offset+=262144){const chunk=await file.read(info.dataStart+first*info.align+offset,Math.min(262144,length-offset));bytes.set(chunk,offset);}
 const view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength),channels=Array.from({length:info.channels},()=>new Float32Array(Math.floor(bytes.length/info.align)));
 for(let n=0;n<channels[0].length;n++)for(let ch=0;ch<info.channels;ch++){
  const p=n*info.align+ch*info.bits/8;let value;
  if(info.codec===3)value=view.getFloat32(p,true);
  else if(info.bits===16)value=view.getInt16(p,true)/32768;
  else if(info.bits===24){let v=view.getUint8(p)|view.getUint8(p+1)<<8|view.getUint8(p+2)<<16;if(v&8388608)v-=16777216;value=v/8388608;}
  else value=view.getInt32(p,true)/2147483648;
  if(!Number.isFinite(value))throw Error('Invalid PCM sample');channels[ch][n]=value;
 }
 const mono=toMono(channels),context=new OfflineAudioContext(1,FRAME,RATE),buffer=context.createBuffer(1,mono.length,info.rate);buffer.copyToChannel(mono,0);const source=context.createBufferSource();source.buffer=buffer;source.connect(context.destination);source.start();const rendered=await context.startRendering();file.check();return rendered.getChannelData(0).slice(0,FRAME);
}
async function mp3Samples(file,info,seconds){
 const fraction=seconds/info.duration;let byteFraction=fraction;
 if(info.toc){const x=fraction*100,i=Math.min(99,Math.floor(x));byteFraction=(info.toc[i]+((i===99?256:info.toc[i+1])-info.toc[i])*(x-i))/256;}
 const target=info.dataStart+Math.floor(info.dataBytes*byteFraction),begin=Math.max(info.dataStart,target-32768),bytes=await file.read(begin,98304),first=firstFrame(bytes),frames=[];let p=first.offset;
 while(p+4<=bytes.length){const h=mp3Header(bytes,p);if(!h||h.rate!==info.rate||p+h.length>bytes.length)break;frames.push({offset:p,...h});p+=h.length;}
 const index=frames.findIndex(f=>begin+f.offset>=target);if(index<0)throw Error('MP3 sample could not be located');
 const from=Math.max(0,index-20),needed=Math.ceil(1.1*info.rate/info.samples),end=Math.min(frames.length,index+needed+2);
 if(end-index<needed)throw Error('Not enough complete MP3 frames');
 const data=bytes.slice(frames[from].offset,frames[end-1].offset+frames[end-1].length),context=new OfflineAudioContext(1,1,RATE);
 const decoded=await context.decodeAudioData(data.buffer),offset=Math.round((index-from)*info.samples/info.rate*RATE);
 if(decoded.length<offset+FRAME)throw Error('Browser cannot decode the selected MP3 frames');
 const result=toMono(Array.from({length:decoded.numberOfChannels},(_,ch)=>decoded.getChannelData(ch).subarray(offset,offset+FRAME)));
 file.check();return result;
}
async function prepare(url,options={}){
 const file=new RangeFile(url,options),info=await probe(file,options.duration);
 if(!Number.isFinite(info.duration)||info.duration<300||info.duration>8*3600)throw Error('Recording must be between five minutes and eight hours');
 const seed=new Uint8Array(info.head.length+8);seed.set(info.head);new DataView(seed.buffer).setFloat64(info.head.length,file.size,true);
 const hash=new Uint8Array(await crypto.subtle.digest('SHA-256',seed)),u=new DataView(hash.buffer),times=[(.2+.15*u.getUint32(0)/4294967296)*info.duration,(.65+.15*u.getUint32(4)/4294967296)*info.duration];
 return {file,info,times,async samples(){return Promise.all(times.map(t=>info.kind==='wav'?wavSamples(file,info,t):mp3Samples(file,info,t)));}};
}
root.RangeAudio={prepare,RangeFile,mp3Header,firstFrame,toMono};
})(globalThis);
