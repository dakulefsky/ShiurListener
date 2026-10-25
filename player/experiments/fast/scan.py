"""Offline fast triage: distributed samples, NOT complete-file approval.
Developer prototype; no plugin edits, installs or runtime model downloads.
"""
import argparse,concurrent.futures,csv,hashlib,json,pathlib,random,subprocess,time
import numpy as np
from ai_edge_litert.interpreter import Interpreter
MODEL_SHA='e193da5676a2fdb7a3702c10fba62aa27d76f64e4534467443811c1a2ff1667d'
def sha(file,deadline=None):
 h=hashlib.sha256()
 with file.open('rb') as stream:
  for chunk in iter(lambda:stream.read(1024*1024),b''):
   if deadline and time.perf_counter()>deadline:raise TimeoutError('Fast-scan time budget exceeded')
   h.update(chunk)
 return h.hexdigest()
def schedule(seconds,identity):
 if not np.isfinite(seconds) or seconds<300:raise ValueError('Recording must have a finite duration of at least five minutes')
 rng=random.Random(identity);end=seconds-.975
 # Two interior regions avoid relying on introductions or closing silence.
 return [round(end*(.2+.15*rng.random()),3),round(end*(.65+.15*rng.random()),3)]
def decode(file,start,deadline):
 command=['ffmpeg','-nostdin','-v','error','-threads','1','-protocol_whitelist','file,pipe','-ss',str(start),'-i',str(file),'-t','0.975','-vn','-ac','1','-ar','16000','-f','f32le','pipe:1']
 remaining=deadline-time.perf_counter()
 if remaining<=0:raise TimeoutError('Fast-scan time budget exceeded')
 raw=subprocess.run(command,capture_output=True,timeout=remaining,check=True).stdout
 if len(raw)%4 or len(raw)<4:raise ValueError('Sample could not be decoded')
 a=np.frombuffer(raw,dtype='<f4')[:15600]
 if not np.isfinite(a).all():raise ValueError('Invalid decoded samples')
 return np.pad(a,(0,15600-len(a)))
def decide_checks(rows):
 if len(rows)!=2:raise ValueError('Exactly two checks are required')
 for row in rows:
  if any(not isinstance(row.get(k),(int,float)) or not np.isfinite(row[k]) or not 0<=row[k]<=1 for k in ['speech','music','singing']):raise ValueError('Invalid classifier scores')
 hits=sum(max(row['music'],row['singing'])>=.5 for row in rows)
 if hits==2:return 'music_detected_in_samples','Both samples indicate music or singing'
 if max(row['speech'] for row in rows)>=.8:return 'provisional_speech','At least one sample strongly indicates speech'
 if hits==0 and all(row['speech']>=.5 for row in rows):return 'provisional_speech','Both samples indicate speech'
 return 'uncertain','No sufficiently clear speech evidence'
def scan(file,model,budget=5):
 if budget<=0:raise TimeoutError('Fast-scan time budget exceeded')
 start=time.perf_counter();deadline=start+budget;file=file.resolve();before=file.stat()
 if not file.is_file() or before.st_size>2*1024**3:raise ValueError('Choose a local audio file no larger than 2 GiB')
 info=json.loads(subprocess.check_output(['ffprobe','-v','error','-protocol_whitelist','file,pipe','-show_entries','format=duration:stream=codec_type','-of','json',str(file)],timeout=max(.05,deadline-time.perf_counter())))
 if not info.get('streams') or any(s.get('codec_type')!='audio' for s in info['streams']):raise ValueError('Only audio streams are supported')
 seconds=float(info['format']['duration'])
 if seconds>8*3600:raise ValueError('Development duration limit is eight hours')
 digest=sha(file,deadline);times=schedule(seconds,digest);prepared=time.perf_counter();rows=[]
 def classify(at,a):
  if time.perf_counter()>deadline:raise TimeoutError('Fast-scan time budget exceeded')
  model.set_tensor(0,a);model.invoke();scores=model.get_tensor(model.get_output_details()[0]['index'])[0]
  return dict(start=at,seconds=.975,speech=float(scores[0]),music=float(scores[132]),singing=float(scores[24]))
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  for at,a in zip(times,pool.map(lambda t:decode(file,t,deadline),times)):rows.append(classify(at,a))
 first=time.perf_counter()
 after=file.stat()
 if after.st_size!=before.st_size or after.st_mtime_ns!=before.st_mtime_ns:raise ValueError('Input changed during analysis')
 rows.sort(key=lambda r:r['start']);decision,reason=decide_checks(rows)
 elapsed=time.perf_counter()-start
 if elapsed>budget:raise TimeoutError('Fast-scan time budget exceeded')
 covered=0.;last_end=0.
 for row in rows:
  end=min(seconds,row['start']+row['seconds']);covered+=max(0,end-max(last_end,row['start']));last_end=max(last_end,end)
 return dict(file=file.name,sha256=digest,encoded_bytes=before.st_size,recording_seconds=seconds,policy='two-interior-checks-v2-speech-priority',scope='sampled_only',decision=decision,reason=reason,full_file_approved=False,sampled_windows=len(rows),sampled_seconds=covered,coverage_fraction=covered/seconds,wall_seconds=elapsed,metadata_and_hash_seconds=prepared-start,first_pass_seconds=first-prepared,target_seconds=budget,target_met=elapsed<=budget,windows=rows)
def main():
 p=argparse.ArgumentParser();p.add_argument('--model',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('files',type=pathlib.Path,nargs='+');args=p.parse_args();begin=time.perf_counter()
 if sha(args.model)!=MODEL_SHA:raise ValueError('Unexpected model checksum')
 model=Interpreter(model_path=str(args.model),num_threads=2);model.allocate_tensors();model.set_tensor(0,np.zeros(15600,np.float32));model.invoke();initialization=time.perf_counter()-begin
 results=[]
 for file in args.files:
  try:result=scan(file,model)
  except Exception as e:result=dict(file=file.name,decision='incomplete' if isinstance(e,(TimeoutError,subprocess.TimeoutExpired)) else 'error',reason=str(e),full_file_approved=False)
  results.append(result);print(json.dumps({k:v for k,v in result.items() if k!='windows'}),flush=True)
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(dict(experimental=True,initialization_seconds=initialization,model_sha256=MODEL_SHA,files=results),indent=2)+'\n')
if __name__=='__main__':main()
