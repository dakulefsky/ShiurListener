"""Fixed-policy file evaluation. Repeated short clips are not new independent recordings."""
import argparse,json,pathlib,subprocess,tempfile,time
import numpy as np
from ai_edge_litert.interpreter import Interpreter
from scan import scan,sha,MODEL_SHA
p=argparse.ArgumentParser();p.add_argument('--assets',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);args=p.parse_args()
model_file=args.assets/'yamnet.tflite'
if sha(model_file)!=MODEL_SHA:raise ValueError('Model checksum mismatch')
model=Interpreter(model_path=str(model_file),num_threads=2);model.allocate_tensors();model.set_tensor(0,np.zeros(15600,np.float32));model.invoke()
items=[(f,f.parent.name.replace('_wav','')) for f in sorted((args.assets/'data').rglob('*.wav'))]+[(args.assets/'shiur_freifeld.mp3','shiur')]+[(f,'constructed_music' if 'music' in f.stem else 'non_speech') for f in sorted((args.assets/'stress').glob('*.wav'))]
results=[];begin=time.perf_counter()
with tempfile.TemporaryDirectory(prefix='inside-two-check-files-') as tmp:
 for n,(source,label) in enumerate(items):
  try:
   duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(source)],timeout=10))
   repeated=duration<300;target=source
   if repeated:
    target=pathlib.Path(tmp)/'five-minute-fixture.wav'
    subprocess.run(['ffmpeg','-nostdin','-v','error','-stream_loop','-1','-i',str(source),'-t','300','-ac','1','-ar','16000','-c:a','pcm_s16le','-y',str(target)],timeout=30,check=True)
   result=scan(target,model);result.update(source=source.name,source_sha256=sha(source),label=label,repeated_to_five_minutes=repeated)
  except Exception as e:result=dict(source=source.name,label=label,decision='error',reason=str(e),full_file_approved=False)
  results.append(result)
  if (n+1)%10==0 or n+1==len(items):print(f'Tested {n+1}/{len(items)} files',flush=True)
summary={label:{decision:sum(r['label']==label and r['decision']==decision for r in results) for decision in sorted({r['decision'] for r in results})} for label in sorted({r['label'] for r in results})}
output=dict(policy='two-interior-checks-v1',rules_changed_during_test=False,model_sha256=MODEL_SHA,wall_seconds=time.perf_counter()-begin,summary=summary,files=results)
args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(output,indent=2)+'\n');print(json.dumps(summary,indent=2))
