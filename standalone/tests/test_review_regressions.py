"""User-facing failure cases found during the standalone source audit."""
import copy
import json
import pathlib
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'app'))
import test_player
from engine import Player

class ReviewTests(unittest.TestCase):
 setUp=test_player.Tests.setUp
 tearDown=test_player.Tests.tearDown

 def test_changing_volume_during_load_does_not_unmute_before_resume_seek(self):
  ident=self.player.tracks[0]['id']
  self.player.saved['tracks'][ident]={'position':65.432,'duration':120}
  self.player.load(ident,autoplay=True)
  self.assertEqual(self.backend.level,0)
  self.player.command({'op':'volume','value':.6})
  self.assertEqual(self.backend.level,0)
  self.player.tick()
  self.assertEqual(self.backend.position,65.432)
  self.assertEqual(self.backend.level,.6)

 def test_speed_can_be_set_before_a_recording_is_loaded(self):
  ident=self.player.tracks[0]['id'];self.player.saved['currentId']=ident
  with patch.object(self.backend,'speed',side_effect=RuntimeError('No media loaded')):
   self.player.command({'op':'speed','value':1.5})
  self.player.command({'op':'play'});self.player.tick()
  self.assertEqual(self.backend.rate,1.5)

 def test_reset_after_pending_async_seek_does_not_restore_old_place(self):
  self.library.play();self.player.tick();self.backend.position=10
  self.backend.seek=lambda value:None
  self.player.command({'op':'seek','value':65.432})
  self.library.reset()
  self.assertEqual(self.player.snapshot()['position'],0)
  self.player.command({'op':'pause'})
  self.assertEqual(json.loads(self.player.file.read_text())['tracks'][self.player.active]['position'],0)

 def test_reset_finished_recording_stays_reset_on_next_tick(self):
  self.library.play();self.player.tick();ident=self.player.active
  self.backend.status='ended';self.backend.position=120;self.player.tick()
  self.library.reset();self.player.tick()
  self.assertEqual(self.player.snapshot()['position'],0)
  self.assertFalse(self.player.saved['tracks'][ident]['completed'])
  self.assertEqual(self.backend.status,'paused')

 def test_failed_load_can_retry_without_losing_saved_position(self):
  ident=self.player.tracks[0]['id']
  self.player.saved['tracks'][ident]={'position':65.432,'duration':120}
  with patch.object(self.backend,'play',side_effect=RuntimeError('Decoder unavailable')):
   with self.assertRaises(RuntimeError):self.player.load(ident,autoplay=True)
  self.assertIsNone(self.player.pending)
  self.assertIsNone(self.player.active)
  self.assertEqual(self.player.snapshot()['position'],65.432)
  self.player.command({'op':'play'});self.player.tick()
  self.assertEqual(self.backend.position,65.432)
  self.assertEqual(self.backend.status,'playing')

 def test_decoder_timeout_preserves_resume_display_and_retries(self):
  ident=self.player.tracks[0]['id']
  self.player.saved['tracks'][ident]={'position':65.432,'duration':120}
  self.player.load(ident,autoplay=True);self.backend.status='loading'
  self.player.pending['started']-=21;self.player.tick()
  self.assertIsNone(self.player.active)
  self.assertEqual(self.player.snapshot()['position'],65.432)
  self.player.command({'op':'play'});self.player.tick()
  self.assertEqual(self.backend.position,65.432)

 def test_error_state_play_reloads_and_restores_position(self):
  self.library.play();self.player.tick();self.backend.position=42
  self.player.command({'op':'pause'});self.backend.status='error';self.backend.position=0
  with patch.object(self.backend,'load',wraps=self.backend.load) as load:
   self.player.command({'op':'play'});self.player.tick();load.assert_called_once()
  self.assertEqual(self.backend.position,42)

 def test_missing_library_can_be_reconnected_by_refresh(self):
  self.library.play();self.player.tick();self.backend.position=42;self.player.command({'op':'pause'})
  moved=self.audio.with_name('disconnected');self.audio.rename(moved)
  restored=Player(None,self.root/'data',test_player.Audio())
  self.assertEqual(restored.root,self.audio)
  moved.rename(self.audio);restored.scan()
  self.assertEqual(len(restored.tracks),2)
  self.assertEqual(next(t['position'] for t in restored.library() if t['id']==self.player.active),42)

 def test_invalid_saved_profile_is_backed_up_before_recovery(self):
  for index,change in enumerate([{'speed':'fast'},{'tracks':[]},{'queue':{}},{'volume':float('nan')}]):
   state={**self.player.saved,**change};self.player.file.write_text(json.dumps(state));before=self.player.file.read_bytes()
   Player(None,self.root/'data',test_player.Audio())
   self.assertEqual(self.player.file.read_bytes(),before)
   backups=list((self.root/'data').glob('state.json.recovery-*.bak'))
   self.assertTrue(backups, 'invalid state must be backed up before recovery')

 def test_failed_load_does_not_replace_queue(self):
  original=list(self.player.saved['queue'])
  with self.assertRaises(ValueError):self.player.command({'op':'load','id':'missing','queue':[self.player.tracks[0]['id']]})
  self.assertEqual(self.player.saved['queue'],original)

 def test_bookmark_window_actions_stay_bound_to_original_recording(self):
  self.library.play();self.player.tick();original=self.player.active
  self.backend.position=32;self.library.mark('Review');mark=self.library.bookmarks()[0]
  other=next(t['id'] for t in self.player.tracks if t['id']!=original)
  self.player.load(other,autoplay=True);self.player.tick()
  self.library.bookmark_action(mark['id'],track_id=original);self.player.tick()
  self.assertEqual(self.player.active,original);self.assertEqual(self.backend.position,32)
  self.player.load(other,autoplay=True);self.player.tick()
  self.library.bookmark_action(mark['id'],delete=True,track_id=original)
  self.assertEqual(self.player.active,other);self.assertEqual(self.player.saved['bookmarks'][original],[])

 def test_decoder_resume_failure_does_not_leave_muted_playback_stuck(self):
  ident=self.player.tracks[0]['id']
  self.player.saved['tracks'][ident]={'position':42,'duration':120}
  self.player.load(ident,autoplay=True)
  with patch.object(self.backend,'speed',side_effect=RuntimeError('Decoder still unavailable')):self.player.tick()
  self.assertIsNone(self.player.active);self.assertIsNone(self.player.pending)
  self.assertEqual(self.player.snapshot()['position'],42)
  self.player.command({'op':'play'});self.player.tick()
  self.assertEqual(self.backend.status,'playing');self.assertEqual(self.backend.level,1)

 def test_rename_failure_restores_playing_state_and_position(self):
  self.library.play();self.player.tick();ident=self.player.active;self.backend.position=42
  with patch.object(pathlib.Path,'rename',side_effect=OSError('File is locked')):
   with self.assertRaises(OSError):self.library.rename(ident,'Renamed')
  self.player.tick();self.assertEqual(self.backend.status,'playing');self.assertEqual(self.backend.position,42)

 def test_load_and_background_checkpoint_do_not_overlap(self):
  import threading
  self.library.play();self.player.tick();self.backend.position=42;self.player.command({'op':'pause'})
  original=self.player.active;other=next(t['id'] for t in self.player.tracks if t['id']!=original)
  started=threading.Event();release=threading.Event();tick_started=threading.Event();tick_done=threading.Event();errors=[]
  original_load=self.backend.load
  def slow_load(path):
   original_load(path);started.set()
   if not release.wait(2):raise RuntimeError('Test release timed out')
  def load():
   try:self.player.load(other,autoplay=False)
   except Exception as error:errors.append(error)
  def tick():tick_started.set();self.player.tick();tick_done.set()
  with patch.object(self.backend,'load',side_effect=slow_load):
   loader=threading.Thread(target=load);loader.start()
   try:
    self.assertTrue(started.wait(1));worker=threading.Thread(target=tick);worker.start()
    self.assertTrue(tick_started.wait(1));self.assertFalse(tick_done.wait(.05))
   finally:release.set();loader.join(2)
   worker.join(2)
  self.assertEqual(errors,[]);self.assertTrue(tick_done.is_set())
  self.assertEqual(self.player.saved['tracks'][original]['position'],42)
  self.assertIsInstance(json.loads(self.player.file.read_text())['tracks'],dict)

 def test_renaming_internal_symlink_does_not_rename_its_target(self):
  original=self.audio/'01.wav';alias=self.audio/'Alias.wav'
  try:alias.symlink_to(original)
  except OSError:self.skipTest('Symlinks unavailable')
  self.player.scan();ident=next(t['id'] for t in self.player.tracks if t['name']=='Alias.wav')
  new=self.library.rename(ident,'Renamed alias')
  self.assertTrue(original.is_file());self.assertTrue(self.player.paths[new].is_symlink())
  self.assertFalse(alias.exists());self.assertEqual(original.read_bytes(),b'fake')

 def test_duplicate_collection_names_are_rejected_without_mutating_collections(self):
  self.player.command({'op':'folder_create','name':'Weekly shiurim'})
  with self.assertRaises(ValueError):self.player.command({'op':'folder_create','name':'WEEKLY SHIURIM'})
  self.player.command({'op':'folder_create','name':'Another series'})
  second=self.player.saved['folders'][1]['id'];before=copy.deepcopy(self.player.saved['folders'])
  with self.assertRaises(ValueError):self.player.command({'op':'folder_rename','id':second,'name':'Weekly shiurim'})
  self.assertEqual(self.player.saved['folders'],before)
