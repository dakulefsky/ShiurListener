"""Build an offline standalone bundle from the existing licensed audio runtime."""
import argparse,hashlib,json,pathlib,struct,zipfile,runpy
ROOT=pathlib.Path(__file__).resolve().parents[1]
VERSION=runpy.run_path(str(ROOT/'app/version.py'))['APP_VERSION']
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--base',type=pathlib.Path,required=True);parser.add_argument('--tk',type=pathlib.Path,required=True,help='Extracted official Python 3.13.17 amd64 tcltk.msi');args=parser.parse_args()
 output=ROOT/f'shiur-player-windows-x64-{VERSION}.zip';prefix='Shiur Player/'
 with zipfile.ZipFile(args.base) as base,zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as bundle:
  for name in base.namelist():
   relative=name.split('/',1)[1]
   if relative.startswith('runtime/') or relative in ['THIRD-PARTY-NOTICES.txt','GO-LICENSE.txt']:
    bundle.writestr(prefix+relative,base.read(name))
  # Match the interpreter ABI. No IDLE, demos, tests, or developer libraries.
  for name in ['_tkinter.pyd','tcl86t.dll','tk86t.dll','zlib1.dll']:
   bundle.write(args.tk/'DLLs'/name,prefix+'runtime/python/'+name)
  for path in sorted((args.tk/'Lib/tkinter').rglob('*')):
   if path.is_file() and not any(part in ('test','tests','__pycache__') for part in path.parts):
    bundle.write(path,prefix+'runtime/python/tkinter/'+path.relative_to(args.tk/'Lib/tkinter').as_posix())
  for directory in ['tcl8','tcl8.6','tk8.6']:
   for path in sorted((args.tk/'tcl'/directory).rglob('*')):
    if path.is_file() and not any(part in ('demos','tests') for part in path.parts):
     bundle.write(path,prefix+'runtime/tcl/'+path.relative_to(args.tk/'tcl').as_posix())
  bundle.writestr(prefix+'TK-RUNTIME-NOTICE.txt','Python Tk runtime: https://www.python.org/ftp/python/3.13.17/amd64/tcltk.msi\nSHA256: ae3e5f9dd998b36d14655cd3444d0af906c1849c60aee40994eeb1e460a3cabf\nTcl license: assets/TCL-LICENSE.txt\nTk license: runtime/tcl/tk8.6/license.terms\nTcl license: https://www.tcl-lang.org/software/tcltk/license.html\nPython license is included in runtime/python/LICENSE.txt.\n')
  for path in sorted((ROOT/'app').rglob('*')):
   if path.is_file() and '__pycache__' not in path.parts and path.relative_to(ROOT/'app').parts[0]!='runtime':bundle.write(path,prefix+path.relative_to(ROOT/'app').as_posix())
  bundle.write(ROOT/'build/Shiur Player.exe',prefix+'Shiur Player.exe')
  bundle.write(ROOT/'READ ME FIRST.txt',prefix+'READ ME FIRST.txt')
  info=json.loads(base.read('Sidekick/BUILD-INFO.json'))
  info.update(version=VERSION,variant='Standalone library, playback dock, queue, repeat and profile backups',tkSource='https://www.python.org/ftp/python/3.13.17/amd64/tcltk.msi',tkMsiSha256='ae3e5f9dd998b36d14655cd3444d0af906c1849c60aee40994eeb1e460a3cabf',baseBundleSha256=hashlib.sha256(args.base.read_bytes()).hexdigest(),validation='Persistence and actual Tk controls, locked column dividers and stable idle repaint tests pass on Linux. Native resize persistence, speed clicks and changed-only repaint pass with Win32 mocks. Real VLC WAV/MP3 decode and speed cycling pass with dummy output. Windows GUI execution remains unverified.')
  for key in ['pluginId','pluginName','pluginVersion']:info.pop(key,None)
  bundle.writestr(prefix+'BUILD-INFO.json',json.dumps(info,ensure_ascii=False,indent=2)+'\n')
 with zipfile.ZipFile(output) as bundle,zipfile.ZipFile(args.base) as base:
  assert bundle.testzip() is None
  assert not any(name.endswith('.otzplugin') for name in bundle.namelist())
  assert not any(name.endswith(('/companion.py','/desktop.py')) for name in bundle.namelist())
  for path in (ROOT/'app').rglob('*'):
   if path.is_file() and '__pycache__' not in path.parts and path.relative_to(ROOT/'app').parts[0]!='runtime':assert bundle.read(prefix+path.relative_to(ROOT/'app').as_posix())==path.read_bytes()
  for name in base.namelist():
   relative=name.split('/',1)[1]
   if relative.startswith('runtime/'):assert bundle.read(prefix+relative)==base.read(name)
  assert bundle.read(prefix+'runtime/tcl/tcl8.6/init.tcl')
  assert bundle.read(prefix+'runtime/tcl/tk8.6/tk.tcl')
  assert bundle.read(prefix+'runtime/python/tkinter/__init__.py')
  assert not any('/idlelib/' in name or '/demos/' in name for name in bundle.namelist())
  for name in ['_tkinter.pyd','tcl86t.dll','tk86t.dll','zlib1.dll']:
   dll=bundle.read(prefix+'runtime/python/'+name);pe=struct.unpack_from('<I',dll,0x3c)[0];assert struct.unpack_from('<H',dll,pe+4)[0]==0x8664
  data=bundle.read(prefix+'Shiur Player.exe');assert data[:2]==b'MZ';offset=struct.unpack_from('<I',data,0x3c)[0]
  assert data[offset:offset+4]==b'PE\0\0' and struct.unpack_from('<H',data,offset+4)[0]==0x8664
  assert struct.unpack_from('<H',data,offset+24+68)[0]==2
  entry=bundle.read(prefix+'main.py').decode();engine=bundle.read(prefix+'engine.py').decode()
  assert 'Server(' not in entry and 'http.server' not in engine and 'token_urlsafe' not in entry
 print(f'Verified standalone Windows GUI x64 ZIP: {output}, {output.stat().st_size:,} bytes; no plugin or connection service; runtime bytes preserved.')
if __name__=='__main__':main()
