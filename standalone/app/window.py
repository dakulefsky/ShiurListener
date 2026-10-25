"""Native Win32 player window. All playback controls call the local engine."""
import ctypes,threading
from controller import clock
from folder_picker import choose_recordings_folder
TEXT={'title': 'Shiur Player', 'folder': 'Choose folder', 'rescan': 'Rescan', 'none': 'Choose the folder containing your audio recordings to begin.', 'all': 'All recordings', 'continue': 'Continue listening', 'play': 'Play', 'pause': 'Pause', 'back': 'Back', 'forward': 'Forward', 'previous': 'Previous', 'next': 'Next', 'volume': 'Volume', 'floating': 'Floating player', 'auto': 'Auto-next', 'keys': 'Shortcuts in other apps', 'off': 'Sleep timer off', 'new': 'New collection', 'rename': 'Rename', 'delete': 'Delete', 'add': 'Add', 'name': 'Collection name', 'search': 'Search recordings', 'mark': 'Bookmark', 'markName': 'Bookmark name', 'go': 'Go', 'reset': 'Start over', 'resetAsk': 'Reset the saved position of the selected recording?', 'deleteAsk': 'Delete this collection? Your audio files will stay where they are.', 'empty': 'No recordings in this view. Try another collection or search.', 'ready': 'Positions are saved on this computer. Ctrl+Space: play; Ctrl+arrows: skip.', 'missing': 'No audio found. Choose a folder containing MP3 / M4A / WAV files and rescan.', 'count': '{n} recordings', 'minutes': '{n} minutes'}
class PlayerWindow:
 def __init__(self,player,library,shortcuts):
  self.player=player;self.library=library;self.shortcuts=shortcuts;self.hwnd=None;self.picking=False;self.seeking=False
 def run(self):
  from ctypes import wintypes as w
  user=ctypes.WinDLL('user32',use_last_error=True);gdi=ctypes.WinDLL('gdi32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True);common=ctypes.WinDLL('comctl32',use_last_error=True)
  def bind(dll,name,result,args):
   fn=getattr(dll,name);fn.restype=result;fn.argtypes=args;return fn
  proc_type=ctypes.WINFUNCTYPE(ctypes.c_ssize_t,w.HWND,w.UINT,w.WPARAM,w.LPARAM)
  class WNDCLASS(ctypes.Structure):
   _fields_=[('style',w.UINT),('proc',proc_type),('clsExtra',ctypes.c_int),('wndExtra',ctypes.c_int),('instance',w.HINSTANCE),('icon',w.HICON),('cursor',w.HANDLE),('brush',w.HBRUSH),('menu',w.LPCWSTR),('name',w.LPCWSTR)]
  class INIT(ctypes.Structure):_fields_=[('size',w.DWORD),('classes',w.DWORD)]
  init=bind(common,'InitCommonControlsEx',w.BOOL,[ctypes.POINTER(INIT)]);init(ctypes.byref(INIT(ctypes.sizeof(INIT),4)))
  create=bind(user,'CreateWindowExW',w.HWND,[w.DWORD,w.LPCWSTR,w.LPCWSTR,w.DWORD]+[ctypes.c_int]*4+[w.HWND,w.HMENU,w.HINSTANCE,w.LPVOID])
  register=bind(user,'RegisterClassW',w.ATOM,[ctypes.POINTER(WNDCLASS)]);default=bind(user,'DefWindowProcW',ctypes.c_ssize_t,[w.HWND,w.UINT,w.WPARAM,w.LPARAM])
  show=bind(user,'ShowWindow',w.BOOL,[w.HWND,ctypes.c_int]);post=bind(user,'PostMessageW',w.BOOL,[w.HWND,w.UINT,w.WPARAM,w.LPARAM]);send=bind(user,'SendMessageW',ctypes.c_ssize_t,[w.HWND,w.UINT,w.WPARAM,w.LPARAM]);enable=bind(user,'EnableWindow',w.BOOL,[w.HWND,w.BOOL])
  settext=bind(user,'SetWindowTextW',w.BOOL,[w.HWND,w.LPCWSTR]);getlen=bind(user,'GetWindowTextLengthW',ctypes.c_int,[w.HWND]);gettext=bind(user,'GetWindowTextW',ctypes.c_int,[w.HWND,w.LPWSTR,ctypes.c_int])
  destroy=bind(user,'DestroyWindow',w.BOOL,[w.HWND]);quit=bind(user,'PostQuitMessage',None,[ctypes.c_int]);foreground=bind(user,'SetForegroundWindow',w.BOOL,[w.HWND]);messagebox=bind(user,'MessageBoxW',ctypes.c_int,[w.HWND,w.LPCWSTR,w.LPCWSTR,w.UINT])
  getmessage=bind(user,'GetMessageW',ctypes.c_int,[ctypes.POINTER(w.MSG),w.HWND,w.UINT,w.UINT]);translate=bind(user,'TranslateMessage',w.BOOL,[ctypes.POINTER(w.MSG)]);dispatch=bind(user,'DispatchMessageW',ctypes.c_ssize_t,[ctypes.POINTER(w.MSG)]);dialogmsg=bind(user,'IsDialogMessageW',w.BOOL,[w.HWND,ctypes.POINTER(w.MSG)])
  timer=bind(user,'SetTimer',ctypes.c_size_t,[w.HWND,ctypes.c_size_t,w.UINT,ctypes.c_void_p]);killtimer=bind(user,'KillTimer',w.BOOL,[w.HWND,ctypes.c_size_t]);key=bind(user,'GetKeyState',ctypes.c_short,[ctypes.c_int]);focus=bind(user,'GetFocus',w.HWND,[])
  module=bind(kernel,'GetModuleHandleW',w.HMODULE,[w.LPCWSTR]);cursor=bind(user,'LoadCursorW',w.HANDLE,[w.HINSTANCE,ctypes.c_void_p]);sysbrush=bind(user,'GetSysColorBrush',w.HBRUSH,[ctypes.c_int]);metrics=bind(user,'GetSystemMetrics',ctypes.c_int,[ctypes.c_int])
  fontfn=bind(gdi,'CreateFontW',w.HFONT,[ctypes.c_int]*5+[w.DWORD]*8+[w.LPCWSTR]);delete=bind(gdi,'DeleteObject',w.BOOL,[w.HGDIOBJ])
  controls={};font=None;last_labels=None;last_list=None;last_collections=None;last_marks=None;visible_ids=[];view_ids=[];target_ids=[];mark_ids=[]
  def text():return TEXT
  def read(ident):
   size=getlen(controls[ident])+1;buffer=ctypes.create_unicode_buffer(size);gettext(controls[ident],buffer,size);return buffer.value
  def add(handle,value,message):
   string=ctypes.c_wchar_p(value);send(handle,message,0,ctypes.cast(string,ctypes.c_void_p).value)
  def combo(ident,items):
   send(controls[ident],0x014B,0,0)
   for item in items:add(controls[ident],item,0x0143)
  def cue(ident,value):
   string=ctypes.c_wchar_p(value);send(controls[ident],0x1501,1,ctypes.cast(string,ctypes.c_void_p).value)
  def update():
   nonlocal last_labels,last_list,last_collections,last_marks,visible_ids,view_ids,target_ids,mark_ids
   if not controls:return
   with self.player.lock:
    state=self.player.snapshot();t=text();lang='en';folders=list(self.player.saved['folders']);marks=list(self.library.bookmarks())
   if lang!=last_labels:
    last_labels=lang;settext(self.hwnd,t['title'])
    for ident,label in [(101,'folder'),(102,'rescan'),(201,'previous'),(202,'back'),(204,'forward'),(205,'next'),(216,'floating'),(214,'auto'),(217,'keys'),(220,'new'),(221,'rename'),(222,'delete'),(223,'add'),(224,'reset'),(230,'mark'),(231,'go'),(232,'delete'),(219,'volume')]:settext(controls[ident],t[label])
    cue(103,t['search']);cue(226,t['name']);cue(233,t['markName'])
    combo(212,[t['off']]+[t['minutes'].format(n=n) for n in (15,30,60,90)])
   settext(controls[104],str(self.player.root) if self.player.root else t['none'])
   values=self.library.tracks();signature=(self.player.library_revision,self.library.view,self.library.query,self.library.revision,lang,state['currentId'],state['status'])
   if signature!=last_list:
    last_list=signature;visible_ids=[track['id'] for track in values];send(controls[200],0x0184,0,0)
    for track in values:
     label=track['name']+(('  ·  '+clock(track.get('position',0))) if track.get('position',0)>0 else '')
     add(controls[200],label,0x0180)
    selected=self.library.selected if self.library.selected in visible_ids else state['currentId']
    if selected in visible_ids:send(controls[200],0x0186,visible_ids.index(selected),0)
   settext(controls[105],t['count'].format(n=len(values)))
   folder_signature=(lang,tuple((f['id'],f['name']) for f in folders),self.library.view)
   if folder_signature!=last_collections:
    last_collections=folder_signature;old=send(controls[225],0x0147,0,0);target=target_ids[old] if 0<=old<len(target_ids) else None
    view_ids=['all','continue']+[f['id'] for f in folders];target_ids=[f['id'] for f in folders]
    combo(106,[t['all'],t['continue']]+[f['name'] for f in folders]);combo(225,[f['name'] for f in folders])
    send(controls[106],0x014E,view_ids.index(self.library.view) if self.library.view in view_ids else 0,0)
    if target_ids:send(controls[225],0x014E,target_ids.index(target) if target in target_ids else len(target_ids)-1,0)
   current=next((v for v in self.player.tracks if v['id']==state['currentId']),None)
   settext(controls[206],current['name'] if current else t['title'])
   remaining=('  ·  '+t['minutes'].format(n=round(state['sleepRemaining']/60))) if state['sleepRemaining'] else ''
   settext(controls[207],f"{clock(state['position'])} / {clock(state['duration'])}"+remaining)
   settext(controls[203],t['pause'] if state['status']=='playing' else t['play'])
   if not self.seeking:send(controls[210],0x0405,1,round(10000*state['position']/state['duration']) if state['duration'] else 0)
   send(controls[211],0x0405,1,round(state['volume']*100));send(controls[213],0x014E,[.75,1,1.25,1.5,1.75,2].index(state['speed']),0)
   send(controls[215],0x014E,[10,15,60].index(state['skipSeconds']),0);send(controls[212],0x014E,[0,15,30,60,90].index(state['sleepMinutes']) if state['sleepMinutes'] in [0,15,30,60,90] else 0,0)
   send(controls[214],0x00F1,int(state['autoNext']),0);send(controls[217],0x00F1,int(self.player.saved.get('globalShortcuts',False)),0)
   enable(controls[203],bool(values) or bool(state['currentId']))
   for ident in [201,202,204,205,210]:enable(controls[ident],state['loaded'])
   for ident in [221,222]:enable(controls[ident],self.library.view not in ['all','continue'])
   enable(controls[223],bool(target_ids) and bool(self.library.selected))
   mark_signature=(state['currentId'],tuple((m['id'],m['name'],m['position']) for m in marks))
   if mark_signature!=last_marks:
    last_marks=mark_signature;mark_ids=[m['id'] for m in marks];combo(234,[clock(m['position'])+' · '+m['name'] for m in marks])
    if marks:send(controls[234],0x014E,len(marks)-1,0)
   errors=self.player.error
   conflicts=[entry for entry in state['hotkeys'] if not entry.get('registered')]
   settext(controls[218],errors or (t['missing'] if not self.player.tracks else ('Shortcut unavailable' if conflicts else t['ready'])))
  def choose():
   if self.picking:return
   self.picking=True
   def work():
    try:
     folder=choose_recordings_folder('en')
     if folder:
      self.player.scan(folder);self.library.view='all';self.library.selected=self.player.saved['currentId']
    except Exception as error:self.player.error=str(error)
    finally:self.picking=False;post(self.hwnd,0x800C,0,0)
   threading.Thread(target=work,daemon=True).start()
  def confirm(key_name):return messagebox(self.hwnd,text()[key_name],text()['title'],0x24)==6
  def action(ident):
   if ident==101:choose()
   elif ident==102:
    if self.player.root:self.player.scan()
    else:choose()
   elif ident==203:self.library.play()
   elif ident in (201,205):self.player.command({'op':'previous' if ident==201 else 'next'})
   elif ident in (202,204):self.player.command({'op':'skip','direction':-1 if ident==202 else 1})
   elif ident==216:self.player.floating_bar.toggle()
   elif ident==214:self.player.command({'op':'autonext','value':bool(send(controls[214],0x00F0,0,0))})
   elif ident==217:self.shortcuts(bool(send(controls[217],0x00F0,0,0)))
   elif ident==220:self.library.collection('folder_create',read(226));settext(controls[226],'')
   elif ident==221:self.library.collection('folder_rename',read(226));settext(controls[226],'')
   elif ident==222:
    if confirm('deleteAsk'):self.library.collection('folder_delete')
   elif ident==223:
    index=send(controls[225],0x0147,0,0)
    if 0<=index<len(target_ids):self.library.add_to(target_ids[index])
   elif ident==224:
    if confirm('resetAsk'):self.library.reset()
   elif ident==230:self.library.mark(read(233));settext(controls[233],'')
   elif ident in (231,232):
    index=send(controls[234],0x0147,0,0)
    if 0<=index<len(mark_ids):self.library.bookmark_action(mark_ids[index],delete=ident==232)
   update()
  def proc(hwnd,msg,wp,lp):
   try:
    if msg==0x0010:self.player.capture();self.player.persist();destroy(hwnd);return 0
    if msg==0x0011:return 1
    if msg==0x0016:
     if wp:self.player.capture();self.player.persist();destroy(hwnd)
     return 0
    if msg==0x0002:killtimer(hwnd,1);quit(0);return 0
    if msg==0x800B:show(hwnd,9);foreground(hwnd);return 0
    if msg==0x800D:show(hwnd,9);foreground(hwnd);choose();return 0
    if msg in (0x0113,0x800C):update();return 0
    if msg==0x0114:
     code=wp&0xffff
     if lp==controls[210]:
      self.seeking=code==5
      if code!=5:
       duration=self.player.snapshot()['duration'];self.player.command({'op':'seek','value':duration*send(controls[210],0x0400,0,0)/10000})
     elif lp==controls[211]:self.player.command({'op':'volume','value':send(controls[211],0x0400,0,0)/100})
     update();return 0
    if msg==0x0111:
     ident,notification=wp&0xffff,wp>>16
     if ident==200 and notification in (1,2):
      index=send(controls[200],0x0188,0,0)
      if 0<=index<len(visible_ids):self.library.selected=visible_ids[index]
      if notification==2:self.library.play(force=True)
      update();return 0
     if ident==103 and notification==0x0300:self.library.query=read(103);update();return 0
     if notification==1 and ident in (106,212,213,215):
      index=send(controls[ident],0x0147,0,0)
      if ident==106 and 0<=index<len(view_ids):self.library.view=view_ids[index]
      elif ident==212 and 0<=index<5:self.player.command({'op':'sleep_timer','minutes':[0,15,30,60,90][index]})
      elif ident==213 and 0<=index<6:self.player.command({'op':'speed','value':[.75,1,1.25,1.5,1.75,2][index]})
      elif ident==215 and 0<=index<3:self.player.command({'op':'skip_interval','value':[10,15,60][index]})
      update();return 0
     if notification==0:action(ident);return 0
   except Exception as error:self.player.error=str(error);update();return 0
   return default(hwnd,msg,wp,lp)
  callback=proc_type(proc);instance=module(None)
  cls=WNDCLASS(0,callback,0,0,instance,None,cursor(None,ctypes.c_void_p(32512)),sysbrush(5),None,'ShiurPlayerStandaloneWindow')
  if not register(ctypes.byref(cls)):raise OSError(ctypes.get_last_error(),'Could not create player window.')
  try:
   x=max(0,(metrics(0)-1000)//2);y=max(0,(metrics(1)-700)//2)
   self.hwnd=create(0x10000,cls.name,'Shiur Player',0x00CA0000,x,y,1000,700,None,None,instance,None)
   if not self.hwnd:raise OSError(ctypes.get_last_error(),'Could not open player window.')
   font=fontfn(-16,0,0,0,400,0,0,0,1,0,0,5,0,'Rubik')
   items=[(104,'EDIT','',20,18,660,30),(101,'BUTTON','',690,16,130,34),(102,'BUTTON','',830,16,130,34),(103,'EDIT','',20,62,370,30),(105,'STATIC','',20,102,350,24),(200,'LISTBOX','',20,132,940,190),(206,'STATIC','',20,334,940,24),(207,'STATIC','',20,362,940,22),(210,'msctls_trackbar32','',20,390,940,28),(201,'BUTTON','',20,430,90,42),(202,'BUTTON','',120,430,90,42),(203,'BUTTON','',220,430,170,42),(204,'BUTTON','',400,430,90,42),(205,'BUTTON','',500,430,90,42),(219,'STATIC','',20,492,60,26),(211,'msctls_trackbar32','',80,486,160,32),(214,'BUTTON','',440,486,160,32),(216,'BUTTON','',610,486,160,32),(217,'BUTTON','',20,626,300,26),(218,'STATIC','',325,626,635,26),(226,'EDIT','',20,538,160,30),(220,'BUTTON','',190,536,120,34),(221,'BUTTON','',320,536,90,34),(222,'BUTTON','',420,536,90,34),(223,'BUTTON','',740,536,90,34),(224,'BUTTON','',840,536,120,34),(233,'EDIT','',20,582,180,30),(230,'BUTTON','',210,580,120,34),(231,'BUTTON','',760,580,90,34),(232,'BUTTON','',860,580,100,34)]
   for ident,kind,value,a,b,width,height in items:
    style=0x50000000
    if kind=='EDIT':style|=0x00810080|(0x0800 if ident==104 else 0)
    elif kind=='LISTBOX':style|=0x00A10101
    elif kind=='BUTTON':style|=0x10000|(3 if ident in (214,217) else 0)
    elif kind=='msctls_trackbar32':style|=0x10001
    controls[ident]=create(0,kind,value,style,a,b,width,height,self.hwnd,ident,instance,None)
   for ident,a,b,width in [(106,410,62,550),(212,260,486,170),(213,610,430,170),(215,790,430,170),(225,525,538,200),(234,345,582,400)]:controls[ident]=create(0,'COMBOBOX','',0x50210003,a,b,width,220,self.hwnd,ident,instance,None)
   for handle in controls.values():
    if not handle:raise RuntimeError('Could not create player controls.')
    send(handle,0x0030,font,1)
   combo(213,['0.75×','1×','1.25×','1.5×','1.75×','2×']);combo(215,['10s','15s','60s'])
   send(controls[210],0x0406,1,10000<<16);send(controls[211],0x0406,1,100<<16)
   self.player.show_window=lambda:post(self.hwnd,0x800B,0,0);self.player.choose_folder=lambda:post(self.hwnd,0x800D,0,0)
   update();timer(self.hwnd,1,500,None);show(self.hwnd,5)
   message=w.MSG()
   while getmessage(ctypes.byref(message),None,0,0)>0:
    if message.message==0x0100 and key(0x11)<0 and message.wParam in (0x20,0x25,0x27):
     try:action(203 if message.wParam==0x20 else 202 if message.wParam==0x25 else 204)
     except Exception as error:self.player.error=str(error);update()
     continue
    if message.message==0x0100 and message.wParam==13 and focus()==controls[200]:
     try:self.library.play(force=True);update()
     except Exception as error:self.player.error=str(error);update()
     continue
    if not dialogmsg(self.hwnd,ctypes.byref(message)):translate(ctypes.byref(message));dispatch(ctypes.byref(message))
  finally:
   self.player.show_window=None;self.player.choose_folder=None
   if font:delete(font)
