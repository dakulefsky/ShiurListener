"""Exercise real native window callbacks with mocked Win32 APIs."""
import ctypes,importlib.util,pathlib,tempfile,threading,unittest,unittest.mock
from test_floating_bar import Function
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('desktop',ROOT/'companion/desktop.py');desktop=importlib.util.module_from_spec(spec);spec.loader.exec_module(desktop)
class Tests(unittest.TestCase):
 def test_hide_reopen_language_copy_rescan_exit(self):
  from ctypes import wintypes as w
  class Player:
   saved={'language':'he'};root=pathlib.Path('recordings');tracks=[{'id':'a'}];error='';lock=threading.RLock();floating_bar=None
   def __init__(self):self.commands=[];self.scans=0
   def command(self,data):self.commands.append(data);self.saved['language']=data['value']
   def scan(self):self.scans+=1
  player=Player();callbacks={};shown=[];texts=[];clipboard=[];destroyed=[];handles=iter(range(10,80));messages=[(0x800E,0),(0x800B,0),(0x111,(1<<16)|106),(0x111,103),(0x111,102),(0x111,104)]
  def register(pointer):callbacks['proc']=pointer._obj.proc;return 1
  def getmessage(pointer,*_):
   if not messages:return 0
   msg,wp=messages.pop(0);value=ctypes.cast(pointer,ctypes.POINTER(w.MSG)).contents;value.hWnd=10;value.message=msg;value.wParam=wp;value.lParam=0;return 1
  def dispatch(pointer):
   value=ctypes.cast(pointer,ctypes.POINTER(w.MSG)).contents;return callbacks['proc'](value.hWnd,value.message,value.wParam,value.lParam)
  def send(hwnd,msg,wp,lp):
   if msg==0x301:clipboard.append(hwnd)
   return 1
  def destroy(hwnd):destroyed.append(hwnd);callbacks['proc'](hwnd,0x2,0,0);return 1
  class Library:
   def __init__(self,functions):self.functions=functions
   def __getattr__(self,name):fn=Function(self.functions.get(name,lambda *_:1));setattr(self,name,fn);return fn
  functions={'RegisterClassW':register,'CreateWindowExW':lambda *_:next(handles),'GetMessageW':getmessage,'IsDialogMessageW':lambda *_:0,'DispatchMessageW':dispatch,'ShowWindow':lambda hwnd,mode:shown.append(mode) or 1,'SetWindowTextW':lambda hwnd,text:texts.append(text) or 1,'SendMessageW':send,'DestroyWindow':destroy}
  libraries={'user32':Library(functions),'gdi32':Library({}),'kernel32':Library({})}
  with unittest.mock.patch.object(ctypes,'WinDLL',side_effect=lambda name,**_:libraries[name],create=True),unittest.mock.patch.object(ctypes,'WINFUNCTYPE',ctypes.CFUNCTYPE,create=True):
   desktop.DesktopWindow(player,'pair-code').run()
  self.assertEqual(shown,[5,0,9]);self.assertEqual(destroyed,[10]);self.assertEqual(len(clipboard),1);self.assertEqual(player.scans,1)
  self.assertEqual(player.commands,[{'op':'language','value':'en'}]);self.assertIn('Shiur Player',texts);self.assertIn('נגן שיעורים',texts)
  self.assertIsNone(player.hide_window);self.assertIsNone(player.show_window);self.assertIsNone(player.choose_folder)
if __name__=='__main__':unittest.main(verbosity=2)
