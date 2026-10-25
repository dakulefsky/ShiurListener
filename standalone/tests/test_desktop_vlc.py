"""Actual Tk controls connected to real libVLC, using a dummy audio sink.
Run separately under a desktop display; this does not test Windows mouse routing.
"""
import contextlib,os,pathlib,sys,tempfile,time,unittest.mock,wave
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'app'))
from engine import Player,VLC
from controller import LibraryController
from window import PlayerWindow


def run():
 with tempfile.TemporaryDirectory() as directory:
  root=pathlib.Path(directory);audio=root/'audio';audio.mkdir()
  for name in ('01.wav','02.wav'):
   with wave.open(str(audio/name),'wb') as stream:
    stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(16000);stream.writeframes(b'\x10\x00'*16000*30)
  lib=os.environ.get('SHIUR_TEST_VLC_LIBRARY')
  with unittest.mock.patch('ctypes.util.find_library',return_value=lib) if lib else contextlib.nullcontext():backend=VLC(options=['--aout=dummy','--quiet'])
  window=None
  try:
   player=Player(audio,root/'data',backend);library=LibraryController(player)
   window=PlayerWindow(player,library,lambda _:None);window.root.update()
   def wait(predicate,label):
    deadline=time.monotonic()+8
    while time.monotonic()<deadline:
     window.root.update();player.tick()
     if predicate(player.snapshot()):return
     time.sleep(.03)
    raise AssertionError(label+': '+str(player.snapshot()))
   window.play_button.invoke();wait(lambda s:s['status']=='playing' and s['position']>.1,'Play from actual UI')
   first=player.active;second=next(ident for ident in player.paths if ident!=first)
   window.speed_button.invoke();assert player.saved['speed']==1.5
   window.toggle_dock();window.root.update();assert window.compact_play.winfo_ismapped()
   window.compact_play.invoke();wait(lambda s:s['status']=='paused','Compact pause')
   window.compact_play.invoke();wait(lambda s:s['status']=='playing','Compact resume')
   window.tree.selection_set(second);window.select();window.resume()
   wait(lambda s:s['status']=='playing' and s['currentId']==second,'Select another recording')
   assert player.saved['speed']==1
   window.compact_speed.invoke();window.compact_speed.invoke();assert player.saved['speed']==2
   window.tree.selection_set(first);window.select();window.resume()
   wait(lambda s:s['status']=='playing' and s['currentId']==first,'Restore first recording')
   assert player.saved['speed']==1.5
   window.toggle_dock();window.root.update()
   window.seek.set(8);window.seek_release(None)
   wait(lambda s:7.5<=s['position']<=9,'Seek from actual UI')
   window.play_button.invoke();wait(lambda s:s['status']=='paused','Pause before closing')
   position=player.snapshot()['position'];window.close();window=None
   player=Player(None,root/'data',backend);library=LibraryController(player)
   window=PlayerWindow(player,library,lambda _:None);window.root.update()
   assert abs(player.snapshot()['position']-position)<.3
   window.play_button.invoke()
   wait(lambda s:s['status']=='playing' and abs(s['position']-position)<1,'Resume from reopened UI')
   assert player.saved['speed']==1.5
   player.command({'op':'sleep_timer','minutes':.01})
   wait(lambda s:s['status']=='paused' and s['sleepRemaining']==0,'Sleep timer in desktop UI')
  finally:
   if window and not window.closed:window.close()
   backend.close()
 print('PASS: actual Tk play/pause, compact dock, per-recording speed, selection, seek, close/reopen and sleep timer with real VLC (dummy audio output).')

if __name__=='__main__':run()
