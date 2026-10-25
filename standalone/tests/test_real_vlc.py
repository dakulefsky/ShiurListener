"""Real libVLC decoder tests. Uses a dummy audio sink: no physical speakers are tested.
Set SHIUR_TEST_VLC_LIBRARY if testing a VLC library extracted outside the system search path.
"""
import importlib.util,os,pathlib,subprocess,tempfile,time,wave,unittest.mock,json
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('companion',ROOT/'app/engine.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
def wait(player,predicate,description,seconds=8):
 deadline=time.monotonic()+seconds
 while time.monotonic()<deadline:
  player.tick();state=player.snapshot()
  if predicate(state):return state
  time.sleep(.05)
 raise AssertionError(description+': '+json.dumps(state))
def run():
 with tempfile.TemporaryDirectory() as directory:
  root=pathlib.Path(directory);audio=root/'audio';audio.mkdir()
  wav=audio/'01-test.wav'
  with wave.open(str(wav),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(b'\x10\x00'*16000*30)
  subprocess.run(['ffmpeg','-loglevel','error','-y','-i',str(wav),str(audio/'02-test.mp3')],check=True)
  lib=os.environ.get('SHIUR_TEST_VLC_LIBRARY')
  with unittest.mock.patch('ctypes.util.find_library',return_value=lib) if lib else __import__('contextlib').nullcontext():backend=module.VLC(options=['--aout=dummy','--quiet'])
  player=module.Player(audio,root/'data',backend);ids=[t['id'] for t in player.tracks]
  try:
   player.command({'op':'load','id':ids[0],'queue':ids,'position':5})
   wait(player,lambda s:s['status']=='paused' and s['position']>=4.5,'paused load at saved position')
   player.command({'op':'play'});wait(player,lambda s:s['status']=='playing' and s['position']>5.3,'real WAV playback')
   player.command({'op':'speed','value':1.5});player.command({'op':'volume','value':.4})
   player.command({'op':'seek','value':12});wait(player,lambda s:s['position']>=11.5,'real seek')
   player.command({'op':'pause'});paused=wait(player,lambda s:s['status']=='paused','real pause')['position'];time.sleep(.3);assert abs(player.snapshot()['position']-paused)<.15
   player.persist();restored=module.Player(audio,root/'data',backend);assert abs(restored.snapshot()['position']-paused)<.2
   # No UI/client connected: native engine and service tick own background continuation.
   player.command({'op':'autonext','value':True});player.command({'op':'play'});wait(player,lambda s:s['status']=='playing','resume')
   player.command({'op':'seek','value':29})
   wait(player,lambda s:s['currentId']==ids[1] and s['status']=='playing' and s['position']>.3,'background advance to real MP3',seconds=10)
   player.command({'op':'sleep_timer','minutes':15});player.sleep_deadline=time.monotonic()-1
   wait(player,lambda s:s['status']=='paused' and s['sleepRemaining']==0,'real sleep-timer pause')
   player.command({'op':'stop'});assert player.snapshot()['status']=='paused'
  finally:backend.close()
 print('PASS: real libVLC WAV/MP3 decoding, seek, speed/volume commands, pause/resume, saved progress and automatic queue advancement without a UI (dummy audio output).')
if __name__=='__main__':run()
