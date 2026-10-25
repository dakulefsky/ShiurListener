"""Exercise the real desktop toolkit, including persistence across a new window."""
import os,pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'app'))
from window import PlayerWindow
from engine import Player
from controller import LibraryController
import test_player
@unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform=='win32','Needs a desktop display')
class Tests(unittest.TestCase):
 def test_multiple_resume_rows_and_reopen(self):
  fixture=test_player.Tests();fixture.setUp();window=None
  try:
   (fixture.audio/'03.wav').write_bytes(b'fake');fixture.player.scan();ids=[t['id'] for t in fixture.player.tracks]
   for ident,position in zip(ids,[65.432,23.789,119.9]):
    fixture.library.selected=ident;fixture.library.play(force=True);fixture.player.tick();fixture.backend.position=position;fixture.player.command({'op':'pause'})
   window=PlayerWindow(fixture.player,fixture.library,lambda _:None);window.root.update()
   self.assertEqual([window.tree.item(i,'values')[1] for i in ids],['1:05','0:23','1:59'])
   window.navigate('continue');window.root.update();self.assertEqual(list(window.tree.get_children()),ids[::-1])
   window.tree.selection_set(ids[0]);window.root.update();window.resume();fixture.player.tick();self.assertEqual(fixture.backend.position,65.432)
   window.query.set('03');window.root.update();self.assertEqual(list(window.tree.get_children()),[ids[2]])
   window.toggle();self.assertEqual(fixture.backend.status,'paused');window.close();window=None
   backend=test_player.Audio();player=Player(None,fixture.root/'data',backend);library=LibraryController(player);window=PlayerWindow(player,library,lambda _:None);window.root.update()
   for ident,position in zip(ids,[65.432,23.789,119.9]):
    window.tree.selection_set(ident);window.root.update();window.resume();player.tick();self.assertEqual(backend.position,position)
  finally:
   if window:window.close()
   fixture.tearDown()
if __name__=='__main__':unittest.main(verbosity=2)
