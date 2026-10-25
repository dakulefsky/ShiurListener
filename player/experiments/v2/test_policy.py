import unittest
from policy import decide
class Tests(unittest.TestCase):
 def window(self,start=0,seconds=.975,speech=.9,music=0):return dict(start=start,seconds=seconds,speech=speech,music=music,singing=0)
 def test_short_insertion_in_long_speech_is_held(self):
  windows=[self.window(i*.975) for i in range(400)];windows[200]['music']=.9
  self.assertEqual(decide(windows)['decision'],'uncertain');self.assertEqual(decide(windows,strict=False)['decision'],'allow')
 def test_sustained_music_blocks_even_in_long_recording(self):
  windows=[self.window(i*.975) for i in range(400)]
  for i in range(200,204):windows[i]['music']=.9
  result=decide(windows);self.assertEqual(result['decision'],'block');self.assertEqual(len(result['segments']),1)
 def test_silence_is_not_a_pass(self):self.assertEqual(decide([self.window(speech=0)])['decision'],'uncertain')
 def test_bad_scores_are_rejected(self):
  with self.assertRaises(ValueError):decide([self.window(music=float('nan'))])
 def test_partial_frame_is_not_counted_as_full_frame(self):
  result=decide([self.window(seconds=10),self.window(start=10,seconds=.1,music=.9)])
  self.assertAlmostEqual(result['music_fraction'],.1/10.1);self.assertEqual(result['segments'][0]['end'],10.1)
if __name__=='__main__':unittest.main()
