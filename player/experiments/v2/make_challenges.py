"""Reproduce new constructed combinations (not independent source recordings)."""
import argparse,pathlib,subprocess,wave
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--assets',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
def read(path):return np.frombuffer(subprocess.check_output(['ffmpeg','-nostdin','-v','error','-i',str(path),'-f','f32le','-ac','1','-ar','16000','-t','30','pipe:1']),dtype='<f4').copy()
def save(name,a):
 with wave.open(str(args.output/(name+'.wav')),'wb') as f:
  f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes((np.clip(a,-1,1)*32767).astype('<i2').tobytes())
s=read(args.assets/'data/speech_wav/geography1.wav');s=s/(np.sqrt(np.mean(s*s))+1e-8)*.1
for name in ['opera','rock','jazz']:
 m=read(args.assets/f'data/music_wav/{name}.wav');n=min(len(m),len(s));m=m[:n]/(np.sqrt(np.mean(m*m))+1e-8)*.1
 save(name+'_under_speech_minus20dB',s[:n]+m*.1)
 for seconds in [2,5]:save(f'{name}_insert_{seconds}sec',np.concatenate([s[:16000*15],m[:16000*seconds],s[16000*15:]]))
save('speech_only_geography',s)
