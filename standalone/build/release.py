"""Build, stage and publish a standalone release using the verified prior runtime."""
import argparse,array,hashlib,json,math,os,pathlib,re,runpy,shutil,subprocess,sys,tempfile,urllib.request,wave,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
REPO=ROOT.parent
VERSION=runpy.run_path(str(ROOT/'app/version.py'))['APP_VERSION']
BASE_VERSION='0.9.4'
BASE_SHA256='d1bc031c8b59fc05796b1ba00933500fc4b39c1604f1599cc68d904d007fabc4'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
HUSH_TAG='v1.0.0'
HUSH_ASSETS=[
 ('runtime/speech/weya_nc.dll','deployment/lib/weya_nc.dll',22464512,'688bd35590ff29f922579d6567d1b4a3f0709d17'),
 ('runtime/speech/advanced_dfnet16k_model_best_onnx.tar.gz','deployment/models/advanced_dfnet16k_model_best_onnx.tar.gz',8558968,'2838b4a4ec8ed2cb7bff4cd4e89f8bff828e3db0'),
 ('runtime/speech/LICENSE','LICENSE',8549,'1c714550021949d38379ad619f5034caeeb4d843'),
 ('runtime/speech/DATASETS.md','DATASETS.md',3606,'486d7ccbec16a48f431e98feff7d1b42da1e57ad'),
]
def download_hush_assets():
 assets={}
 for target,source,size,expected_blob in HUSH_ASSETS:
  url=f'https://raw.githubusercontent.com/pulp-vision/Hush/{HUSH_TAG}/{source}'
  with urllib.request.urlopen(url,timeout=90) as response:data=response.read()
  if len(data)!=size:raise ValueError(f'Unexpected Hush asset size: {source}')
  blob=hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest()
  if blob!=expected_blob:raise ValueError(f'Hush asset identity mismatch: {source}')
  assets[target]=data
 print('Verified pinned Hush native runtime, model, license and dataset notice.',flush=True)
 return assets
def smoke_test_hush(assets):
 with tempfile.TemporaryDirectory(prefix='shiur-hush-smoke-',ignore_cleanup_errors=True) as directory:
  directory=pathlib.Path(directory);app=directory/'app';speech=app/'runtime'/'speech';speech.mkdir(parents=True)
  library=speech/'weya_nc.dll';model=speech/'advanced_dfnet16k_model_best_onnx.tar.gz'
  library.write_bytes(assets['runtime/speech/weya_nc.dll'])
  model.write_bytes(assets['runtime/speech/advanced_dfnet16k_model_best_onnx.tar.gz'])
  source=directory/'input.wav';output=directory/'output.wav'
  samples=array.array('h',(round(5000*math.sin(2*math.pi*220*i/16000)+350*math.sin(2*math.pi*1100*i/16000)) for i in range(32000)))
  with wave.open(str(source),'wb') as audio:
   audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(16000);audio.writeframes(samples.tobytes())
  sys.path.insert(0,str(ROOT/'app'))
  from speech_enhancement import enhance_file
  original=source.read_bytes()
  enhance_file(source,output,app)
  if source.read_bytes()!=original:raise ValueError('Speech enhancement modified the original input.')
  with wave.open(str(output),'rb') as audio:
   if audio.getnchannels()!=1 or audio.getsampwidth()!=2 or audio.getframerate()!=16000 or audio.getnframes()!=len(samples):
    raise ValueError('Hush native runtime smoke test produced invalid audio.')
 print('Hush native runtime loaded the model and processed a WAV successfully.',flush=True)
def git(*args):subprocess.run(['git',*args],cwd=REPO,check=True)
def build():
 if not re.fullmatch(r'\d+\.\d+\.\d+',VERSION):raise ValueError('Invalid version')
 if (REPO/'downloads'/f'shiur-player-setup-{VERSION}.exe').exists():raise ValueError('Version already published')
 base=ROOT/'build/runtime-base.zip'
 url=f'https://raw.githubusercontent.com/dakulefsky/ShiurListener/main/downloads/shiur-player-windows-x64-{BASE_VERSION}.zip'
 urllib.request.urlretrieve(url,base)
 assert digest(base)==BASE_SHA256,'Prior runtime checksum mismatch'
 hush_assets=download_hush_assets()
 smoke_test_hush(hush_assets)
 env={**os.environ,'GOOS':'windows','GOARCH':'amd64','CGO_ENABLED':'0','GO111MODULE':'off','GOTOOLCHAIN':'local'}
 subprocess.run(['go','build','-trimpath','-ldflags=-s -w -H windowsgui','-o',str(ROOT/'build/Shiur Player.exe'),str(ROOT/'build/launcher.go')],env=env,check=True)
 prefix='Shiur Player/'
 output=ROOT/f'shiur-player-windows-x64-{VERSION}.zip'
 with zipfile.ZipFile(base) as old,zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as bundle:
  assert old.testzip() is None
  retained=[]
  for name in old.namelist():
   relative=name.removeprefix(prefix)
   if relative.startswith('runtime/') or relative in ('THIRD-PARTY-NOTICES.txt','GO-LICENSE.txt','TK-RUNTIME-NOTICE.txt'):
    bundle.writestr(name,old.read(name));retained.append(name)
  for path in sorted((ROOT/'app').rglob('*')):
   if path.is_file() and '__pycache__' not in path.parts and path.relative_to(ROOT/'app').parts[0]!='runtime':
    bundle.write(path,prefix+path.relative_to(ROOT/'app').as_posix())
  bundle.write(ROOT/'build/Shiur Player.exe',prefix+'Shiur Player.exe')
  bundle.write(ROOT/'READ ME FIRST.txt',prefix+'READ ME FIRST.txt')
  for name,data in hush_assets.items():bundle.writestr(prefix+name,data)
  info=json.loads(old.read(prefix+'BUILD-INFO.json'))
  info.update(version=VERSION,baseStandaloneVersion=BASE_VERSION,baseStandaloneSha256=BASE_SHA256)
  bundle.writestr(prefix+'BUILD-INFO.json',json.dumps(info,indent=2)+'\n')
 with zipfile.ZipFile(output) as bundle,zipfile.ZipFile(base) as old:
  assert bundle.testzip() is None
  for name in retained:assert bundle.read(name)==old.read(name),'Runtime bytes changed'
  for path in (ROOT/'app').rglob('*'):
   if path.is_file() and '__pycache__' not in path.parts and path.relative_to(ROOT/'app').parts[0]!='runtime':
    assert bundle.read(prefix+path.relative_to(ROOT/'app').as_posix())==path.read_bytes()
  for name,data in hush_assets.items():assert bundle.read(prefix+name)==data
  for name in ('runtime/python/pythonw.exe','runtime/python/_tkinter.pyd','runtime/tcl/tk8.6/tk.tcl','runtime/vlc/libvlc.dll','runtime/speech/weya_nc.dll','runtime/speech/advanced_dfnet16k_model_best_onnx.tar.gz','runtime/speech/LICENSE','runtime/speech/DATASETS.md'):
   assert bundle.read(prefix+name)
 subprocess.run([os.sys.executable,str(ROOT/'build/build_installer.py')],check=True)
 # Keep the public channel unchanged until the actual candidate passes installation.
 metadata=json.loads((REPO/'downloads/standalone-latest.json').read_text(encoding='utf-8'))
 (ROOT/'build/release-metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
 git('restore','downloads/standalone-latest.json')
 print('Verified source bytes and preserved runtime; candidate built.',flush=True)
def stage():
 qa=REPO/'downloads/qa';qa.mkdir(parents=True,exist_ok=True)
 setup=f'shiur-player-setup-{VERSION}.exe'
 shutil.copy2(REPO/'downloads'/setup,qa/setup)
 shutil.copy2(ROOT/'build/release-metadata.json',qa/setup.replace('.exe','.json'))
 git('add','--sparse','-f',f'downloads/qa/{setup}',f'downloads/qa/{setup.replace(".exe",".json")}')
 git('commit','-m',f'Stage standalone {VERSION} installer for native Windows verification')
 git('push','origin','HEAD:main')
def publish():
 metadata=json.loads((ROOT/'build/release-metadata.json').read_text(encoding='utf-8'))
 setup=REPO/'downloads'/f'shiur-player-setup-{VERSION}.exe'
 assert digest(setup)==metadata['sha256'] and setup.stat().st_size==metadata['size']
 portable=REPO/'downloads'/f'shiur-player-windows-x64-{VERSION}.zip'
 shutil.copy2(ROOT/portable.name,portable)
 source=REPO/'downloads'/f'shiur-player-standalone-source-{VERSION}.zip'
 with zipfile.ZipFile(source,'w',zipfile.ZIP_DEFLATED) as archive:
  for path in sorted(ROOT.rglob('*')):
   if not path.is_file():continue
   relative=path.relative_to(ROOT)
   if '__pycache__' in relative.parts or path.suffix in ('.zip','.exe','.pyc') or relative.name=='release-metadata.json':continue
   archive.write(path,'standalone/'+relative.as_posix())
  archive.write(REPO/'.github/workflows/release-standalone.yml','.github/workflows/release-standalone.yml')
 sums=REPO/'downloads/SHA256SUMS.txt'
 text=sums.read_text(encoding='utf-8').rstrip()+'\n'
 for path in (setup,portable,source):
  text+=f'{digest(path)}  {path.name}\n'
 sums.write_text(text,encoding='utf-8')
 (REPO/'downloads/standalone-latest.json').write_text(json.dumps(metadata,indent=2)+'\n')
 readme=REPO/'downloads/README.md'
 text=readme.read_text(encoding='utf-8')
 notes=(ROOT/'RELEASE-NOTES.md').read_text(encoding='utf-8').strip()
 text=re.sub(r'## Current standalone:.*?(?=\n## )',f'## Current standalone: {VERSION}\n\n[Download setup](shiur-player-setup-{VERSION}.exe) or choose **Check for updates** in the app. {notes} Existing listening positions are preserved. Windows and Linux desktop checks and the actual packaged Windows installer pass.\n',text,count=1,flags=re.S)
 readme.write_text(text,encoding='utf-8')
 paths=[f'downloads/{path.name}' for path in (setup,portable,source)]+['downloads/SHA256SUMS.txt','downloads/standalone-latest.json','downloads/README.md']
 git('add','--sparse','-f',*paths)
 git('commit','-m',f'Release Shiur Player {VERSION} after native installer verification')
 git('push','origin','HEAD:main')
 print(f'Published standalone {VERSION}: {metadata}',flush=True)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('step',choices=['build','stage','publish'])
 globals()[parser.parse_args().step]()
