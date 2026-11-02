import sys,pathlib,json,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'app'))
import test_player
from engine import Player
from controller import LibraryController
class RenameTests(unittest.TestCase):
 setUp=test_player.Tests.setUp
 tearDown=test_player.Tests.tearDown
 def test_rename_keeps_progress_bookmarks_queue_and_collections_after_reopen(self):
  self.library.play();self.player.tick();self.backend.position=42.875
  old=self.player.active;source=self.player.paths[old];self.library.mark('Review');self.library.assign_many([old],'My series')
  moved=next(track['id'] for track in self.player.tracks if track['name']==source.name)
  new=self.library.rename(moved,'My renamed shiur')
  self.assertFalse(source.exists());self.assertEqual(self.player.paths[new].name,'My renamed shiur.wav')
  self.player.tick();self.assertEqual(self.backend.position,42.875);self.assertEqual(self.backend.status,'playing')
  self.assertIn(new,self.player.saved['queue']);self.assertNotIn(old,self.player.saved['queue'])
  self.assertEqual(self.player.saved['folders'][0]['trackIds'],[new]);self.assertEqual(self.player.saved['bookmarks'][new][0]['position'],42.875)
  restored=Player(None,self.root/'data',test_player.Audio());self.assertEqual(restored.snapshot()['position'],42.875)
  self.assertIn(new,restored.paths);self.assertNotIn(old,restored.paths)
 def test_startup_recovers_progress_after_interrupted_filesystem_rename(self):
  import hashlib
  ident=self.player.tracks[0]['id'];source=self.player.paths[ident]
  self.player.saved['tracks'][ident]={'position':73.5,'duration':300,'completed':False,'lastListenedAt':123456,'favorite':True}
  self.player.saved['bookmarks'][ident]=[{'id':'bookmark1','position':73.5,'name':'Review'}]
  self.player.saved['queue']=[ident]
  self.player.saved['currentId']=ident
  self.player.saved['folders']=[{'id':'series1','name':'Series','trackIds':[ident]}]
  self.player.persist()
  target=source.with_name('Recovered name'+source.suffix)
  library_root=self.player.root.resolve()
  relative_source=source.relative_to(library_root).as_posix()
  relative_target=target.relative_to(library_root).as_posix()
  new_id=hashlib.sha256((str(library_root)+'/'+relative_target).encode()).hexdigest()[:24]
  journal=self.root/'data'/'rename-recovery.json'
  journal.write_text(json.dumps({'root':str(library_root),'source':relative_source,'target':relative_target,'old_id':ident,'new_id':new_id}),encoding='utf-8')
  source.rename(target)  # Simulate power loss immediately after the filesystem rename.
  restored=Player(None,self.root/'data',test_player.Audio())
  self.assertIn(new_id,restored.paths);self.assertNotIn(ident,restored.paths)
  self.assertEqual(restored.saved['tracks'][new_id]['position'],73.5)
  self.assertTrue(restored.saved['tracks'][new_id]['favorite'])
  self.assertEqual(restored.saved['bookmarks'][new_id][0]['name'],'Review')
  self.assertEqual(restored.saved['queue'],[new_id])
  self.assertEqual(restored.saved['currentId'],new_id)
  self.assertEqual(restored.saved['folders'][0]['trackIds'],[new_id])
  self.assertFalse(journal.exists())
 def test_rename_rejects_existing_names_and_path_traversal_without_changes(self):
  ident=self.player.tracks[0]['id'];original=self.player.paths[ident];original_bytes=original.read_bytes()
  (self.audio/'existing.wav').write_bytes(b'other')
  for name in ['../escape','existing','CON','bad/name','bad:name']:
   with self.assertRaises(ValueError):self.library.rename(ident,name)
  self.assertEqual(original.read_bytes(),original_bytes);self.assertEqual((self.audio/'existing.wav').read_bytes(),b'other')
 def test_rename_paused_recording_stays_paused_and_preserves_extension(self):
  self.library.play();self.player.tick();self.backend.position=19.25;self.player.command({'op':'pause'})
  new=self.library.rename(self.player.active,'A title.wav');self.player.tick()
  self.assertEqual(self.player.paths[new].name,'A title.wav');self.assertEqual(self.backend.status,'paused');self.assertEqual(self.backend.position,19.25)
if __name__=='__main__':unittest.main()
