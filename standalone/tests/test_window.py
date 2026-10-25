"""Real native window callbacks exercised through mock Win32 APIs."""
import ctypes,pathlib,sys,unittest,unittest.mock
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'app'))
from window import PlayerWindow
import test_player
class Function:
 def __init__(self,fn):self.fn=fn
 def __call__(self,*args):return self.fn(*args)
class Tests(unittest.TestCase):
 def test_play_bookmark_collection_and_close(self):
  from ctypes import wintypes as w
  fixture=test_player.Tests();fixture.setUp();player=fixture.player;library=fixture.library
  callbacks={};handles={};next_handle=10;shown=[];destroyed=[];captions=[]
  messages=[(0x111,203),(0x111,230),(0x111,220),(0x111,223),(0x10,0)]
  def register(pointer):callbacks['proc']=pointer._obj.proc;return 1
  def create(ex,cls,title,style,x,y,width,height,parent,ident,*_):
   nonlocal next_handle
   next_handle+=1;handles[next_handle]={'id':ident,'text':title,'items':[],'selected':-1,'position':0};return next_handle
  def send(hwnd,msg,wp,lp):
   control=handles.get(hwnd,{})
   if msg in (0x014B,0x0184):control['items']=[];control['selected']=-1
   elif msg in (0x0143,0x0180):control['items'].append(ctypes.cast(lp,ctypes.c_wchar_p).value)
   elif msg in (0x014E,0x0186):control['selected']=wp
   elif msg in (0x0147,0x0188):return control.get('selected',-1)
   elif msg==0x0405:control['position']=lp
   elif msg==0x0400:return control.get('position',0)
   return 1
  def getmessage(pointer,*_):
   player.tick()
   if not messages:return 0
   msg,wp=messages.pop(0)
   if msg==0x10:fixture.backend.position=41.123
   value=ctypes.cast(pointer,ctypes.POINTER(w.MSG)).contents;value.hWnd=11;value.message=msg;value.wParam=wp;value.lParam=0;return 1
  def dispatch(pointer):
   value=ctypes.cast(pointer,ctypes.POINTER(w.MSG)).contents;return callbacks['proc'](value.hWnd,value.message,value.wParam,value.lParam)
  def settext(hwnd,value):handles[hwnd]['text']=value;captions.append(value);return 1
  def field(hwnd):
   ident=handles[hwnd]['id'];return 'Review' if ident==233 else 'My series' if ident==226 else handles[hwnd]['text']
  def gettext(hwnd,buffer,size):buffer.value=field(hwnd)[:size-1];return len(buffer.value)
  def destroy(hwnd):destroyed.append(hwnd);callbacks['proc'](hwnd,2,0,0);return 1
  class Library:
   def __init__(self,mapping):self.mapping=mapping
   def __getattr__(self,name):fn=Function(self.mapping.get(name,lambda *_:1));setattr(self,name,fn);return fn
  functions={'RegisterClassW':register,'CreateWindowExW':create,'GetMessageW':getmessage,'DispatchMessageW':dispatch,'SendMessageW':send,'SetWindowTextW':settext,'GetWindowTextLengthW':lambda hwnd:len(field(hwnd)),'GetWindowTextW':gettext,'DestroyWindow':destroy,'ShowWindow':lambda hwnd,mode:shown.append(mode) or 1,'GetSystemMetrics':lambda i:1280 if i==0 else 800,'IsDialogMessageW':lambda *_:0,'MessageBoxW':lambda *_:6}
  libs={'user32':Library(functions),'gdi32':Library({}),'kernel32':Library({}),'comctl32':Library({})}
  try:
   with unittest.mock.patch.object(ctypes,'WinDLL',side_effect=lambda name,**_:libs[name],create=True),unittest.mock.patch.object(ctypes,'WINFUNCTYPE',ctypes.CFUNCTYPE,create=True):PlayerWindow(player,library,lambda _:None).run()
   self.assertEqual(shown,[5]);self.assertEqual(destroyed,[11]);self.assertIn('Shiur Player',captions);self.assertEqual(player.error,'')
   self.assertEqual(player.saved['language'],'en');self.assertEqual(len(library.bookmarks()),1);self.assertEqual(len(player.saved['folders'][0]['trackIds']),1)
   self.assertEqual(player.saved['tracks'][player.saved['currentId']]['position'],41.123)
  finally:fixture.tearDown()
if __name__=='__main__':unittest.main(verbosity=2)
