import unittest
from scan import schedule,sha,scan
class Tests(unittest.TestCase):
 def test_exactly_two_separated_interior_checks(self):
  t=schedule(3600,'fixture');self.assertEqual(len(t),2);self.assertTrue(700<t[0]<1260);self.assertTrue(2300<t[1]<2880)
 def test_schedule_reproducible_and_content_keyed(self):
  self.assertEqual(schedule(3600,'a'),schedule(3600,'a'));self.assertNotEqual(schedule(3600,'a'),schedule(3600,'b'))
 def test_bad_durations_not_approved(self):
  for d in [0,299.9,float('nan'),float('inf')]:
   with self.assertRaises(ValueError):schedule(d,'a')
 def test_expired_budget_stops_before_decoder(self):
  import pathlib
  with self.assertRaises(TimeoutError):scan(pathlib.Path('unused.wav'),None,budget=0)
 def test_hashing_checks_budget(self):
  import pathlib,tempfile,time
  with tempfile.TemporaryDirectory() as d:
   file=pathlib.Path(d)/'file';file.write_bytes(b'audio')
   with self.assertRaises(TimeoutError):sha(file,time.perf_counter()-1)
 def test_only_two_decodes_and_predictions_even_when_music_found(self):
  import tempfile,pathlib,json,numpy as np
  from unittest.mock import patch
  class Model:
   def __init__(self):self.calls=0
   def set_tensor(self,*args):pass
   def invoke(self):self.calls+=1
   def get_output_details(self):return [{'index':1}]
   def get_tensor(self,*args):
    values=np.zeros((1,521));values[0,132]=.9;return values
  with tempfile.TemporaryDirectory() as d:
   file=pathlib.Path(d)/'recording.wav';file.write_bytes(b'fixture');model=Model()
   with patch('scan.subprocess.check_output',return_value=json.dumps({'streams':[{'codec_type':'audio'}],'format':{'duration':'3600'}}).encode()),patch('scan.decode',return_value=np.zeros(15600,np.float32)) as decoder:
    result=scan(file,model)
   self.assertEqual(decoder.call_count,2);self.assertEqual(model.calls,2);self.assertEqual(result['sampled_windows'],2);self.assertEqual(result['decision'],'music_detected_in_samples');self.assertFalse(result['full_file_approved'])
if __name__=='__main__' :unittest.main()
