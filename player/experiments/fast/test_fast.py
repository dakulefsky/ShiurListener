import unittest
from scan import schedule,sha,scan
class Tests(unittest.TestCase):
 def test_samples_cover_start_end_and_interior(self):
  t=schedule(3600,'fixture');self.assertEqual(len(t),24);self.assertEqual(t[0],0);self.assertAlmostEqual(t[-1],3599.025);self.assertTrue(any(1700<x<1900 for x in t))
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
if __name__=='__main__':unittest.main()
