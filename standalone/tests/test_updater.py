import hashlib,io,json,pathlib,sys,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'app'))
import updater
class Response(io.BytesIO):
 def __init__(self,data,url):super().__init__(data);self.url=url
 def geturl(self):return self.url
class Tests(unittest.TestCase):
 def release(self,data=b'installer'):
  return {'version':'0.6.1','url':'https://raw.githubusercontent.com/dakulefsky/ShiurListener/main/downloads/shiur-player-setup-0.6.1.exe','sha256':hashlib.sha256(data).hexdigest(),'size':len(data)}
 def test_new_version_and_no_downgrade(self):
  release=self.release()
  self.addCleanup(patch.stopall);patch.object(updater,'APP_VERSION','0.6.0').start()
  with patch.object(updater.urllib.request,'urlopen',return_value=Response(json.dumps(release).encode(),updater.CHANNEL)):
   self.assertEqual(updater.check(),release)
  release['version']='0.5.1';release['url']=release['url'].replace('0.6.1','0.5.1')
  with patch.object(updater.urllib.request,'urlopen',return_value=Response(json.dumps(release).encode(),updater.CHANNEL)):self.assertIsNone(updater.check())
 def test_verified_download_and_corruption(self):
  release=self.release()
  with patch.object(updater.urllib.request,'urlopen',return_value=Response(b'installer',release['url'])):
   file=updater.download(release);self.assertEqual(file.read_bytes(),b'installer');file.unlink();file.parent.rmdir()
  with patch.object(updater.urllib.request,'urlopen',return_value=Response(b'corrupted',release['url'])):
   with self.assertRaises(ValueError):updater.download(release)
 def test_foreign_hosts_and_redirects_are_rejected(self):
  release=self.release();release['url']='https://example.com/setup.exe'
  with self.assertRaises(ValueError):updater.validate_release(release)
  with patch.object(updater.urllib.request,'urlopen',return_value=Response(b'{}','https://example.com/')):
   with self.assertRaises(ValueError):updater.check()
