"""Deterministic constructed challenges; these are not independent test recordings."""
import argparse,pathlib,subprocess,wave
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--assets',type=pathlib.Path,required=True);args=p.parse_args();root=args.assets;out=root/'stress';out.mkdir(exist_ok=True)
def audio(path,seconds):return np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-f','f32le','-ac','1','-ar','16000','-t',str(seconds),'pipe:1']),dtype='<f4').copy()
def save(name,a):
 with wave.open(str(out/(name+'.wav')),'wb') as f:
  f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes((np.clip(a,-1,1)*32767).astype('<i2').tobytes())
s=audio(root/'shiur_freifeld.mp3',30);m=audio(root/'data/music_wav/brahms.wav',30);length=min(len(s),len(m));s=s[:length];m=m[:length]
s=s/(np.sqrt(np.mean(s*s))+1e-8)*.1;m=m/(np.sqrt(np.mean(m*m))+1e-8)*.1
for db in [-20,-10,0]:save(f'shiur_plus_music_{db}dB',s+m*10**(db/20))
save('spoken_intro_then_music',np.concatenate([s,m]));save('silence',np.zeros(16000*15));save('white_noise',np.random.default_rng(42).normal(0,.05,16000*15))
save('six_minutes_speech_then_15sec_music',np.concatenate([audio(root/'shiur_freifeld.mp3',360),m[:16000*15]]))
