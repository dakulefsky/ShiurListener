"""CI-only end-to-end installation in a disposable Windows runner account.
Downloads a checksum-bound candidate; installs, launches, verifies and repairs it.
"""
import ctypes,hashlib,json,os,pathlib,re,subprocess,sys,tempfile,time,urllib.request


def run():
 if sys.platform!='win32' or os.environ.get('GITHUB_ACTIONS')!='true':
  raise RuntimeError('Run this installation test only in a disposable GitHub Windows runner.')
 version=os.environ.get('SHIUR_INSTALLER_VERSION','')
 if not re.fullmatch(r'\d+\.\d+\.\d+',version):raise ValueError('A candidate version is required')
 origin='https://raw.githubusercontent.com/dakulefsky/ShiurListener/main/downloads/qa/'
 with urllib.request.urlopen(origin+f'shiur-player-setup-{version}.json',timeout=30) as response:metadata=json.load(response)
 assert metadata['version']==version and re.fullmatch(r'[0-9a-f]{64}',metadata['sha256'])
 url=origin+f'shiur-player-setup-{version}.exe?sha256='+metadata['sha256']
 with urllib.request.urlopen(url,timeout=60) as response:payload=response.read(50*1024*1024)
 assert len(payload)==metadata['size'] and hashlib.sha256(payload).hexdigest()==metadata['sha256']
 from ctypes import wintypes as w
 user=ctypes.WinDLL('user32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
 def bind(library,name,result,args):
  function=getattr(library,name);function.restype=result;function.argtypes=args;return function
 find=bind(user,'FindWindowW',w.HWND,[w.LPCWSTR,w.LPCWSTR])
 classname=bind(user,'GetClassNameW',ctypes.c_int,[w.HWND,w.LPWSTR,ctypes.c_int])
 dialogtext=bind(user,'GetDlgItemTextW',ctypes.c_int,[w.HWND,ctypes.c_int,w.LPWSTR,ctypes.c_int])
 pidof=bind(user,'GetWindowThreadProcessId',w.DWORD,[w.HWND,ctypes.POINTER(w.DWORD)])
 post=bind(user,'PostMessageW',w.BOOL,[w.HWND,w.UINT,w.WPARAM,w.LPARAM])
 openprocess=bind(kernel,'OpenProcess',w.HANDLE,[w.DWORD,w.BOOL,w.DWORD])
 waitprocess=bind(kernel,'WaitForSingleObject',w.DWORD,[w.HANDLE,w.DWORD])
 closehandle=bind(kernel,'CloseHandle',w.BOOL,[w.HANDLE])
 app=pathlib.Path(os.environ['LOCALAPPDATA'])/'Programs/ShiurPlayer'
 profile=pathlib.Path(os.environ['LOCALAPPDATA'])/'ShiurPlayerStandalone/state.json'
 def current_window():
  hwnd=find(None,'Shiur Player')
  if hwnd:
   value=ctypes.create_unicode_buffer(256);classname(hwnd,value,256)
   if not value.value.startswith('Tk'):
    text=ctypes.create_unicode_buffer(4096);dialogtext(hwnd,-1,text,len(text));raise AssertionError('Player startup dialog: '+text.value)
  return hwnd
 def await_window():
  deadline=time.monotonic()+25
  while time.monotonic()<deadline:
   hwnd=current_window()
   if hwnd:return hwnd
   time.sleep(.1)
  raise AssertionError('Installed app did not open its main window')
 def close_player():
  hwnd=current_window()
  if not hwnd:return
  pid=w.DWORD();pidof(hwnd,ctypes.byref(pid));handle=openprocess(0x100000,False,pid.value)
  try:
   assert post(hwnd,0x10,0,0)
   if handle:assert waitprocess(handle,15000)==0,'Player did not exit cleanly'
  finally:
   if handle:closehandle(handle)
 with tempfile.TemporaryDirectory() as temporary:
  setup=pathlib.Path(temporary)/'Setup.exe';setup.write_bytes(payload)
  def install():
   # Simulates an already-exited prior player process; avoids interactive setup prompts.
   process=subprocess.Popen([str(setup),'--update','2147483647'])
   try:assert process.wait(timeout=45)==0,'Setup failed'
   except subprocess.TimeoutExpired:
    value=ctypes.create_unicode_buffer(4096);dialogtext(find(None,'Shiur Player Setup'),-1,value,len(value))
    process.terminate();process.wait(timeout=5);raise AssertionError('Setup did not finish: '+value.value)
  try:
   install();hwnd=await_window();print('Native setup and packaged application startup passed',flush=True)
   assert json.loads((app/'active.json').read_text())['version']==version
   package=app/'versions'/version
   assert (package/'runtime/python/pythonw.exe').is_file()
   powershell="""$desktop=[Environment]::GetFolderPath('Desktop'); $shell=New-Object -ComObject Shell.Application; $item=$shell.NameSpace($desktop).ParseName('Shiur Player.lnk'); if (!$item) { throw 'Desktop shortcut is missing' }; $item.ExtendedProperty('System.AppUserModel.ID')"""
   result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',powershell],capture_output=True,text=True,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
   assert result.stdout.strip()=='ShiurPlayer.Standalone',repr(result.stdout)
   print('Installed shortcut taskbar identity verified',flush=True)
   duplicate=subprocess.Popen([str(package/'runtime/python/pythonw.exe'),'-I','-u',str(package/'main.py')],cwd=package)
   assert duplicate.wait(timeout=15)==0,'Duplicate runtime did not exit cleanly'
   assert current_window()==hwnd,'Duplicate runtime replaced the original main window'
   print('Actual duplicate-process guard verified',flush=True)
   close_player();state=json.loads(profile.read_text());state['tracks']['audit-retained-position']={'position':65.432,'duration':120,'speed':1.5}
   profile.write_text(json.dumps(state),encoding='utf-8')
   marker=package/'repair-test-marker.txt';marker.write_text('A program file which must disappear on clean repair')
   install();await_window();close_player()
   assert not marker.exists(),'Same-version installer did not replace existing program files'
   assert json.loads(profile.read_text())['tracks']['audit-retained-position']==state['tracks']['audit-retained-position']
   print('Native same-version repair and saved-position/speed preservation passed',flush=True)
  finally:close_player()

if __name__=='__main__':run()
