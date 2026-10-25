"""Offline local scanner prototype. Does not install or change Inside.
python scan.py --model /path/yamnet.tflite --classes /path/yamnet_class_map.csv --output report.json recording.mp3 [...]
"""
import argparse,csv,hashlib,html,json,pathlib,subprocess,tempfile,time
import numpy as np
from ai_edge_litert.interpreter import Interpreter
from policy import decide
MODEL_SHA='e193da5676a2fdb7a3702c10fba62aa27d76f64e4534467443811c1a2ff1667d'
def sha(file):
 h=hashlib.sha256()
 with open(file,'rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--model',type=pathlib.Path,required=True);p.add_argument('--classes',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--balanced',action='store_true');p.add_argument('files',type=pathlib.Path,nargs='+');args=p.parse_args()
 if sha(args.model)!=MODEL_SHA:raise ValueError('Model checksum mismatch')
 classes={r['display_name']:int(r['index']) for r in csv.DictReader(args.classes.open())}
 if any(classes.get(k)!=v for k,v in {'Speech':0,'Singing':24,'Music':132}.items()):raise ValueError('Unexpected class mapping')
 engine=Interpreter(model_path=str(args.model),num_threads=2);engine.allocate_tensors();inp=engine.get_input_details()[0];out=engine.get_output_details()[0];size=int(inp['shape'][0]);results=[]
 for file in args.files:
  record={'file':file.name};start=time.perf_counter();proc=None
  try:
   before=file.stat();record['sha256']=sha(file);windows=[];samples=0
   with tempfile.TemporaryFile() as errors:
    proc=subprocess.Popen(['ffmpeg','-nostdin','-v','error','-protocol_whitelist','file,pipe','-i',str(file.resolve()),'-vn','-f','f32le','-ac','1','-ar','16000','pipe:1'],stdout=subprocess.PIPE,stderr=errors)
    while True:
     raw=proc.stdout.read(size*4)
     if not raw:break
     if len(raw)%4:raise ValueError('Incomplete audio frame')
     a=np.frombuffer(raw,dtype='<f4');n=len(a)
     if not np.isfinite(a).all():raise ValueError('Invalid decoded samples')
     engine.set_tensor(inp['index'],np.pad(a,(0,size-n)) if n<size else a);engine.invoke();scores=engine.get_tensor(out['index'])[0]
     windows.append(dict(start=samples/16000,seconds=n/16000,**{k.lower():float(scores[i]) for k,i in classes.items() if k in ['Speech','Music','Singing']}));samples+=n
    if proc.wait()!=0:errors.seek(0);raise ValueError('Decode failed: '+errors.read(500).decode(errors='replace'))
   if file.stat().st_mtime_ns!=before.st_mtime_ns or sha(file)!=record['sha256']:raise ValueError('File changed during analysis')
   record.update(decide(windows,strict=not args.balanced));record['duration_policy']='meets_five_minutes' if record.get('seconds',0)>=300 else 'below_five_minutes';record['playback_eligible']=record['decision']=='allow' and record['duration_policy']=='meets_five_minutes'
  except Exception as e:record.update(decision='error',reason=str(e),playback_eligible=False)
  finally:
   if proc and proc.poll() is None:proc.kill();proc.wait()
  record['wall_seconds']=time.perf_counter()-start;results.append(record);print(file.name,record['decision'],record.get('reason',''),flush=True)
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(dict(model_sha256=MODEL_SHA,experimental=True,files=results),indent=2)+'\n')
 rows=[]
 for r in results:
  spots=', '.join(f"{s['start']:.1f}–{s['end']:.1f}s" for s in r.get('segments',[])) or 'None'
  rows.append('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in [r['file'],r['decision'],r.get('reason',''),spots])+'</tr>')
 args.output.with_suffix('.html').write_text('<!doctype html><meta charset="utf-8"><title>Inside sound analysis</title><style>body{font:16px system-ui;max-width:1100px;margin:40px auto;padding:20px;color:#223}table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:14px;border-bottom:1px solid #ddd}h1{font-size:28px}</style><h1>Inside · Experimental sound analysis</h1><p>Local research tool. Decisions are estimates, not a guarantee of Torah content. No audio or scripts are embedded in this report.</p><table><tr><th>File</th><th>Decision</th><th>Reason</th><th>Possible music segments</th></tr>'+''.join(rows)+'</table>')
if __name__=='__main__':main()
