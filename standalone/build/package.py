"""Build an offline standalone bundle from the existing licensed audio runtime."""
import argparse,hashlib,json,pathlib,struct,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--base',type=pathlib.Path,required=True);args=parser.parse_args()
 output=ROOT/'shiur-player-windows-x64-0.1.0.zip';prefix='Shiur Player/'
 with zipfile.ZipFile(args.base) as base,zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as bundle:
  for name in base.namelist():
   relative=name.split('/',1)[1]
   if relative.startswith('runtime/') or relative in ['THIRD-PARTY-NOTICES.txt','GO-LICENSE.txt']:
    bundle.writestr(prefix+relative,base.read(name))
  for path in sorted((ROOT/'app').rglob('*')):
   if path.is_file() and '__pycache__' not in path.parts:bundle.write(path,prefix+path.relative_to(ROOT/'app').as_posix())
  bundle.write(ROOT/'build/Shiur Player.exe',prefix+'Shiur Player.exe')
  bundle.write(ROOT/'READ ME FIRST.txt',prefix+'READ ME FIRST.txt')
  info=json.loads(base.read('Sidekick/BUILD-INFO.json'))
  info.update(version='0.1.0',variant='Standalone native player',baseBundleSha256=hashlib.sha256(args.base.read_bytes()).hexdigest(),validation='Persistence/controller and mocked native window callbacks pass; real VLC WAV/MP3 decoding passes on Linux with dummy output. Windows GUI execution remains unverified.')
  for key in ['pluginId','pluginName','pluginVersion']:info.pop(key,None)
  bundle.writestr(prefix+'BUILD-INFO.json',json.dumps(info,ensure_ascii=False,indent=2)+'\n')
 with zipfile.ZipFile(output) as bundle,zipfile.ZipFile(args.base) as base:
  assert bundle.testzip() is None
  assert not any(name.endswith('.otzplugin') for name in bundle.namelist())
  assert not any(name.endswith(('/companion.py','/desktop.py')) for name in bundle.namelist())
  for path in (ROOT/'app').rglob('*'):
   if path.is_file() and '__pycache__' not in path.parts:assert bundle.read(prefix+path.relative_to(ROOT/'app').as_posix())==path.read_bytes()
  for name in base.namelist():
   relative=name.split('/',1)[1]
   if relative.startswith('runtime/'):assert bundle.read(prefix+relative)==base.read(name)
  data=bundle.read(prefix+'Shiur Player.exe');assert data[:2]==b'MZ';offset=struct.unpack_from('<I',data,0x3c)[0]
  assert data[offset:offset+4]==b'PE\0\0' and struct.unpack_from('<H',data,offset+4)[0]==0x8664
  assert struct.unpack_from('<H',data,offset+24+68)[0]==2
  entry=bundle.read(prefix+'main.py').decode();engine=bundle.read(prefix+'engine.py').decode()
  assert 'Server(' not in entry and 'http.server' not in engine and 'token_urlsafe' not in entry
 print(f'Verified standalone Windows GUI x64 ZIP: {output}, {output.stat().st_size:,} bytes; no plugin or connection service; runtime bytes preserved.')
if __name__=='__main__':main()
