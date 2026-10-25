"""Offline YAMNet exploratory evaluation; never changes the plugin or its policy.
Requires ai-edge-litert, numpy and ffmpeg. Assets are supplied locally, not uploaded.
Rule fixed before the first run: >=10% frames with music/singing score >=.5 =>
block; otherwise >=50% frames with Speech score >=.5 => allow; else uncertain.
Short benchmark clips intentionally bypass the separate five-minute rule.
"""
import argparse,csv,hashlib,json,pathlib,platform,resource,subprocess,time
from importlib.metadata import version
import numpy as np
from ai_edge_litert.interpreter import Interpreter

def digest(path):
 h=hashlib.sha256()
 with pathlib.Path(path).open('rb') as stream:
  for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--sustained-frames',type=int,default=0,help='Post-hoc candidate: also block this many consecutive music frames; 0 disables');p.add_argument('--assets',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
 model=args.assets/'yamnet.tflite';classes=list(csv.DictReader((args.assets/'yamnet_class_map.csv').open()));ids={r['display_name']:int(r['index']) for r in classes}
 runner=Interpreter(model_path=str(model),num_threads=2);runner.allocate_tensors();inp=runner.get_input_details()[0];out=runner.get_output_details()[0];size=int(inp['shape'][0]);runner.set_tensor(inp['index'],np.zeros(size,np.float32));runner.invoke()
 items=[(f,f.parent.name.replace('_wav','')) for f in sorted((args.assets/'data').rglob('*.wav'))]+[(f,'shiur') for f in sorted(args.assets.glob('shiur_*.mp3'))]+[(f,'stress') for f in sorted((args.assets/'stress').glob('*.wav'))]
 results=[];start=time.perf_counter();inference=0
 with (args.output/'windows.csv').open('w',newline='') as stream:
  windows=csv.writer(stream);windows.writerow(['file','seconds','speech','music','singing','silence'])
  for n,(file,label) in enumerate(items):
   proc=subprocess.Popen(['ffmpeg','-v','error','-i',str(file),'-vn','-f','f32le','-ac','1','-ar','16000','pipe:1'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
   samples=0;rows=[];weights=[];file_start=time.perf_counter()
   while True:
    raw=proc.stdout.read(size*4)
    if not raw:break
    audio=np.frombuffer(raw,dtype='<f4');length=len(audio)
    if length<size:audio=np.pad(audio,(0,size-length))
    runner.set_tensor(inp['index'],audio);t=time.perf_counter();runner.invoke();inference+=time.perf_counter()-t;scores=runner.get_tensor(out['index'])[0]
    values=[float(scores[ids[k]]) for k in ['Speech','Music','Singing','Silence']];windows.writerow([file.name,round(samples/16000,4),*values]);rows.append(values);weights.append(length);samples+=length
   error=proc.stderr.read().decode();code=proc.wait()
   if code:raise RuntimeError(str(file)+': '+error)
   a=np.array(rows);w=np.array(weights);music=float(np.average(np.maximum(a[:,1],a[:,2])>=.5,weights=w));speech=float(np.average(a[:,0]>=.5,weights=w));longest=run=0
   for hit in np.maximum(a[:,1],a[:,2])>=.5:
    run=run+1 if hit else 0;longest=max(longest,run)
   decision='block' if music>=.1 or (args.sustained_frames>0 and longest>=args.sustained_frames) else 'allow' if speech>=.5 else 'uncertain'
   results.append(dict(file=file.name,label=label,sha256=digest(file),seconds=samples/16000,music_fraction=music,speech_fraction=speech,longest_music_run_frames=int(longest),decision=decision,wall_seconds=time.perf_counter()-file_start))
   if (n+1)%10==0 or n+1==len(items):print(f'Processed {n+1}/{len(items)}',flush=True)
 summary={label:{decision:sum(r['label']==label and r['decision']==decision for r in results) for decision in ['allow','block','uncertain']} for label in sorted({r['label'] for r in results})}
 result=dict(runtime=version('ai-edge-litert'),python=platform.python_version(),platform=platform.platform(),model_sha256=digest(model),model_bytes=model.stat().st_size,model_url='https://storage.googleapis.com/audioset/yamnet.tflite',dataset_zip_sha256=digest(args.assets/'dataset.zip'),frame_samples=size,sample_rate=16000,threads=2,sustained_frames=args.sustained_frames,rule='music-or-singing >=.5 in >=10% frames: block; else speech >=.5 in >=50% frames: allow; else uncertain',seconds_of_audio=sum(r['seconds'] for r in results),wall_seconds=time.perf_counter()-start,inference_seconds=inference,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,summary=summary,files=results)
 (args.output/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='files'},indent=2))
if __name__=='__main__':main()
