"""Build, stage and publish a standalone release using the verified prior runtime."""
import argparse,hashlib,json,os,pathlib,re,runpy,shutil,subprocess,urllib.request,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
REPO=ROOT.parent
VERSION=runpy.run_path(str(ROOT/'app/version.py'))['APP_VERSION']
BASE_VERSION='0.9.4'
BASE_SHA256='d1bc031c8b59fc05796b1ba00933500fc4b39c1604f1599cc68d904d007fabc4'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def git(*args):subprocess.run(['git',*args],cwd=REPO,check=True)
def build():
 if not re.fullmatch(r'\d+\.\d+\.\d+',VERSION):raise ValueError('Invalid version')
 if (REPO/'downloads'/f'shiur-player-setup-{VERSION}.exe').exists():raise ValueError('Version already published')
 base=ROOT/'build/runtime-base.zip'
 url=f'https://raw.githubusercontent.com/dakulefsky/ShiurListener/main/downloads/shiur-player-windows-x64-{BASE_VERSION}.zip'
 urllib.request.urlretrieve(url,base)
 assert digest(base)==BASE_SHA256,'Prior runtime checksum mismatch'
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
  info=json.loads(old.read(prefix+'BUILD-INFO.json'))
  info.update(version=VERSION,baseStandaloneVersion=BASE_VERSION,baseStandaloneSha256=BASE_SHA256)
  bundle.writestr(prefix+'BUILD-INFO.json',json.dumps(info,indent=2)+'\n')
 with zipfile.ZipFile(output) as bundle,zipfile.ZipFile(base) as old:
  assert bundle.testzip() is None
  for name in retained:assert bundle.read(name)==old.read(name),'Runtime bytes changed'
  for path in (ROOT/'app').rglob('*'):
   if path.is_file() and '__pycache__' not in path.parts and path.relative_to(ROOT/'app').parts[0]!='runtime':
    assert bundle.read(prefix+path.relative_to(ROOT/'app').as_posix())==path.read_bytes()
  for name in ('runtime/python/pythonw.exe','runtime/python/_tkinter.pyd','runtime/tcl/tk8.6/tk.tcl','runtime/vlc/libvlc.dll'):
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
 text=re.sub(r'## Current standalone:.*?(?=\n## )',f'## Current standalone: {VERSION}\n\n[Download setup](shiur-player-setup-{VERSION}.exe) or choose **Check for updates** in the app. Adds an × close button to both mini player views, keeps long titles from crowding the shiurim list, protects the Mini player button beside long collection names, and adds full-title hover previews. Existing listening positions are preserved. Windows and Linux desktop checks and the actual packaged Windows installer pass.\n',text,count=1,flags=re.S)
 readme.write_text(text,encoding='utf-8')
 paths=[f'downloads/{path.name}' for path in (setup,portable,source)]+['downloads/SHA256SUMS.txt','downloads/standalone-latest.json','downloads/README.md']
 git('add','-f',*paths)
 git('commit','-m',f'Release Shiur Player {VERSION} after native installer verification')
 git('push','origin','HEAD:main')
 print(f'Published standalone {VERSION}: {metadata}',flush=True)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('step',choices=['build','stage','publish'])
 globals()[parser.parse_args().step]()
