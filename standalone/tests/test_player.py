import pathlib,sys,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from engine import Player
from controller import LibraryController
class Audio:
 def __init__(self):self.position=0;self.status='stopped';self.duration=120
 def load(self,path):self.path=path;self.position=0;self.status='stopped'
 def play(self):self.status='playing'
 def pause(self):self.status='paused'
 def stop(self):self.status='stopped'
 def seek(self,value):self.position=value
 def speed(self,value):self.rate=value
 def volume(self,value):self.level=value
 def state(self):return {'position':self.position,'duration':self.duration,'status':self.status}
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name).resolve();self.audio=self.root/'audio';self.audio.mkdir();(self.audio/'01.wav').write_bytes(b'fake');(self.audio/'02.mp3').write_bytes(b'fake')
  self.backend=Audio();self.player=Player(self.audio,self.root/'data',self.backend);self.library=LibraryController(self.player)
 def tearDown(self):self.tmp.cleanup()
 def test_next_day_open_and_play_needs_no_connection(self):
  self.library.play();self.player.tick();self.backend.position=65.432;self.player.command({'op':'pause'})
  backend=Audio();restored=Player(None,self.root/'data',backend);view=LibraryController(restored)
  self.assertEqual(restored.root,self.audio);self.assertEqual(restored.snapshot()['position'],65.432)
  view.play();restored.tick();self.assertEqual(backend.status,'playing');self.assertEqual(backend.position,65.432)
 def test_separate_positions_for_two_recordings(self):
  ids=[t['id'] for t in self.player.tracks]
  self.library.selected=ids[0];self.library.play();self.player.tick();self.backend.position=65.432
  self.library.selected=ids[1];self.library.play(force=True);self.player.tick();self.backend.position=23.789;self.player.command({'op':'pause'})
  self.library.selected=ids[0];self.library.play();self.player.tick();self.assertEqual(self.backend.position,65.432)
  self.assertEqual(self.player.saved['tracks'][ids[1]]['position'],23.789)
 def test_each_recording_restores_speed_after_switch_and_restart(self):
  a,b=[t['id'] for t in self.player.tracks]
  self.player.load(a,autoplay=True);self.player.tick()
  self.player.command({'op':'speed','value':1.5})
  self.player.load(b,autoplay=True);self.player.tick();self.assertEqual(self.backend.rate,1)
  self.player.command({'op':'speed_cycle'});self.player.command({'op':'speed_cycle'})
  self.assertEqual(self.backend.rate,2)
  self.player.load(a,autoplay=True);self.player.tick();self.assertEqual(self.backend.rate,1.5)
  restored=Player(None,self.root/'data',Audio())
  restored.load(b,autoplay=True);restored.tick();self.assertEqual(restored.backend.rate,2)
  restored.load(a,autoplay=False);restored.tick();self.assertEqual(restored.backend.rate,1.5)
  self.assertEqual(restored.backend.status,'paused')
 def test_finished_tracks_and_near_end_are_distinguished(self):
  ids=[t['id'] for t in self.player.tracks]
  self.library.selected=ids[0];self.library.play();self.player.tick();self.backend.position=119.9;self.player.command({'op':'pause'})
  self.library.selected=ids[1];self.library.play(force=True);self.player.tick();self.backend.status='ended';self.player.tick()
  self.library.view='continue';self.assertEqual([t['id'] for t in self.library.tracks()],[ids[0]])
  self.library.selected=ids[1];self.library.reset();self.assertFalse(self.player.saved['tracks'][ids[1]]['completed'])
  self.assertEqual(self.player.saved['tracks'][ids[0]]['position'],119.9)
 def test_collections_are_user_created_and_do_not_copy_audio(self):
  self.assertEqual(self.player.saved['folders'],[]);self.library.selected=self.player.tracks[0]['id']
  self.library.collection('folder_create','My series');folder=self.library.view;self.library.add_to(folder)
  self.assertEqual(len(self.library.tracks()),1);self.library.collection('folder_rename','Renamed');self.assertEqual(self.player.saved['folders'][0]['name'],'Renamed')
  self.library.collection('folder_delete');self.assertEqual(len(list(self.audio.iterdir())),2)
 def test_bookmarks_are_local_and_survive_restart(self):
  self.library.play();self.player.tick();self.backend.position=32.456;self.library.mark('Review')
  mark=self.library.bookmarks()[0];self.assertEqual(mark['position'],32.456)
  restored=Player(None,self.root/'data',Audio());view=LibraryController(restored);self.assertEqual(view.bookmarks()[0]['name'],'Review')
  view.bookmark_action(mark['id']);restored.tick();self.assertEqual(restored.backend.position,32.456);self.assertEqual(restored.backend.status,'paused')
  view.bookmark_action(mark['id'],delete=True);self.assertEqual(view.bookmarks(),[])
 def test_reset_one_track_preserves_others(self):
  ids=[t['id'] for t in self.player.tracks];self.library.selected=ids[0];self.library.play();self.player.tick();self.backend.position=35
  self.player.saved['tracks'][ids[1]]={'position':23.789};self.library.reset()
  self.assertEqual(self.backend.status,'paused');self.assertEqual(self.backend.position,0);self.assertEqual(self.player.saved['tracks'][ids[1]]['position'],23.789)
 def test_rescan_finds_new_files_and_confines_symlinks(self):
  (self.audio/'new.mp3').write_bytes(b'fake');outside=self.root/'outside.wav';outside.write_bytes(b'fake');(self.audio/'escape.wav').symlink_to(outside)
  self.player.scan();self.assertEqual(len(self.player.tracks),3)
 def test_pause_after_auto_next_does_not_reload_the_old_selection(self):
  self.library.play();self.player.tick();first=self.player.saved['currentId'];self.library.selected=first
  self.player.saved['autoNext']=True;self.player.was_playing=True;self.backend.status='ended';self.backend.position=120
  self.player.tick();self.player.tick();current=self.player.saved['currentId'];self.assertNotEqual(first,current)
  self.library.play();self.assertEqual(self.backend.status,'paused');self.assertEqual(self.player.saved['currentId'],current)
 def test_search_does_not_block_pausing_current_recording(self):
  self.library.play();self.player.tick();self.library.query='no match';self.library.play();self.assertEqual(self.backend.status,'paused')
 def test_speed_skip_and_sleep_timer(self):
  self.player.command({'op':'language','value':'en'});self.library.play();self.player.tick()
  self.player.command({'op':'speed','value':1.5});self.assertEqual(self.backend.rate,1.5)
  for n in [10,15,60]:
   self.backend.position=10;self.player.command({'op':'skip_interval','value':n});self.player.command({'op':'skip','direction':1});self.assertEqual(self.backend.position,10+n)
  self.player.command({'op':'sleep_timer','minutes':15});self.player.sleep_deadline=0.01;self.player.tick();self.assertEqual(self.backend.status,'paused')
  restored=Player(None,self.root/'data',Audio());self.assertEqual(restored.saved['language'],'en')
 def test_skip_while_loading_uses_the_saved_position(self):
  ident=self.player.tracks[0]['id'];self.player.saved['tracks'][ident]={'position':65.432,'duration':120}
  self.player.load(ident,autoplay=True)
  self.assertEqual(self.backend.position,0)
  self.player.command({'op':'skip','direction':1})
  self.assertEqual(self.player.pending['position'],80.432)
  self.player.tick();self.assertEqual(self.backend.position,80.432)
 def test_batch_collection_validation_does_not_create_an_empty_collection(self):
  ident=self.player.tracks[0]['id']
  with self.assertRaises(ValueError):self.library.assign_many([ident,'missing'],'My series')
  with self.assertRaises(ValueError):self.library.assign_many([ident],'x'*161)
  self.assertEqual(self.player.saved['folders'],[])
 def test_mini_speed_bounces_and_survives_restart(self):
  self.library.play();self.player.tick();ident=self.player.active;self.backend.position=42.875
  rates=[]
  for _ in range(4):
   self.player.command({'op':'speed_cycle'});rates.append(self.backend.rate)
  self.assertEqual(rates,[1.5,2,.5,1]);self.assertEqual(self.backend.position,42.875)
  self.assertEqual(self.player.saved['tracks'][ident]['position'],42.875)
  self.player.command({'op':'speed_cycle'});self.player.command({'op':'speed_cycle'})
  restored=Player(None,self.root/'data',Audio());restored.command({'op':'speed_cycle'});self.assertEqual(restored.saved['speed'],.5)
  restored.saved['miniSpeedMiddle']=.5;restored.command({'op':'speed','value':1})
  rates=[restored.command({'op':'speed_cycle'})['speed'] for _ in range(4)];self.assertEqual(rates,[1.5,2,.5,1])
 def test_upgrade_corrects_existing_mini_speed_cycle(self):
  import json
  saved=dict(self.player.saved);saved.pop('halfSpeedCycleMigration',None)
  saved.update(miniSpeedMiddle=1.5,miniSpeedCycleIndex=2,speed=2)
  self.player.file.write_text(json.dumps(saved))
  restored=Player(None,self.root/'data',Audio())
  self.assertEqual(restored.command({'op':'speed_cycle'})['speed'],.5)
  self.assertEqual(restored.command({'op':'speed_cycle'})['speed'],1)
if __name__=='__main__':unittest.main(verbosity=2)
