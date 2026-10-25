"""Floating transport behavior with Win32 calls mocked; a real Windows GUI is still required."""
import ctypes,importlib.util,pathlib,threading,unittest,unittest.mock,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('floating_bar',ROOT/'app/floating_bar.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class Function:
 def __init__(self,fn):self.fn=fn
 def __call__(self,*args):return self.fn(*args)
class TestBar(unittest.TestCase):
 def test_labels_and_colors(self):
  state={'currentId':'a','skipSeconds':60,'status':'playing'}
  self.assertEqual(module.display(state,[{'id':'a','name':'Shiur'}]),('Shiur','Pause','−60','+60'))
  self.assertEqual(module.timing({'position':3661,'duration':7200,'speed':1.5}),'1:01:01 / 2:00:00  ·  1.5×')
  self.assertEqual(module.color('#123456','#000000'),0x563412)
  self.assertEqual(module.color('bad','#ffffff'),0xffffff)
 def test_native_transport_and_hiding(self):
  from ctypes import wintypes as w
  with tempfile.TemporaryDirectory() as tmp:
   class Player:
    data_dir=pathlib.Path(tmp);lock=threading.RLock();saved={};tracks=[{'id':'a','name':'Current shiur'}];error=''
    def __init__(self):self.commands=[];self.writes=0;self.state={'currentId':'a','skipSeconds':15,'status':'playing'}
    def snapshot(self):return self.state
    def command(self,cmd):self.commands.append(cmd);self.state['status']='paused'
    def persist(self):self.writes+=1
   player=Player();callbacks={};handles={};shows=[];texts=[];next_handle=10;messages=[(0x111,102),(0x111,101),(0x111,103),(0x10,0),(0x8001,0),(0x8003,1),(0x8003,1),(0x8003,0)];registered_style=[]
   def register(pointer):callbacks['proc']=pointer._obj.proc;return 1
   def create(ex,name,title,style,x,y,width,height,parent,ident,instance,param):
    nonlocal next_handle
    next_handle+=1;handles[next_handle]=ident
    if not parent:registered_style.append(ex)
    return next_handle
   def message(pointer,*args):
    if not messages:return 0
    msg,wp=messages.pop(0);value=ctypes.cast(pointer,ctypes.POINTER(w.MSG)).contents;value.hWnd=11;value.message=msg;value.wParam=wp;value.lParam=0;return 1
   def dispatch(pointer):
    value=ctypes.cast(pointer,ctypes.POINTER(w.MSG)).contents;return callbacks['proc'](value.hWnd,value.message,value.wParam,value.lParam)
   user_funcs={'RegisterClassW':register,'CreateWindowExW':create,'GetMessageW':message,'DispatchMessageW':dispatch,'ShowWindow':lambda hwnd,mode:shows.append(mode) or 1,'SetWindowTextW':lambda hwnd,text:texts.append(text) or 1,'LoadCursorW':lambda *args:1,'DefWindowProcW':lambda *args:0}
   class Library:
    def __init__(self,functions):self.functions=functions
    def __getattr__(self,name):value=Function(self.functions.get(name,lambda *args:1));setattr(self,name,value);return value
   libraries={'user32':Library(user_funcs),'gdi32':Library({}),'kernel32':Library({})}
   with unittest.mock.patch.object(module.ctypes,'WinDLL',side_effect=lambda name,**kwargs:libraries[name],create=True),unittest.mock.patch.object(module.ctypes,'WINFUNCTYPE',ctypes.CFUNCTYPE,create=True):
    bar=module.FloatingBar(player);bar.run()
   self.assertEqual(player.commands,[{'op':'toggle'},{'op':'skip','direction':-1},{'op':'skip','direction':1}]);self.assertIn(0,shows);self.assertEqual(shows[-3:],[4,4,0]);self.assertFalse(player.saved['floatingVisible']);self.assertEqual(player.writes,5);self.assertIn('Current shiur',texts);self.assertEqual(registered_style[0]&0x08000088,0x08000088);self.assertEqual(bar.status,'ready')
if __name__=='__main__':unittest.main(verbosity=2)
