"""Floating transport behavior with Win32 calls mocked; a real Windows GUI is still required."""
import ctypes,importlib.util,pathlib,threading,unittest,unittest.mock,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('floating_bar',ROOT/'app/floating_bar.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class Function:
 def __init__(self,fn):self.fn=fn
 def __call__(self,*args):return self.fn(*args)
class TestBar(unittest.TestCase):
 def test_responsive_controls_fit_compact_and_large_clients(self):
  for width,height in [(284,100),(344,110),(600,240)]:
   bounds=module.layout(width,height)
   for ident,(x,y,w,h) in bounds.items():
    self.assertGreater(w,0);self.assertGreater(h,0);self.assertGreaterEqual(x,0);self.assertGreaterEqual(y,0)
    self.assertLessEqual(x+w,width);self.assertLessEqual(y+h,height)
   controls=[bounds[i] for i in (101,102,103,106)]
   for left,right in zip(controls,controls[1:]):self.assertLess(left[0]+left[2],right[0])
   self.assertLessEqual(controls[0][1]+controls[0][3],bounds[104][1])
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
    def __init__(self):self.commands=[];self.writes=0;self.state={'currentId':'a','skipSeconds':15,'status':'playing','speed':1};self.opens=0
    def show_window(self):self.opens+=1
    def snapshot(self):return self.state
    def command(self,cmd):
     self.commands.append(cmd);self.state['status']='paused'
     if cmd['op']=='speed_cycle':self.state['speed']=.5
    def persist(self):self.writes+=1
   player=Player();callbacks={};handles={};shows=[];texts=[];next_handle=10;messages=[(0x111,106),(0x111,105),(0x0005,0),(0x0232,0)]+[(0x113,0)]*10+[(0x111,102),(0x111,101),(0x111,103),(0x10,0),(0x8001,0),(0x8003,1),(0x8003,1),(0x8003,0)];registered_style=[];window_sizes=[];invalidations=[];moves=[];caption_updates=[]
   def register(pointer):callbacks['proc']=pointer._obj.proc;return 1
   def create(ex,name,title,style,x,y,width,height,parent,ident,instance,param):
    nonlocal next_handle
    next_handle+=1;handles[next_handle]=ident
    if not parent:registered_style.append(ex);window_sizes.append((width,height,style))
    return next_handle
   def message(pointer,*args):
    if not messages:return 0
    msg,wp=messages.pop(0);value=ctypes.cast(pointer,ctypes.POINTER(w.MSG)).contents;value.hWnd=11;value.message=msg;value.wParam=wp;value.lParam=0;return 1
   def dispatch(pointer):
    value=ctypes.cast(pointer,ctypes.POINTER(w.MSG)).contents;return callbacks['proc'](value.hWnd,value.message,value.wParam,value.lParam)
   def getrect(hwnd,pointer):
    rect=pointer._obj;rect.left=72;rect.top=96;rect.right=492;rect.bottom=276;return 1
   def clientrect(hwnd,pointer):
    rect=pointer._obj;rect.left=0;rect.top=0;rect.right=404;rect.bottom=140;return 1
   def settext(hwnd,text):texts.append(text);caption_updates.append((handles[hwnd],text));return 1
   user_funcs={'GetSystemMetrics':lambda index:{76:0,77:0,78:1920,79:1080}.get(index,0),'GetWindowRect':getrect,'GetClientRect':clientrect,'InvalidateRect':lambda hwnd,rect,erase:invalidations.append((hwnd,erase)) or 1,'MoveWindow':lambda hwnd,*args:moves.append((hwnd,args)) or 1,'RegisterClassW':register,'CreateWindowExW':create,'GetMessageW':message,'DispatchMessageW':dispatch,'ShowWindow':lambda hwnd,mode:shows.append(mode) or 1,'SetWindowTextW':settext,'LoadCursorW':lambda *args:1,'DefWindowProcW':lambda *args:0}
   class Library:
    def __init__(self,functions):self.functions=functions
    def __getattr__(self,name):value=Function(self.functions.get(name,lambda *args:1));setattr(self,name,value);return value
   libraries={'user32':Library(user_funcs),'gdi32':Library({}),'kernel32':Library({})}
   with unittest.mock.patch.object(module.ctypes,'WinDLL',side_effect=lambda name,**kwargs:libraries[name],create=True),unittest.mock.patch.object(module.ctypes,'WINFUNCTYPE',ctypes.CFUNCTYPE,create=True):
    bar=module.FloatingBar(player);bar.run()
   self.assertEqual(player.commands,[{'op':'speed_cycle'},{'op':'toggle'},{'op':'skip','direction':-1},{'op':'skip','direction':1}]);self.assertIn(0,shows);self.assertEqual(shows[-3:],[4,4,0]);self.assertFalse(player.saved['floatingVisible']);self.assertEqual(player.writes,6);self.assertIn('Current shiur',texts);self.assertEqual(registered_style[0]&0x08000088,0x08000088);self.assertEqual(bar.status,'ready')
   self.assertEqual(player.saved['floatingSize'],[420,180]);self.assertEqual(player.saved['floatingPosition'],[72,96]);self.assertEqual(player.opens,1)
   self.assertEqual(window_sizes[0][:2],module.DEFAULT_SIZE);self.assertTrue(window_sizes[0][2]&0x00040000)
   self.assertTrue(moves);self.assertEqual(len([i for i in invalidations if i[0]==11]),1);self.assertFalse(any(erase for _,erase in invalidations))
   self.assertEqual(len([c for c in caption_updates if c[0]==100]),1);self.assertEqual(len([c for c in caption_updates if c[0]==104]),1)
   self.assertIn((106,'0.5x'),caption_updates)
if __name__=='__main__':unittest.main(verbosity=2)
