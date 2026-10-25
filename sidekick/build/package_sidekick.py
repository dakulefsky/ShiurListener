"""Repack the existing licensed portable runtime with the Sidekick facelift."""
import argparse,hashlib,json,pathlib,struct,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--base',type=pathlib.Path,required=True);args=parser.parse_args()
 package=ROOT/'sidekick-1.1.0.otzplugin';launcher=ROOT/'build/windows/Sidekick.exe'
 manifest=json.loads((ROOT/'plugin/manifest.json').read_text())
 assert manifest['id']=='org.shiurplayer.companion' and manifest['version']=='1.1.0'
 replacements={n:(ROOT/'companion'/n).read_bytes() for n in ['companion.py','floating_bar.py','hotkeys.py','runtime_policy.py','desktop.py']}
 replacements['READ ME FIRST.txt']=(ROOT/'READ ME FIRST.txt').read_bytes()
 replacements['Sidekick.exe']=launcher.read_bytes()
 out=ROOT/'sidekick-windows-x64-1.1.0.zip'
 with zipfile.ZipFile(args.base) as src,zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as dst:
  written=set()
  for item in src.infolist():
   assert item.filename.startswith('Shiur Player/')
   relative=item.filename[len('Shiur Player/'):]
   if relative.endswith('.otzplugin') or relative=='PORTABLE-ORIGINAL-NOTES.txt':continue
   if relative=='Shiur Player.exe':relative='Sidekick.exe'
   data=replacements.get(relative,src.read(item.filename))
   if relative=='BUILD-INFO.json':
    info=json.loads(data);info.update(version='1.1.0',variant='Native setup window and bilingual controller',pluginId=manifest['id'],pluginName='נגן שיעורים',pluginVersion='1.1.0',baseBundleSha256=hashlib.sha256(args.base.read_bytes()).hexdigest(),validation='UI/service and mocked Win32 controls pass. Archive integrity and x64 launcher checked. Windows desktop execution is unverified.')
    data=(json.dumps(info,ensure_ascii=False,indent=2)+'\n').encode()
   dst.writestr('Sidekick/'+relative,data);written.add(relative)
  for relative,data in replacements.items():
   if relative not in written:dst.writestr('Sidekick/'+relative,data)
  dst.write(package,'Sidekick/'+package.name)
 with zipfile.ZipFile(out) as z,zipfile.ZipFile(args.base) as src:
  assert z.testzip() is None
  assert [n for n in z.namelist() if n.endswith('.otzplugin')]==['Sidekick/'+package.name]
  assert z.read('Sidekick/'+package.name)==package.read_bytes()
  for relative,data in replacements.items():assert z.read('Sidekick/'+relative)==data
  for n in src.namelist():
   relative=n[len('Shiur Player/'):]
   if relative.startswith('runtime/') or relative.endswith(('LICENSE.txt','NOTICES.txt','OFL.txt')):assert z.read('Sidekick/'+relative)==src.read(n)
  for n in ['Sidekick/Sidekick.exe','Sidekick/runtime/python/python.exe','Sidekick/runtime/vlc/libvlc.dll']:
   data=z.read(n);assert data[:2]==b'MZ';offset=struct.unpack_from('<I',data,0x3c)[0];assert data[offset:offset+4]==b'PE\0\0';assert struct.unpack_from('<H',data,offset+4)[0]==0x8664
  binary=z.read('Sidekick/Sidekick.exe');offset=struct.unpack_from('<I',binary,0x3c)[0];assert struct.unpack_from('<H',binary,offset+24+68)[0]==2, 'Launcher must use the Windows GUI subsystem'
 print(f'Verified {out}: {out.stat().st_size:,} bytes; unchanged runtime/licenses, current sources and plugin, x64 launcher.')
if __name__=='__main__':main()
