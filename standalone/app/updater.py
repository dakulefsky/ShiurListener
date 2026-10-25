"""Manual HTTPS update checks. No browser, listener or background network polling."""
import hashlib,json,os,pathlib,re,subprocess,tempfile,urllib.request
from version import APP_VERSION
CHANNEL='https://raw.githubusercontent.com/dakulefsky/ShiurListener/main/downloads/standalone-latest.json'
MAX_DOWNLOAD=100*1024*1024

def version_tuple(value):
 if not isinstance(value,str) or not re.fullmatch(r'\d+\.\d+\.\d+',value):raise ValueError('Invalid update version.')
 return tuple(map(int,value.split('.')))

def validate_release(data):
 version_tuple(data['version'])
 expected=f"https://raw.githubusercontent.com/dakulefsky/ShiurListener/main/downloads/shiur-player-setup-{data['version']}.exe"
 if data.get('url')!=expected:raise ValueError('The update download address is invalid.')
 if not isinstance(data.get('sha256'),str) or not re.fullmatch('[a-f0-9]{64}',data['sha256']):raise ValueError('The update checksum is invalid.')
 if not isinstance(data.get('size'),int) or not 0<data['size']<=MAX_DOWNLOAD:raise ValueError('The update size is invalid.')
 return data

def check():
 request=urllib.request.Request(CHANNEL,headers={'User-Agent':'ShiurPlayer/'+APP_VERSION})
 with urllib.request.urlopen(request,timeout=20) as response:
  if response.geturl()!=CHANNEL:raise ValueError('Unexpected update server redirect.')
  raw=response.read(65537)
 if len(raw)>65536:raise ValueError('The update information is too large.')
 release=validate_release(json.loads(raw))
 return release if version_tuple(release['version'])>version_tuple(APP_VERSION) else None

def download(release):
 validate_release(release)
 directory=pathlib.Path(tempfile.mkdtemp(prefix='ShiurPlayer-update-'));target=directory/'Setup.exe';digest=hashlib.sha256();count=0
 try:
  request=urllib.request.Request(release['url'],headers={'User-Agent':'ShiurPlayer/'+APP_VERSION})
  with urllib.request.urlopen(request,timeout=30) as response,target.open('wb') as output:
   if response.geturl()!=release['url']:raise ValueError('Unexpected download server redirect.')
   while chunk:=response.read(1024*256):
    count+=len(chunk)
    if count>release['size']:raise ValueError('The update download exceeds its expected size.')
    digest.update(chunk);output.write(chunk)
  if count!=release['size'] or digest.hexdigest()!=release['sha256']:raise ValueError('The update download failed its integrity check. Please try again.')
  return target
 except Exception:
  target.unlink(missing_ok=True);directory.rmdir();raise

def install(target):
 if os.name!='nt':raise RuntimeError('Windows updates can only be installed on Windows.')
 return subprocess.Popen([str(target),'--update',str(os.getpid())],creationflags=0x08000000,close_fds=True)
