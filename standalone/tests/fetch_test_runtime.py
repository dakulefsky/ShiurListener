"""CI only: obtain the already-published Windows VLC runtime, verifying its archive."""
import hashlib,io,pathlib,urllib.request,zipfile
URL='https://raw.githubusercontent.com/dakulefsky/ShiurListener/main/downloads/shiur-player-windows-x64-0.9.3.zip'
SHA256='79e66157e482572e46ed3e5f7d048b9e32ca2e13b27f8d584f6d28408e52a3a5'
if __name__=='__main__':
 with urllib.request.urlopen(URL,timeout=60) as response:payload=response.read(40*1024*1024)
 if hashlib.sha256(payload).hexdigest()!=SHA256:raise RuntimeError('Test runtime checksum mismatch')
 target=pathlib.Path(__file__).resolve().parents[1]/'app/runtime/vlc'
 prefix='Shiur Player/runtime/vlc/'
 with zipfile.ZipFile(io.BytesIO(payload)) as archive:
  for name in archive.namelist():
   if not name.startswith(prefix) or name.endswith('/'):continue
   relative=pathlib.PurePosixPath(name[len(prefix):])
   if relative.is_absolute() or '..' in relative.parts:raise RuntimeError('Invalid test runtime path')
   output=target.joinpath(*relative.parts);output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(archive.read(name))
 print('Verified Windows VLC test runtime extracted')
