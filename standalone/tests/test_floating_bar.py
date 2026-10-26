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
   self.assertLessEqual(bounds[104][1]+bounds[104][3],bounds[107][1])
 def test_frameless_edges_resize_and_empty_surface_drags(self):
  self.assertFalse(module.FRAMELESS_STYLE & 0x00C00000)
  for point,target in [((1,1),13),((359,1),14),((1,149),16),((359,149),17),((1,50),10),((359,50),11),((80,1),12),((80,149),15),((80,20),2)]:
   self.assertEqual(module.hit_test(*point,360,150),target)
  self.assertEqual(module.hit_test(1,1,144,44,collapsed=True),2)
 def test_buttons_are_client_targets_not_window_drag_targets(self):
  for width,height,collapsed,hovered in [(360,150,False,False),(144,44,True,False),(252,44,True,True)]:
   for ident,(x,y,w,h) in module.layout(width,height,collapsed,hovered).items():
    if ident in (101,102,103,105,106,107,108,109):
     self.assertEqual(module.hit_test(x+w//2,y+h//2,width,height,collapsed,hovered),1,f'Control {ident} must receive clicks')
   self.assertEqual(module.hit_test(8,20,width,height,collapsed,hovered),2)
 def test_hover_waits_for_intent_and_ignores_brief_crossings(self):
  intent=module.HoverIntent()
  self.assertFalse(intent.update(True,0))
  self.assertFalse(intent.update(False,.1))
  self.assertFalse(intent.update(True,.15))
  self.assertTrue(intent.update(True,.4))
  self.assertTrue(intent.update(False,.5))
  self.assertTrue(intent.update(True,.7))
  self.assertTrue(intent.update(False,.8))
  self.assertFalse(intent.update(False,1.3))
 def test_hover_never_changes_layout_during_click_or_drag(self):
  intent=module.HoverIntent()
  intent.update(True,0)
  self.assertFalse(intent.update(True,1,blocked=True))
  self.assertFalse(intent.update(True,2))
  self.assertTrue(intent.update(True,2.3))
  intent.update(False,3)
  self.assertTrue(intent.update(False,4,blocked=True))
  self.assertTrue(intent.update(False,5))
  self.assertFalse(intent.update(False,5.5))
 def test_leftward_hover_preserves_original_button_screen_positions(self):
  original=module.layout(144,44,True,False)
  expanded=module.layout(252,44,True,True,True)
  shift=module.HOVER_SIZE[0]-module.COLLAPSED_SIZE[0]
  for ident in (102,108,109):
   self.assertEqual(expanded[ident][0]-shift,original[ident][0])
  for ident,(x,y,width,height) in expanded.items():
   self.assertEqual(module.hit_test(x+width//2,y+height//2,252,44,True,True,True),1)
 def test_labels_and_colors(self):
  state={'currentId':'a','skipSeconds':60,'status':'playing'}
  self.assertEqual(module.display(state,[{'id':'a','name':'Shiur'}]),('Shiur','Pause','−60','+60'))
  self.assertEqual(module.timing({'position':3661,'duration':7200,'speed':1.5}),'1:01:01  ·  58:59 left  ·  1.5×')
  self.assertEqual(module.timing({'position':5,'duration':0},False),'0:05')
  self.assertEqual(module.color('#123456','#000000'),0x563412)
  self.assertEqual(module.color('bad','#ffffff'),0xffffff)
 def test_collapse_and_expand_preserve_transport_and_expanded_size(self):
  self.test_native_transport_and_hiding(collapse=True)
 def test_hover_reveals_skip_and_leaving_collapses_again(self):
  self.test_native_transport_and_hiding(collapse=True,hover=True)
 def test_close_button_hides_without_playback_commands(self):
  self.test_native_transport_and_hiding(close_button=True)
 def test_native_transport_and_hiding(self,collapse=False,hover=False,close_button=False):
  from ctypes import wintypes as w
  with tempfile.TemporaryDirectory() as tmp:
   class Player:
    data_dir=pathlib.Path(tmp);lock=threading.RLock();saved={};tracks=[{'id':'a','name':'Current shiur'}];error=''
    def __init__(self):self.commands=[];self.writes=0;self.state={'currentId':'a','skipSeconds':15,'status':'playing','speed':1,'position':90,'duration':360};self.opens=0
    def show_window(self):self.opens+=1
    def snapshot(self):return self.state
    def command(self,cmd):
     self.commands.append(cmd);self.state['status']='paused'
     if cmd['op']=='speed_cycle':self.state['speed']=1.5
     if cmd['op']=='seek':self.state['position']=cmd['value']
    def persist(self):self.writes+=1
   player=Player();callbacks={};handles={};shows=[];texts=[];next_handle=10;messages=[(0x111,106),(0x111,105),(0x0005,0),(0x0232,0)]+[(0x113,0)]*10+[(0x111,107),(0x111,102),(0x111,101),(0x111,103),(0x10,0),(0x8001,0),(0x8003,1),(0x8003,1),(0x8003,0)];registered_style=[];window_sizes=[];invalidations=[];moves=[];caption_updates=[];bounds={};idle_checks=[]
   if close_button:messages[messages.index((0x10,0))]=(0x111,109)
   messages.append((0x000F,0))
   messages.extend((0x002B,ident) for ident in (102,105,108,109,106,107))
   mode_sizes=[];position_flags=[];paint_calls=[]
   if collapse:messages[14:14]=[(0x111,108),(0x0232,0),(0x111,108)]
   cursor_reads=[];cursor_position=[0,0];fake_clock=[0.]
   if hover:messages[15:15]=[(0x8003,1)]+[(0x113,n) for n in range(1,8)]
   def getcursor(pointer):
    cursor_reads.append(1);pointer._obj.x,pointer._obj.y=cursor_position;return 1
   def register(pointer):callbacks['proc']=pointer._obj.proc;return 1
   def create(ex,name,title,style,x,y,width,height,parent,ident,instance,param):
    nonlocal next_handle
    next_handle+=1;handles[next_handle]=ident
    if not parent:registered_style.append(ex);window_sizes.append((width,height,style))
    return next_handle
   def message(pointer,*args):
    if not messages:
     for ident,(x,y,width,height) in module.layout(404,140).items():
      if ident in (101,102,103,105,106,107,108,109):
       packed=((96+y+height//2)&0xffff)<<16 | ((72+x+width//2)&0xffff)
       self.assertEqual(callbacks['proc'](11,0x0084,0,packed),1,f'Native control {ident} must be clickable')
     return 0
    msg,wp=messages.pop(0)
    if msg==0x113 and wp:
     fake_clock[0]=wp*.25;cursor_position[:]=[80,100] if wp<=3 else [0,0]
    if msg==0x113:idle_checks.append((len(invalidations),len(caption_updates)))
    value=ctypes.cast(pointer,ctypes.POINTER(w.MSG)).contents;value.hWnd=11;value.message=msg;value.wParam=wp;value.lParam=0;return 1
   class DrawItem(ctypes.Structure):
    _fields_=[('type',w.UINT),('id',w.UINT),('item',w.UINT),('action',w.UINT),('state',w.UINT),('hwnd',w.HWND),('dc',w.HDC),('rect',w.RECT),('data',ctypes.c_size_t)]
   def dispatch(pointer):
    value=ctypes.cast(pointer,ctypes.POINTER(w.MSG)).contents
    if value.message==0x002B:
     item=DrawItem();item.id=value.wParam;item.dc=1;item.rect=w.RECT(0,0,76,32);value.lParam=ctypes.addressof(item)
     return callbacks['proc'](value.hWnd,value.message,value.wParam,value.lParam)
    return callbacks['proc'](value.hWnd,value.message,value.wParam,value.lParam)
   def getrect(hwnd,pointer):
    rect=pointer._obj;rect.left=72;rect.top=96;rect.right=492;rect.bottom=276;return 1
   def clientrect(hwnd,pointer):
    rect=pointer._obj;rect.left=0;rect.top=0;rect.right=bounds.get(hwnd,(0,0,404,140))[2];rect.bottom=bounds.get(hwnd,(0,0,404,140))[3];return 1
   def move(hwnd,x,y,width,height,repaint):bounds[hwnd]=(x,y,width,height);moves.append((hwnd,(x,y,width,height,repaint)));return 1
   def screenclient(hwnd,pointer):pointer._obj.x=bounds.get(hwnd,(0,0,404,140))[2]//2;pointer._obj.y=4;return 1
   def settext(hwnd,text):texts.append(text);caption_updates.append((handles[hwnd],text));return 1
   user_funcs={'GetCursorPos':getcursor,'BeginPaint':lambda *args:paint_calls.append('begin') or 1,'EndPaint':lambda *args:paint_calls.append('end') or 1,'SetWindowPos':lambda hwnd,after,x,y,width,height,flags:(mode_sizes.append((width,height)),position_flags.append(flags),1)[2],'GetSystemMetrics':lambda index:{76:0,77:0,78:1920,79:1080}.get(index,0),'GetWindowRect':getrect,'GetClientRect':clientrect,'ScreenToClient':screenclient,'InvalidateRect':lambda hwnd,rect,erase:invalidations.append((hwnd,erase)) or 1,'MoveWindow':move,'RegisterClassW':register,'CreateWindowExW':create,'GetMessageW':message,'DispatchMessageW':dispatch,'ShowWindow':lambda hwnd,mode:shows.append(mode) or 1,'SetWindowTextW':settext,'LoadCursorW':lambda *args:1,'DefWindowProcW':lambda *args:0}
   class Library:
    def __init__(self,functions):self.functions=functions
    def __getattr__(self,name):value=Function(self.functions.get(name,lambda *args:1));setattr(self,name,value);return value
   libraries={'user32':Library(user_funcs),'gdi32':Library({}),'kernel32':Library({}),'dwmapi':Library({})}
   with unittest.mock.patch.object(module.time,'monotonic',side_effect=lambda:fake_clock[0]),unittest.mock.patch.object(module.ctypes,'WinDLL',side_effect=lambda name,**kwargs:libraries[name],create=True),unittest.mock.patch.object(module.ctypes,'WINFUNCTYPE',ctypes.CFUNCTYPE,create=True):
    bar=module.FloatingBar(player);bar.run()
   self.assertEqual(player.commands,[{'op':'speed_cycle'},{'op':'seek','value':180.0},{'op':'toggle'},{'op':'skip','direction':-1},{'op':'skip','direction':1}]);self.assertIn(0,shows);self.assertEqual(shows[-3:],[4,4,0]);self.assertFalse(player.saved['floatingVisible']);self.assertEqual(player.writes,10 if hover else 9 if collapse else 6);self.assertIn('Current shiur',texts);self.assertEqual(registered_style[0]&0x08000088,0x08000088);self.assertEqual(bar.status,'ready')
   self.assertEqual(player.saved['floatingSize'],[420,180]);self.assertEqual(player.saved['floatingPosition'],[72,96]);self.assertEqual(player.opens,1)
   self.assertEqual(window_sizes[0][:2],module.DEFAULT_SIZE);self.assertTrue(window_sizes[0][2]&0x00040000)
   self.assertTrue(moves);self.assertEqual(len([i for i in invalidations if i[0]==11]),5 if hover else 3 if collapse else 1);self.assertFalse(any(erase for _,erase in invalidations))
   self.assertEqual(len([c for c in caption_updates if c[0]==100]),1);self.assertEqual(len([c for c in caption_updates if c[0]==104]),2)
   if not hover:self.assertEqual(len(set(idle_checks[1:])),1,'Idle timer ticks must not repaint the strip or rewrite captions.')
   self.assertIn((106,'1.5x'),caption_updates)
   self.assertEqual(player.error,'','Native drawing and message handlers must not raise')
   self.assertEqual(paint_calls,['begin','end'])
   if hover:self.assertEqual(position_flags,[0x34,0x14,0x14,0x34], 'Hover must not rebuild the native window frame')
   if collapse:
    self.assertEqual(mode_sizes,[module.COLLAPSED_SIZE,module.HOVER_SIZE,module.COLLAPSED_SIZE,(420,180)] if hover else [module.COLLAPSED_SIZE,(420,180)])
    self.assertFalse(player.saved['floatingCollapsed'])
    self.assertIn((108,'↗'),caption_updates)
    self.assertEqual(set(module.layout(*module.COLLAPSED_SIZE,collapsed=True)),{102,108,109})
if __name__=='__main__':unittest.main(verbosity=2)

