"""Windows RegisterHotKey integration, independent of browser focus. No keyboard hook or typing capture."""
import ctypes,json,pathlib,sys,threading
DEFAULTS={
 'toggle':{'key':'P','action':{'op':'toggle'}},
 'back':{'key':'LEFT','action':{'op':'skip','direction':-1}},
 'forward':{'key':'RIGHT','action':{'op':'skip','direction':1}},
 'slower':{'key':'DOWN','action':{'op':'speed_step','direction':-1}},
 'faster':{'key':'UP','action':{'op':'speed_step','direction':1}},
 'previous':{'key':'PAGEUP','action':{'op':'previous'}},
 'next':{'key':'PAGEDOWN','action':{'op':'next'}},
 'skip10':{'key':'1','action':{'op':'skip_interval','value':10}},
 'skip15':{'key':'2','action':{'op':'skip_interval','value':15}},
 'skip60':{'key':'3','action':{'op':'skip_interval','value':60}},
 'stop':{'key':'S','action':{'op':'stop'}},
 'floating':{'key':'F','action':{'op':'floating_toggle'}},
}
KEYS={'LEFT':0x25,'UP':0x26,'RIGHT':0x27,'DOWN':0x28,'PAGEUP':0x21,'PAGEDOWN':0x22,'SPACE':0x20,**{chr(i):i for i in range(65,91)},**{str(i):48+i for i in range(10)}}
MODS={'ALT':1,'CTRL':2,'SHIFT':4,'WIN':8}
def bindings(config):
 result=[];used=set()
 if not isinstance(config,dict):raise ValueError('hotkeys.json must contain an object.')
 for name,spec in DEFAULTS.items():
  value=config.get(name,{'modifiers':['CTRL','ALT','SHIFT'],'key':spec['key']})
  if value is None:continue
  if not isinstance(value,dict):raise ValueError('Invalid shortcut: '+name)
  modifiers=value.get('modifiers',[]);key=str(value.get('key','')).upper()
  if not isinstance(modifiers,list) or len(set(modifiers))<2 or any(m not in MODS for m in modifiers) or key not in KEYS:raise ValueError('Use at least two modifiers and a supported key for '+name)
  flags=0
  for modifier in modifiers:flags|=MODS[modifier]
  chord=(flags,KEYS[key])
  if chord in used:raise ValueError('Duplicate shortcut: '+name)
  used.add(chord);result.append((name,flags,KEYS[key],'+'.join(modifiers+[key]),spec['action']))
 return result
class GlobalHotkeys:
 def __init__(self,player):self.player=player;self.thread=None;self.thread_id=None;self.ready=threading.Event()
 def start(self):
  if sys.platform!='win32':
   self.player.hotkey_status=[{'name':'platform','registered':False,'error':'System-wide shortcuts are implemented for Windows only.'}];return
  self.thread=threading.Thread(target=self.run,name='shiur-global-hotkeys',daemon=True);self.thread.start();self.ready.wait(3)
 def run(self):
  from ctypes import wintypes
  user=ctypes.WinDLL('user32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
  user.RegisterHotKey.argtypes=[wintypes.HWND,ctypes.c_int,wintypes.UINT,wintypes.UINT];user.RegisterHotKey.restype=wintypes.BOOL
  user.UnregisterHotKey.argtypes=[wintypes.HWND,ctypes.c_int];user.UnregisterHotKey.restype=wintypes.BOOL
  user.GetMessageW.argtypes=[ctypes.POINTER(wintypes.MSG),wintypes.HWND,wintypes.UINT,wintypes.UINT];user.GetMessageW.restype=ctypes.c_int
  user.PeekMessageW.argtypes=[ctypes.POINTER(wintypes.MSG),wintypes.HWND,wintypes.UINT,wintypes.UINT,wintypes.UINT];user.PeekMessageW.restype=wintypes.BOOL
  kernel.GetCurrentThreadId.restype=wintypes.DWORD
  message=wintypes.MSG();user.PeekMessageW(ctypes.byref(message),None,0,0,0);self.thread_id=kernel.GetCurrentThreadId()
  active={};statuses=[]
  try:
   path=self.player.data_dir/'hotkeys.json'
   if not path.exists():path.write_text(json.dumps({name:{'modifiers':['CTRL','ALT','SHIFT'],'key':item['key']} for name,item in DEFAULTS.items()},indent=2),'utf-8')
   config=json.loads(path.read_text('utf-8'));items=bindings(config)
   for index,(name,mods,key,label,action) in enumerate(items,1):
    ok=bool(user.RegisterHotKey(None,index,mods|0x4000,key));statuses.append({'name':name,'label':label,'registered':ok,'error':'' if ok else f'Shortcut unavailable (Windows error {ctypes.get_last_error()}).'})
    if ok:active[index]=action
   with self.player.lock:self.player.hotkey_status=statuses
   for status in statuses:print(('Shortcut: ' if status['registered'] else 'Shortcut conflict: ')+status['label'],flush=True)
   self.ready.set()
   while True:
    result=user.GetMessageW(ctypes.byref(message),None,0,0)
    if result<=0:break
    if message.message==0x0312 and message.wParam in active:
     try:self.player.command(active[message.wParam])
     except Exception as e:
      with self.player.lock:self.player.error=str(e)
  except Exception as e:
   with self.player.lock:self.player.hotkey_status=[{'name':'configuration','registered':False,'error':str(e)}]
   print('Global shortcuts unavailable: '+str(e),flush=True)
  finally:
   self.ready.set()
   for ident in active:user.UnregisterHotKey(None,ident)
 def close(self):
  if self.thread_id:
   from ctypes import wintypes
   user=ctypes.WinDLL('user32',use_last_error=True);user.PostThreadMessageW.argtypes=[wintypes.DWORD,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM];user.PostThreadMessageW.restype=wintypes.BOOL
   user.PostThreadMessageW(self.thread_id,0x0012,0,0)
  if self.thread:self.thread.join(timeout=3)
