"""Real Win32 floating window and injected mouse clicks; Windows desktop required.
Temporarily moves the pointer over the test window, then restores it.
"""
import ctypes,pathlib,sys,time,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'app'))
import test_player
from floating_bar import FloatingBar,layout,COLLAPSED_SIZE,HOVER_SIZE

@unittest.skipUnless(sys.platform=='win32','Requires a real Windows desktop')
class NativeWindowTests(unittest.TestCase):
 def test_actual_mouse_controls_expanded_collapsed_and_hover(self):
  from ctypes import wintypes as w
  fixture=test_player.Tests();fixture.setUp();bar=None
  user=ctypes.WinDLL('user32',use_last_error=True)
  def bind(name,result,args):
   fn=getattr(user,name);fn.restype=result;fn.argtypes=args;return fn
  rect=bind('GetClientRect',w.BOOL,[w.HWND,ctypes.POINTER(w.RECT)])
  to_client=bind('ScreenToClient',w.BOOL,[w.HWND,ctypes.POINTER(w.POINT)])
  screen=bind('ClientToScreen',w.BOOL,[w.HWND,ctypes.POINTER(w.POINT)])
  cursor=bind('GetCursorPos',w.BOOL,[ctypes.POINTER(w.POINT)])
  move=bind('SetCursorPos',w.BOOL,[ctypes.c_int,ctypes.c_int])
  child=bind('GetDlgItem',w.HWND,[w.HWND,ctypes.c_int])
  point_window=bind('WindowFromPoint',w.HWND,[w.POINT])
  windowrect=bind('GetWindowRect',w.BOOL,[w.HWND,ctypes.POINTER(w.RECT)])
  position=bind('SetWindowPos',w.BOOL,[w.HWND,w.HWND,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,w.UINT])
  metric=bind('GetSystemMetrics',ctypes.c_int,[ctypes.c_int])
  visible=bind('IsWindowVisible',w.BOOL,[w.HWND])
  sendmouse=bind('mouse_event',None,[w.DWORD,w.DWORD,w.DWORD,w.DWORD,ctypes.c_size_t])
  original=w.POINT();cursor(ctypes.byref(original))
  def wait(predicate,label):
   deadline=time.monotonic()+5
   while time.monotonic()<deadline:
    if predicate():return
    time.sleep(.03)
   self.fail(label+'; mini status='+str(bar.status)+'; player error='+str(fixture.player.error))
  def size():
   value=w.RECT();self.assertTrue(rect(bar.hwnd,ctypes.byref(value)));return value.right,value.bottom
  def settled():
   width,height=size();collapsed=bool(fixture.player.saved.get('floatingCollapsed',False))
   hovered=collapsed and width>=HOVER_SIZE[0]
   for leftward in ([False,True] if hovered else [False]):
    expected=layout(width,height,collapsed,hovered,leftward,player.saved.get('floatingCollapsedSize',list(COLLAPSED_SIZE))[0]);matches=True
    for ident in range(100,109):
     handle=child(bar.hwnd,ident)
     if not handle or bool(visible(handle))!=(ident in expected):matches=False;break
     if ident in expected:
      value=w.RECT();windowrect(handle,ctypes.byref(value));point=w.POINT(value.left,value.top);to_client(bar.hwnd,ctypes.byref(point))
      actual=(point.x,point.y,value.right-value.left,value.bottom-value.top)
      if actual!=expected[ident]:matches=False;break
    if matches:return True
   return False
  def click(ident):
   wait(settled,'Control layout did not finish updating')
   expected=child(bar.hwnd,ident);self.assertTrue(expected);self.assertTrue(visible(expected))
   value=w.RECT();self.assertTrue(rect(expected,ctypes.byref(value)))
   point=w.POINT(value.right//2,value.bottom//2)
   self.assertTrue(screen(expected,ctypes.byref(point)))
   self.assertTrue(move(point.x,point.y));time.sleep(.04)
   if ident!=107:self.assertEqual(point_window(point),expected,'Mouse target must be the real button')
   sendmouse(0x0002,0,0,0,0)
   try:time.sleep(.03)
   finally:sendmouse(0x0004,0,0,0,0)
  try:
   player=fixture.player;ident=player.tracks[0]['id'];player.load(ident,position=30,autoplay=False);player.tick()
   opened=[];player.show_window=lambda:opened.append(True)
   bar=FloatingBar(player);player.floating_bar=bar;bar.start()
   self.assertTrue(bar.hwnd,bar.status);bar.set_visible(True);wait(lambda:visible(bar.hwnd),'Mini player did not become visible')
   click(102);wait(lambda:fixture.backend.status=='playing','Expanded play failed')
   click(101);wait(lambda:fixture.backend.position==15,'Expanded backward skip failed')
   click(103);wait(lambda:fixture.backend.position==30,'Expanded forward skip failed')
   click(106);wait(lambda:player.saved['speed']==1.5,'Expanded speed failed')
   click(105);wait(lambda:bool(opened),'Open main-window control failed')
   click(108);wait(lambda:size()[0]==COLLAPSED_SIZE[0],'Collapse failed')
   click(102);wait(lambda:fixture.backend.status=='paused','Collapsed pause failed')
   width,height=size();point=w.POINT(40,20);screen(bar.hwnd,ctypes.byref(point));move(point.x,point.y)
   wait(lambda:size()[0]==HOVER_SIZE[0],'Hover did not reveal skips')
   click(101);wait(lambda:fixture.backend.position==15,'Hover backward skip failed')
   click(103);wait(lambda:fixture.backend.position==30,'Hover forward skip failed')
   move(1,1);wait(lambda:size()[0]==COLLAPSED_SIZE[0],'Hover did not retract')
   click(108);wait(lambda:not player.saved['floatingCollapsed'],'Expand failed')
   click(107);wait(lambda:abs(fixture.backend.position-60)<2,'Seek failed')
   click(108);wait(lambda:size()[0]==COLLAPSED_SIZE[0],'Second collapse failed')
   move(1,1);wait(lambda:size()[0]==COLLAPSED_SIZE[0],'Tiny mode did not settle')
   position(bar.hwnd,None,metric(0)-COLLAPSED_SIZE[0],80,*COLLAPSED_SIZE,0x14)
   base=w.RECT();windowrect(bar.hwnd,ctypes.byref(base))
   play=w.POINT(38,16);screen(child(bar.hwnd,102),ctypes.byref(play));move(play.x,play.y)
   wait(lambda:size()[0]==HOVER_SIZE[0],'Screen-edge hover failed');wait(settled,'Screen-edge layout did not settle')
   anchored=w.POINT(38,16);screen(child(bar.hwnd,102),ctypes.byref(anchored))
   self.assertEqual((play.x,play.y),(anchored.x,anchored.y),'Hover must not move play/pause away from the pointer')
   click(102);wait(lambda:fixture.backend.status=='playing','Screen-edge play failed')
   move(1,1);wait(lambda:size()[0]==COLLAPSED_SIZE[0],'Screen-edge hover did not retract')
   restored=w.RECT();windowrect(bar.hwnd,ctypes.byref(restored));self.assertEqual(restored.left,base.left)
  finally:
   sendmouse(0x0004,0,0,0,0)
   if bar:bar.close()
   move(original.x,original.y);fixture.tearDown()
