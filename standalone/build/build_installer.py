"""Build the no-console per-user Windows setup and public update channel."""
import argparse,hashlib,json,os,pathlib,runpy,shutil,struct,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
VERSION=runpy.run_path(str(ROOT/'app/version.py'))['APP_VERSION']
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--go',default='go');args=parser.parse_args()
 env={**os.environ,'GOOS':'windows','GOARCH':'amd64','CGO_ENABLED':'0','GO111MODULE':'off','GOTOOLCHAIN':'local'}
 directory=ROOT/'build/installer';shutil.copy2(ROOT/f'shiur-player-windows-x64-{VERSION}.zip',directory/'payload.zip')
 common=[args.go,'build','-trimpath']
 subprocess.run(common+['-ldflags=-s -w -H windowsgui','-o',str(directory/'installed-launcher.exe'),str(ROOT/'build/installed_launcher.go')],env=env,check=True)
 output=ROOT.parent/'downloads'/f'shiur-player-setup-{VERSION}.exe'
 subprocess.run(common+[f'-ldflags=-s -w -H windowsgui -X main.releaseVersion={VERSION}','-o',str(output),'./standalone/build/installer'],cwd=ROOT.parent,env=env,check=True)
 data=output.read_bytes();pe=struct.unpack_from('<I',data,0x3c)[0]
 assert data[:2]==b'MZ' and data[pe:pe+4]==b'PE\0\0' and struct.unpack_from('<H',data,pe+4)[0]==0x8664
 assert struct.unpack_from('<H',data,pe+24+68)[0]==2
 assert (directory/'payload.zip').read_bytes() in data
 assert (directory/'installed-launcher.exe').read_bytes() in data
 release={'version':VERSION,'url':f'https://raw.githubusercontent.com/dakulefsky/ShiurListener/main/downloads/{output.name}','size':len(data),'sha256':hashlib.sha256(data).hexdigest()}
 (output.parent/'standalone-latest.json').write_text(json.dumps(release,indent=2)+'\n')
 print(f'Verified Windows x64 GUI setup: {output}, {len(data):,} bytes; update channel written.')
if __name__=='__main__':main()
