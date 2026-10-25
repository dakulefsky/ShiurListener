"""Playback regressions: repeat boundaries, sleeping and saved seeks before load."""
import json
import math
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'app'))
from engine import Player
from test_player import Audio


class PlaybackToolsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=pathlib.Path(self.tmp.name)
        self.audio=self.root/'audio';self.audio.mkdir()
        for name in ('01.mp3','02.mp3'):(self.audio/name).write_bytes(b'test')
        self.backend=Audio();self.player=Player(self.audio,self.root/'data',self.backend)
        self.ids=[t['id'] for t in self.player.tracks]

    def tearDown(self):self.tmp.cleanup()

    def start(self):
        self.player.command({'op':'load','id':self.ids[0],'queue':self.ids})
        self.player.command({'op':'play'});self.player.tick()

    def loop(self,start=10,end=20):
        self.backend.position=start;self.player.command({'op':'loop_a'})
        self.backend.position=end;self.player.command({'op':'loop_b'})

    def test_repeat_seeks_back_without_completing_or_advancing(self):
        self.start();self.player.saved['autoNext']=True;self.loop()
        self.backend.position=20.25;self.player.tick()
        self.assertEqual(self.backend.position,10)
        self.assertEqual(self.player.saved['currentId'],self.ids[0])
        self.assertFalse(self.player.saved['tracks'][self.ids[0]]['completed'])
        self.player.command({'op':'loop_clear'});self.backend.position=24;self.player.tick()
        self.assertEqual(self.backend.position,24)

    def test_repeat_can_end_at_end_of_recording_and_is_cleared_when_switching(self):
        self.start();self.player.saved['autoNext']=True;self.loop(100,120)
        self.backend.status='ended';self.backend.position=120;self.player.was_playing=True
        self.player.tick();self.player.tick()
        self.assertEqual(self.player.saved['currentId'],self.ids[0])
        self.assertEqual(self.backend.position,100)
        self.assertEqual(self.backend.status,'playing')
        self.assertFalse(self.player.saved['tracks'][self.ids[0]]['completed'])
        self.player.command({'op':'next'})
        self.assertIsNone(self.player.snapshot()['loopA'])
        self.assertIsNone(self.player.snapshot()['loopB'])

    def test_repeat_rejects_missing_or_invalid_end(self):
        self.start()
        with self.assertRaises(ValueError):self.player.command({'op':'loop_b'})
        self.backend.position=10;self.player.command({'op':'loop_a'})
        for position in (9,10,10.25):
            self.backend.position=position
            with self.assertRaises(ValueError):self.player.command({'op':'loop_b'})
        self.assertIsNone(self.player.snapshot()['loopB'])

    def test_end_timer_prevents_autonext_and_remains_stopped(self):
        self.start();self.player.saved['autoNext']=True;self.loop()
        state=self.player.command({'op':'sleep_timer','mode':'end'})
        self.assertTrue(state['sleepAtEnd']);self.assertIsNone(state['loopA'])
        self.backend.position=120;self.backend.status='ended';self.player.was_playing=True
        self.player.tick();self.player.tick()
        self.assertEqual(self.player.saved['currentId'],self.ids[0])
        self.assertEqual(self.player.snapshot()['status'],'paused')
        self.assertFalse(self.player.snapshot()['sleepAtEnd'])
        self.assertTrue(self.player.saved['tracks'][self.ids[0]]['completed'])
        self.player.command({'op':'play'});self.player.tick()
        self.assertEqual(self.backend.position,0);self.assertEqual(self.backend.status,'playing')

    def test_sleep_timer_cancels_end_mode_and_pauses_repeat(self):
        self.start();self.player.command({'op':'sleep_timer','mode':'end'})
        self.loop()
        self.assertFalse(self.player.snapshot()['sleepAtEnd'])
        self.player.command({'op':'sleep_timer','minutes':15})
        self.player.sleep_deadline=.01;self.backend.position=25;self.player.tick()
        self.assertEqual(self.backend.status,'paused');self.assertEqual(self.backend.position,25)

    def test_seek_before_loading_is_paused_clamped_and_saved_immediately(self):
        ident=self.ids[0]
        self.player.saved['currentId']=ident
        self.player.saved['tracks'][ident]={'position':30.125,'duration':120}
        result=self.player.command({'op':'seek','value':65.432})
        self.assertEqual(result['position'],65.432);self.assertFalse(self.player.pending['autoplay'])
        saved=json.loads(self.player.file.read_text())
        self.assertEqual(saved['tracks'][ident]['position'],65.432)
        restored=Player(None,self.root/'data',Audio())
        self.assertEqual(restored.snapshot()['position'],65.432)
        self.assertEqual(restored.snapshot()['status'],'paused')
        self.player.command({'op':'seek','value':200});self.player.tick()
        self.assertEqual(self.backend.position,120);self.assertEqual(self.backend.status,'paused')

    def test_skip_before_loading_starts_from_exact_saved_position(self):
        ident=self.ids[0];self.player.saved['currentId']=ident
        self.player.saved['tracks'][ident]={'position':65.432,'duration':120}
        self.player.command({'op':'skip','direction':-1});self.player.tick()
        self.assertAlmostEqual(self.backend.position,50.432)
        self.assertEqual(self.backend.status,'paused')

    def test_invalid_seek_does_not_change_or_load_audio(self):
        self.player.saved['currentId']=self.ids[0]
        for value in (math.nan,math.inf,-math.inf,-1):
            with self.assertRaises(ValueError):self.player.command({'op':'seek','value':value})
        self.assertIsNone(self.player.active)

    def test_pause_before_decoder_finishes_seeking_preserves_requested_position(self):
        self.start();self.backend.position=10
        requested=[]
        self.backend.seek=requested.append
        self.player.command({'op':'seek','value':65.432})
        self.player.command({'op':'pause'})
        self.assertEqual(requested,[65.432])
        self.assertEqual(self.backend.position,10)
        restored=Player(None,self.root/'data',Audio())
        self.assertEqual(restored.snapshot()['position'],65.432)
        self.backend.position=65.432
        self.assertEqual(self.player.snapshot()['position'],65.432)
        self.assertIsNone(self.player.seek_target)

    def test_completed_recording_restarts_after_reopening(self):
        self.start();self.backend.position=120;self.backend.status='ended';self.player.tick()
        restored=Player(None,self.root/'data',Audio())
        self.assertEqual(restored.snapshot()['position'],120)
        restored.command({'op':'play'});restored.tick()
        self.assertEqual(restored.backend.position,0)
        self.assertFalse(restored.saved['tracks'][self.ids[0]]['completed'])


if __name__=='__main__':unittest.main()
