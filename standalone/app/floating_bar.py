"""Compact, resizable Win32 transport; only changed controls are repainted."""
import ctypes,sys,threading,pathlib

MIN_SIZE=(300,140)
DEFAULT_SIZE=(360,150)
COLLAPSED_SIZE=(144,44)

def display(state,tracks):
 track=next((t for t in tracks if t['id']==state['currentId']),None)
 title=track['name'] if track else 'Choose a recordings folder'
 n=state.get('skipSeconds',15)
 return title,('Pause' if state['status']=='playing' or state.get('playRequested') else 'Play'),f'−{n}',f'+{n}'

def timing(state,include_speed=True):
 def fmt(value):
  value=max(0,int(value));return f'{value//3600}:{value%3600//60:02}:{value%60:02}' if value>=3600 else f'{value//60}:{value%60:02}'
 position=state.get('position',0);duration=state.get('duration',0)
 text=f"{fmt(position)}  ·  {fmt(max(0,duration-position))} left" if duration else fmt(position)
 return text+(f"  ·  {state.get('speed',1):g}×" if include_speed else '')

def color(value,fallback):
 if not isinstance(value,str) or len(value)!=7 or value[0]!='#':value=fallback
 try:r,g,b=(int(value[i:i+2],16) for i in (1,3,5))
 except ValueError:return color(fallback,fallback)
 return r|(g<<8)|(b<<16)

def layout(width,height,collapsed=False):
 """Client coordinates; title, transport, timing and a clickable progress strip."""
 if collapsed:return {102:(16,6,76,32),108:(98,6,36,32)}
 width=max(270,width);height=max(96,height);pad=10;gap=6
 available=width-2*pad-3*gap;back=int(available*.19);play=int(available*.32);speed=available-2*back-play
 row_height=max(26,min(44,height-74));bottom=height-34
 return {100:(pad,6,width-144,22),108:(width-112,4,30,24),105:(width-76,4,66,24),
         101:(pad,34,back,row_height),102:(pad+back+gap,34,play,row_height),
         103:(pad+back+play+2*gap,34,back,row_height),106:(width-pad-speed,34,speed,row_height),
         104:(pad,bottom,width-2*pad,20),107:(pad,height-10,width-2*pad,8)}

class FloatingBar:
 def __init__(self,player):self.player=player;self.thread=None;self.hwnd=None;self.ready=threading.Event();self.status='';self.post=None
 def start(self):
  if sys.platform!='win32':self.status='Floating desktop bar is available on Windows.';return
  self.thread=threading.Thread(target=self._run_guarded,name='shiur-floating-bar',daemon=True);self.thread.start();self.ready.wait(3)
 def _run_guarded(self):
  try:self.run()
  except Exception as e:self.status=str(e);self.ready.set();print('Floating bar unavailable: '+str(e),flush=True)
 def toggle(self):
  if not self.hwnd:raise RuntimeError(self.status or 'Floating bar is not ready.')
  self.post(self.hwnd,0x8001,0,0)
 def set_visible(self,visible):
  if not self.hwnd:raise RuntimeError(self.status or 'Floating bar is not ready.')
  self.post(self.hwnd,0x8003,int(bool(visible)),0)
 def close(self):
  if self.hwnd:self.post(self.hwnd,0x8002,0,0)
  if self.thread:self.thread.join(timeout=3)
 def run(self):
  from ctypes import wintypes as w
  user=ctypes.WinDLL('user32',use_last_error=True);gdi=ctypes.WinDLL('gdi32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
  LRESULT=ctypes.c_ssize_t;PROC=ctypes.WINFUNCTYPE(LRESULT,w.HWND,w.UINT,w.WPARAM,w.LPARAM)
  class WNDCLASS(ctypes.Structure):
   _fields_=[('style',w.UINT),('proc',PROC),('clsExtra',ctypes.c_int),('wndExtra',ctypes.c_int),('instance',w.HINSTANCE),('icon',w.HICON),('cursor',w.HANDLE),('brush',w.HBRUSH),('menu',w.LPCWSTR),('name',w.LPCWSTR)]
  class DRAWITEM(ctypes.Structure):
   _fields_=[('type',w.UINT),('id',w.UINT),('item',w.UINT),('action',w.UINT),('state',w.UINT),('hwnd',w.HWND),('dc',w.HDC),('rect',w.RECT),('data',ctypes.c_size_t)]
  class MINMAXINFO(ctypes.Structure):
   _fields_=[('reserved',w.POINT),('maxSize',w.POINT),('maxPosition',w.POINT),('minTrackSize',w.POINT),('maxTrackSize',w.POINT)]
  def bind(dll,name,result,args):
   fn=getattr(dll,name);fn.restype=result;fn.argtypes=args;return fn
  create=bind(user,'CreateWindowExW',w.HWND,[w.DWORD,w.LPCWSTR,w.LPCWSTR,w.DWORD,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,w.HWND,w.HMENU,w.HINSTANCE,w.LPVOID])
  default=bind(user,'DefWindowProcW',LRESULT,[w.HWND,w.UINT,w.WPARAM,w.LPARAM]);register=bind(user,'RegisterClassW',w.ATOM,[ctypes.POINTER(WNDCLASS)])
  self.post=bind(user,'PostMessageW',w.BOOL,[w.HWND,w.UINT,w.WPARAM,w.LPARAM]);show=bind(user,'ShowWindow',w.BOOL,[w.HWND,ctypes.c_int]);destroy=bind(user,'DestroyWindow',w.BOOL,[w.HWND]);settext=bind(user,'SetWindowTextW',w.BOOL,[w.HWND,w.LPCWSTR]);invalidate=bind(user,'InvalidateRect',w.BOOL,[w.HWND,ctypes.POINTER(w.RECT),w.BOOL])
  enable=bind(user,'EnableWindow',w.BOOL,[w.HWND,w.BOOL]);move=bind(user,'MoveWindow',w.BOOL,[w.HWND,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,w.BOOL])
  setstyle=bind(user,'SetWindowLongW',ctypes.c_long,[w.HWND,ctypes.c_int,ctypes.c_long])
  setpos=bind(user,'SetWindowPos',w.BOOL,[w.HWND,w.HWND,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,w.UINT])
  getrect=bind(user,'GetWindowRect',w.BOOL,[w.HWND,ctypes.POINTER(w.RECT)]);clientrect=bind(user,'GetClientRect',w.BOOL,[w.HWND,ctypes.POINTER(w.RECT)]);metrics=bind(user,'GetSystemMetrics',ctypes.c_int,[ctypes.c_int])
  getcursor=bind(user,'GetCursorPos',w.BOOL,[ctypes.POINTER(w.POINT)]);screenclient=bind(user,'ScreenToClient',w.BOOL,[w.HWND,ctypes.POINTER(w.POINT)])
  getmessage=bind(user,'GetMessageW',ctypes.c_int,[ctypes.POINTER(w.MSG),w.HWND,w.UINT,w.UINT]);translate=bind(user,'TranslateMessage',w.BOOL,[ctypes.POINTER(w.MSG)]);dispatch=bind(user,'DispatchMessageW',LRESULT,[ctypes.POINTER(w.MSG)]);quitmessage=bind(user,'PostQuitMessage',None,[ctypes.c_int])
  timer=bind(user,'SetTimer',ctypes.c_size_t,[w.HWND,ctypes.c_size_t,w.UINT,ctypes.c_void_p]);killtimer=bind(user,'KillTimer',w.BOOL,[w.HWND,ctypes.c_size_t]);send=bind(user,'SendMessageW',LRESULT,[w.HWND,w.UINT,w.WPARAM,w.LPARAM])
  brush=bind(gdi,'CreateSolidBrush',w.HBRUSH,[w.DWORD]);delete=bind(gdi,'DeleteObject',w.BOOL,[w.HGDIOBJ]);fill=bind(user,'FillRect',ctypes.c_int,[w.HDC,ctypes.POINTER(w.RECT),w.HBRUSH]);drawtext=bind(user,'DrawTextW',ctypes.c_int,[w.HDC,w.LPCWSTR,ctypes.c_int,ctypes.POINTER(w.RECT),w.UINT]);setcolor=bind(gdi,'SetTextColor',w.DWORD,[w.HDC,w.DWORD]);setbg=bind(gdi,'SetBkMode',ctypes.c_int,[w.HDC,ctypes.c_int]);select=bind(gdi,'SelectObject',w.HGDIOBJ,[w.HDC,w.HGDIOBJ])
  fontfn=bind(gdi,'CreateFontW',w.HFONT,[ctypes.c_int]*5+[w.DWORD]*8+[w.LPCWSTR]);getmodule=bind(kernel,'GetModuleHandleW',w.HMODULE,[w.LPCWSTR]);cursor=bind(user,'LoadCursorW',w.HANDLE,[w.HINSTANCE,ctypes.c_void_p])
  roundrect=bind(gdi,'RoundRect',w.BOOL,[w.HDC]+[ctypes.c_int]*6);penfn=bind(gdi,'CreatePen',w.HPEN,[ctypes.c_int,ctypes.c_int,w.DWORD])
  addfont=bind(gdi,'AddFontResourceExW',ctypes.c_int,[w.LPCWSTR,w.DWORD,w.LPVOID]);removefont=bind(gdi,'RemoveFontResourceExW',w.BOOL,[w.LPCWSTR,w.DWORD,w.LPVOID])
  fontpath=pathlib.Path(__file__).resolve().parent/'assets/Rubik.ttf';fontloaded=bool(fontpath.exists() and addfont(str(fontpath),0x10,None))
  current_family='Rubik' if fontloaded else 'Segoe UI'
  controls={};labels={101:'−15',102:'Play',103:'+15',105:'Open',106:'1x',108:'−'};palette={};resources=[];font=None
  progress_ratio=0.;last_progress=None
  texts={};enabled={};visible=self.player.saved.get('floatingVisible',False)
  collapsed=bool(self.player.saved.get('floatingCollapsed',False));expanded_size=list(DEFAULT_SIZE)
  def apply_mode():
   setstyle(self.hwnd,-16,ctypes.c_long(0x82000000 if collapsed else 0x02CC0000).value)
   size=COLLAPSED_SIZE if collapsed else expanded_size
   rect=w.RECT();getrect(self.hwnd,ctypes.byref(rect))
   # Keep the restored window on screen, even after dragging the pill to an edge.
   left,top,width,height=(metrics(i) for i in [76,77,78,79])
   x=max(left,min(rect.left,left+max(0,width-size[0])));y=max(top,min(rect.top,top+max(0,height-size[1])))
   setpos(self.hwnd,None,x,y,*size,0x0034)
   resize();invalidate(self.hwnd,None,False)
  def resize():
   nonlocal last_progress
   if not self.hwnd:return
   rect=w.RECT();clientrect(self.hwnd,ctypes.byref(rect))
   bounds=layout(rect.right,rect.bottom,collapsed)
   for ident,handle in controls.items():show(handle,5 if ident in bounds else 0)
   for ident,(x,y,width,height) in bounds.items():
    if ident in controls:move(controls[ident],x,y,width,height,True)
   last_progress=None
  def update():
   nonlocal palette,font,current_family,progress_ratio,last_progress
   with self.player.lock:state=self.player.snapshot();tracks=self.player.tracks;desired_palette=dict(self.player.saved.get('floatingTheme',{}))
   desired=desired_palette.get('fontFamily') or ('Rubik' if fontloaded else 'Segoe UI')
   if desired!=current_family:
    replacement=fontfn(-16,0,0,0,600,0,0,0,1,0,0,5,0,desired)
    if replacement:
     old=font;font=replacement;current_family=desired
     for handle in controls.values():send(handle,0x0030,font,1)
     if old:delete(old)
   if not resources or desired_palette!=palette:
    palette=desired_palette;background=brush(color(palette.get('surface'),'#111E36'))
    if resources:delete(resources.pop())
    resources.append(background)
    if self.hwnd:invalidate(self.hwnd,None,False)
    for handle in controls.values():invalidate(handle,None,False)
   for ident in (101,102,103,107):
    available=bool(tracks) if ident==102 else bool(state.get('currentId'))
    if ident==107:available=available and state.get('duration',0)>0
    if enabled.get(ident)!=available:enable(controls[ident],available);enabled[ident]=available
   duration=state.get('duration',0);progress_ratio=max(0,min(1,state.get('position',0)/duration)) if duration else 0.
   rect=w.RECT();clientrect(controls[107],ctypes.byref(rect))
   progress=(rect.right,rect.bottom,round(max(0,rect.right)*progress_ratio),enabled[107])
   if last_progress!=progress:invalidate(controls[107],None,False);last_progress=progress
   title,play,back,forward=display(state,tracks)
   values={100:title,102:play,101:back,103:forward,104:timing(state,False),105:'Open',106:f"{state.get('speed',1):g}x",108:'↗' if collapsed else '−'}
   for ident,text in values.items():
    if texts.get(ident)!=text:
     texts[ident]=text
     if ident in labels:labels[ident]=text
     settext(controls[ident],text)
  def proc(hwnd,msg,wp,lp):
   nonlocal visible,collapsed,expanded_size
   try:
    if msg==0x0024:
     info=ctypes.cast(lp,ctypes.POINTER(MINMAXINFO)).contents
     info.minTrackSize.x,info.minTrackSize.y=COLLAPSED_SIZE if collapsed else MIN_SIZE;return 0
    if msg==0x0084 and collapsed:return 2 # Unoccupied pill surface drags like a title bar.
    if msg==0x0005:resize();return 0
    if msg==0x0232:
     rect=w.RECT()
     if getrect(hwnd,ctypes.byref(rect)):
      with self.player.lock:
       self.player.saved['floatingPosition']=[rect.left,rect.top]
       if not collapsed:
        expanded_size=[max(MIN_SIZE[0],rect.right-rect.left),max(MIN_SIZE[1],rect.bottom-rect.top)];self.player.saved['floatingSize']=expanded_size
       self.player.persist()
     return 0
    if msg in (0x0010,0x8001,0x8003):
     visible=bool(wp) if msg==0x8003 else False if msg==0x0010 else not visible;show(hwnd,4 if visible else 0)
     with self.player.lock:self.player.saved['floatingVisible']=visible;self.player.persist()
     return 0
    if msg==0x8002:destroy(hwnd);return 0
    if msg==0x0002:killtimer(hwnd,1);quitmessage(0);return 0
    if msg==0x0021:return 3
    if msg==0x0113:update();return 0
    if msg==0x0111:
     ident=wp&0xffff
     if (wp>>16)==0 and ident==108:
      collapsed=not collapsed
      with self.player.lock:self.player.saved['floatingCollapsed']=collapsed;self.player.persist()
      apply_mode();update();return 0
     if (wp>>16)==0 and ident==107:
      point=w.POINT();rect=w.RECT()
      if getcursor(ctypes.byref(point)) and screenclient(controls[107],ctypes.byref(point)) and clientrect(controls[107],ctypes.byref(rect)) and rect.right>0:
       with self.player.lock:
        state=self.player.snapshot()
        if state.get('currentId') and state.get('duration',0)>0:self.player.command({'op':'seek','value':max(0,min(1,point.x/rect.right))*state['duration']})
       update()
      return 0
     if (wp>>16)==0 and ident==105:
      callback=getattr(self.player,'show_window',None)
      if callback:callback()
      return 0
     if (wp>>16)==0 and ident in (101,102,103,106):
      action={'op':'speed_cycle'} if ident==106 else {'op':'toggle'} if ident==102 else {'op':'skip','direction':-1 if ident==101 else 1}
      self.player.command(action);update();return 0
    if msg==0x0014:
     rect=w.RECT();clientrect(hwnd,ctypes.byref(rect))
     if resources:fill(wp,ctypes.byref(rect),resources[0])
     return 1
    if msg==0x0138:
     setbg(wp,1);setcolor(wp,color(palette.get('onSurface'),'#FFFFFF'));return resources[0] if resources else 0
    if msg==0x002B:
     item=ctypes.cast(lp,ctypes.POINTER(DRAWITEM)).contents;primary=item.id==102
     if item.id==107:
      if resources:fill(item.dc,ctypes.byref(item.rect),resources[0])
      middle=(item.rect.top+item.rect.bottom)//2
      track=w.RECT(item.rect.left,middle-2,item.rect.right,middle+2)
      background=brush(color(palette.get('surfaceContainer'),'#263A5B'));fill(item.dc,ctypes.byref(track),background);delete(background)
      if progress_ratio>0:
       track.right=track.left+round((track.right-track.left)*progress_ratio)
       foreground=brush(color(palette.get('primary'),'#214CDB'));fill(item.dc,ctypes.byref(track),foreground);delete(foreground)
      return 1
     shade=color(palette.get('primary') if primary else palette.get('surfaceContainer'),'#214CDB' if primary else '#263A5B')
     if resources:fill(item.dc,ctypes.byref(item.rect),resources[0])
     b=brush(shade);pen=penfn(0,1,shade);oldbrush=select(item.dc,b);oldpen=select(item.dc,pen)
     roundrect(item.dc,item.rect.left+1,item.rect.top+1,item.rect.right-1,item.rect.bottom-1,12,12)
     select(item.dc,oldpen);select(item.dc,oldbrush);delete(pen);delete(b)
     setcolor(item.dc,color(palette.get('onPrimary') if primary else palette.get('onSurface'),'#FFFFFF'));setbg(item.dc,1)
     old=select(item.dc,font);drawtext(item.dc,labels.get(item.id,''),-1,ctypes.byref(item.rect),0x25);select(item.dc,old);return 1
   except Exception as e:
    with self.player.lock:self.player.error=str(e)
    return 0
   return default(hwnd,msg,wp,lp)
  self.callback=PROC(proc)
  try:
   instance=getmodule(None);name='ShiurPlayerFloatingTransport'
   cls=WNDCLASS(0,self.callback,0,0,instance,None,cursor(None,ctypes.c_void_p(32512)),None,None,name)
   if not register(ctypes.byref(cls)):raise OSError(ctypes.get_last_error(),'Could not register floating bar window.')
   font=fontfn(-16,0,0,0,600,0,0,0,1,0,0,5,0,current_family)
   position=self.player.saved.get('floatingPosition',[80,80]);x,y=position if isinstance(position,list) and len(position)==2 and all(isinstance(v,int) for v in position) else [80,80]
   size=self.player.saved.get('floatingSize',list(DEFAULT_SIZE))
   if not isinstance(size,list) or len(size)!=2 or not all(isinstance(v,int) for v in size):size=list(DEFAULT_SIZE)
   bar_width=max(MIN_SIZE[0],size[0]);bar_height=max(MIN_SIZE[1],size[1])
   expanded_size=[bar_width,bar_height]
   if collapsed:bar_width,bar_height=COLLAPSED_SIZE
   left,top,width,height=(metrics(i) for i in [76,77,78,79])
   if width>0 and height>0:
    bar_width=min(bar_width,max(1,width));bar_height=min(bar_height,max(1,height))
    x=max(left,min(x,left+max(0,width-bar_width)));y=max(top,min(y,top+max(0,height-bar_height)))
   # WS_THICKFRAME enables resizing. WS_CLIPCHILDREN avoids painting over controls.
   self.hwnd=create(0x08000088,name,'Shiur Player',(0x82000000 if collapsed else 0x02CC0000),x,y,bar_width,bar_height,None,None,instance,None)
   if not self.hwnd:raise OSError(ctypes.get_last_error(),'Could not create floating bar.')
   for ident in (100,104):controls[ident]=create(0,'STATIC','',0x50004000,0,0,1,1,self.hwnd,ident,instance,None)
   # SS_OWNERDRAW | SS_NOTIFY: clickable, without claiming a keyboard tab stop.
   controls[107]=create(0,'STATIC','Seek position',0x5000010D,0,0,1,1,self.hwnd,107,instance,None)
   for ident,text in labels.items():controls[ident]=create(0,'BUTTON',text,0x5001000B,0,0,1,1,self.hwnd,ident,instance,None)
   if not all(controls.values()):raise RuntimeError('Could not create floating controls.')
   for handle in controls.values():send(handle,0x0030,font,1)
   resize();update();timer(self.hwnd,1,500,None);show(self.hwnd,4 if visible else 0);self.status='ready';self.ready.set()
   message=w.MSG()
   while getmessage(ctypes.byref(message),None,0,0)>0:translate(ctypes.byref(message));dispatch(ctypes.byref(message))
  except Exception as e:self.status=str(e);print('Floating bar unavailable: '+str(e),flush=True)
  finally:
   self.ready.set()
   if self.hwnd:destroy(self.hwnd)
   self.hwnd=None
   if font:delete(font)
   for resource in resources:delete(resource)
   if fontloaded:removefont(str(fontpath),0x10,None)
