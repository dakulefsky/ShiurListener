"""Library and queue operations must preserve independent playback progress."""
import copy,json,pathlib,sys,tempfile,unittest

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'app'))
from controller import LibraryController
from engine import Player
from test_player import Audio


class LibraryToolsTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.temp.name)
  self.audio=self.root/'audio';self.audio.mkdir()
  for name in ('Shiur 10.mp3','Shiur 1.mp3','Shiur 2.mp3','Other.wav'):(self.audio/name).write_bytes(b'fake')
  self.backend=Audio();self.player=Player(self.audio,self.root/'data',self.backend);self.library=LibraryController(self.player)
  self.ids={track['name']:track['id'] for track in self.player.tracks}
 def tearDown(self):self.temp.cleanup()
 def test_natural_order_multiword_search_and_filtering(self):
  self.library.query='shiur';self.assertEqual([t['name'] for t in self.library.tracks()],['Shiur 1.mp3','Shiur 2.mp3','Shiur 10.mp3'])
  self.library.query=' 2  SHIUR ';self.assertEqual([t['name'] for t in self.library.tracks()],['Shiur 2.mp3'])
  one,two,ten=[self.ids[f'Shiur {n}.mp3'] for n in (1,2,10)]
  self.player.saved['tracks'][one]={'position':23.789,'duration':120,'lastListenedAt':10}
  self.player.saved['tracks'][two]={'position':120,'duration':120,'completed':True}
  self.library.query='shiur';self.library.view='unplayed';self.assertEqual([t['id'] for t in self.library.tracks()],[ten])
  self.library.view='finished';self.assertEqual([t['id'] for t in self.library.tracks()],[two])
  self.library.view='continue';self.assertEqual([t['id'] for t in self.library.tracks()],[one])
 def test_favorites_survive_reopen_without_changing_positions(self):
  one,two=[self.ids[f'Shiur {n}.mp3'] for n in (1,2)]
  self.player.saved['tracks'][one]={'position':65.432,'duration':120,'completed':False}
  self.player.saved['tracks'][two]={'position':23.789,'duration':120,'completed':False}
  self.library.favorite([one,two],True);self.library.favorite([two])
  restored=Player(None,self.root/'data',Audio());view=LibraryController(restored);view.view='favorites'
  self.assertEqual([t['id'] for t in view.tracks()],[one])
  self.assertEqual(restored.saved['tracks'][one]['position'],65.432)
  self.assertEqual(restored.saved['tracks'][two]['position'],23.789)
  self.assertFalse(restored.saved['tracks'][two]['favorite'])
 def test_queue_play_next_moves_existing_items_after_current_without_restarting(self):
  one,two,ten=[self.ids[f'Shiur {n}.mp3'] for n in (1,2,10)];other=self.ids['Other.wav']
  self.player.command({'op':'load','id':one,'queue':[other,one,two,ten]});self.player.command({'op':'play'});self.player.tick()
  self.backend.position=65.432;self.player.capture();before=copy.deepcopy(self.player.saved['tracks'])
  result=self.library.queue_add([ten,other,ten,one],next_up=True)
  self.assertEqual(result,[one,ten,other,two]);self.assertEqual(self.player.active,one)
  self.assertEqual(self.backend.position,65.432);self.assertEqual(self.backend.status,'playing')
  self.assertEqual(self.player.saved['tracks'],before)
  self.library.queue_move(other,-1);self.assertEqual(self.player.saved['queue'],[one,other,ten,two])
  self.library.queue_remove([one,other]);self.assertEqual(self.player.saved['queue'],[one,ten,two])
  self.assertEqual(self.player.saved['currentId'],one);self.assertEqual(self.player.saved['tracks'],before)
  restored=Player(None,self.root/'data',Audio());self.assertEqual(restored.saved['queue'],[one,ten,two])
  self.assertEqual(restored.snapshot()['position'],65.432)
 def test_queue_deduplicates_and_keeps_current_as_anchor(self):
  one,two,ten=[self.ids[f'Shiur {n}.mp3'] for n in (1,2,10)]
  self.player.saved['currentId']=one;self.player.saved['queue']=[two,two,'missing']
  self.assertEqual(self.library.queue_add([ten,ten,two]),[one,two,ten])
  with self.assertRaises(ValueError):self.library.queue_remove([one])
  self.assertEqual(self.library.queue_move(one,-1),[one,two,ten])
  self.assertEqual(self.library.queue_move(ten,1),[one,two,ten])
 def test_invalid_selection_does_not_partially_mutate_library(self):
  ident=self.ids['Other.wav'];before=copy.deepcopy(self.player.saved)
  for action in (lambda:self.library.favorite([ident,'missing'],True),lambda:self.library.queue_add([ident,'missing']),lambda:self.library.queue_remove([ident,'missing']),lambda:self.library.queue_move(ident,2)):
   with self.assertRaises(ValueError):action()
   self.assertEqual(self.player.saved,before)
 def test_bookmarks_are_listed_chronologically_without_rewriting_positions(self):
  ident=self.ids['Other.wav'];self.player.saved['currentId']=ident
  self.player.saved['bookmarks'][ident]=[{'id':'late','position':90.5,'name':'Later'},{'id':'early','position':12.345,'name':'Earlier'}]
  self.assertEqual([m['id'] for m in self.library.bookmarks()],['early','late'])
  self.assertEqual(self.player.saved['bookmarks'][ident][0]['position'],90.5)


if __name__=='__main__':unittest.main(verbosity=2)
