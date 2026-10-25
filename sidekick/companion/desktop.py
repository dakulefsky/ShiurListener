"""Native companion setup window. Uses Windows controls; no browser or GUI runtime."""
import ctypes,pathlib,threading
TEXT={
'he':{'title':'נגן שיעורים','folder':'תיקיית השיעורים','none':'טרם נבחרה תיקייה','choose':'בחירת תיקיית שיעורים','scan':'סריקה מחדש','count':'נמצאו {count} שיעורים','empty':'אין קובצי שמע בתיקייה. בחרו תיקייה אחרת או הוסיפו קבצים וסרקו מחדש.','code':'קוד חיבור — להדבקה בתוסף אוצריא','copy':'העתקת הקוד','copied':'הקוד הועתק. הדביקו אותו בתוסף ולחצו על חיבור.','hide':'הסתרה והמשך האזנה','quit':'יציאה מהנגן','floating':'הצגה / הסתרה של הנגן הצף','hint':'סגירת החלון מסתירה אותו בלבד. לפתיחה מחדש הפעילו את ה־EXE שוב. יציאה עוצרת את השמע.'},
'en':{'title':'Shiur Player','folder':'Recordings folder','none':'No folder selected','choose':'Choose recordings folder','scan':'Rescan folder','count':'{count} recordings found','empty':'No audio files in this folder. Choose another folder or add files and rescan.','code':'Connection code — paste into the Otzaria plugin','copy':'Copy code','copied':'Code copied. Paste it into the plugin and click Connect.','hide':'Hide and keep listening','quit':'Exit player','floating':'Show / hide floating player','hint':'Closing this window only hides it. Run the EXE again to reopen it. Exit stops the audio.'}}
def labels(player):
 lang=player.saved.get('language','he');text=TEXT.get(lang,TEXT['he'])
 return text,text['count'].format(count=len(player.tracks)),str(player.root) if player.root else text['none']
def choose_recordings_folder(language='he'):
 import base64,os,subprocess
 title=TEXT.get(language,TEXT['he'])['choose']
 # Both titles are fixed application strings; no paths or request data enter this command.
 script="""[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName System.Windows.Forms
$picker = New-Object System.Windows.Forms.FolderBrowserDialog
$picker.Description = '"""+title+"""'
$picker.ShowNewFolderButton = $false
if ($picker.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { [Console]::Write($picker.SelectedPath) }
$picker.Dispose()
"""
 powershell=pathlib.Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
 result=subprocess.run([str(powershell),'-NoProfile','-STA','-NonInteractive','-EncodedCommand',base64.b64encode(script.encode('utf-16le')).decode('ascii')],capture_output=True,text=True,encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW,check=True)
 return result.stdout.strip()
class DesktopWindow:
 def __init__(self,player,token):self.player=player;self.token=token;self.hwnd=None;self.picking=False
 def run(self):
  from ctypes import wintypes as w
  user=ctypes.WinDLL('user32',use_last_error=True);gdi=ctypes.WinDLL('gdi32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
  def bind(dll,name,result,args):
   fn=getattr(dll,name);fn.restype=result;fn.argtypes=args;return fn
  proc_type=ctypes.WINFUNCTYPE(ctypes.c_ssize_t,w.HWND,w.UINT,w.WPARAM,w.LPARAM)
  class WNDCLASS(ctypes.Structure):
   _fields_=[('style',w.UINT),('proc',proc_type),('clsExtra',ctypes.c_int),('wndExtra',ctypes.c_int),('instance',w.HINSTANCE),('icon',w.HICON),('cursor',w.HANDLE),('brush',w.HBRUSH),('menu',w.LPCWSTR),('name',w.LPCWSTR)]
  create=bind(user,'CreateWindowExW',w.HWND,[w.DWORD,w.LPCWSTR,w.LPCWSTR,w.DWORD]+[ctypes.c_int]*4+[w.HWND,w.HMENU,w.HINSTANCE,w.LPVOID])
  register=bind(user,'RegisterClassW',w.ATOM,[ctypes.POINTER(WNDCLASS)]);default=bind(user,'DefWindowProcW',ctypes.c_ssize_t,[w.HWND,w.UINT,w.WPARAM,w.LPARAM])
  show=bind(user,'ShowWindow',w.BOOL,[w.HWND,ctypes.c_int]);post=bind(user,'PostMessageW',w.BOOL,[w.HWND,w.UINT,w.WPARAM,w.LPARAM]);send=bind(user,'SendMessageW',ctypes.c_ssize_t,[w.HWND,w.UINT,w.WPARAM,w.LPARAM])
  foreground=bind(user,'SetForegroundWindow',w.BOOL,[w.HWND])
  settext=bind(user,'SetWindowTextW',w.BOOL,[w.HWND,w.LPCWSTR]);destroy=bind(user,'DestroyWindow',w.BOOL,[w.HWND]);quit=bind(user,'PostQuitMessage',None,[ctypes.c_int])
  getmessage=bind(user,'GetMessageW',ctypes.c_int,[ctypes.POINTER(w.MSG),w.HWND,w.UINT,w.UINT]);translate=bind(user,'TranslateMessage',w.BOOL,[ctypes.POINTER(w.MSG)]);dispatch=bind(user,'DispatchMessageW',ctypes.c_ssize_t,[ctypes.POINTER(w.MSG)])
  dialogmsg=bind(user,'IsDialogMessageW',w.BOOL,[w.HWND,ctypes.POINTER(w.MSG)]);timer=bind(user,'SetTimer',ctypes.c_size_t,[w.HWND,ctypes.c_size_t,w.UINT,ctypes.c_void_p]);killtimer=bind(user,'KillTimer',w.BOOL,[w.HWND,ctypes.c_size_t])
  module=bind(kernel,'GetModuleHandleW',w.HMODULE,[w.LPCWSTR]);cursor=bind(user,'LoadCursorW',w.HANDLE,[w.HINSTANCE,ctypes.c_void_p]);sysbrush=bind(user,'GetSysColorBrush',w.HBRUSH,[ctypes.c_int])
  fontfn=bind(gdi,'CreateFontW',w.HFONT,[ctypes.c_int]*5+[w.DWORD]*8+[w.LPCWSTR]);delete=bind(gdi,'DeleteObject',w.BOOL,[w.HGDIOBJ])
  controls={};last=None;font=None
  def update():
   nonlocal last
   with self.player.lock:
    text,count,folder=labels(self.player);error=self.player.error
   signature=(text['title'],count,folder,error)
   if signature==last:return
   last=signature;settext(self.hwnd,text['title'])
   for ident,key in [(100,'folder'),(101,'choose'),(102,'scan'),(103,'copy'),(104,'quit'),(105,'hide'),(107,'floating'),(108,'code'),(109,'hint')]:settext(controls[ident],text[key])
   settext(controls[110],folder);settext(controls[111],count)
   settext(controls[112],error or (text['empty'] if not self.player.tracks else ''))
   send(controls[106],0x014E,1 if self.player.saved.get('language')=='en' else 0,0)
  def pick():
   if self.picking:return
   self.picking=True
   def work():
    try:
     folder=choose_recordings_folder(self.player.saved.get('language','he'))
     if folder:self.player.scan(folder)
    except Exception as error:self.player.error=str(error)
    finally:self.picking=False;post(self.hwnd,0x800C,0,0)
   threading.Thread(target=work,daemon=True).start()
  def proc(hwnd,msg,wp,lp):
   try:
    if msg in (0x0010,0x800E):show(hwnd,0);return 0
    if msg==0x0002:killtimer(hwnd,1);quit(0);return 0
    if msg==0x800B:show(hwnd,9);foreground(hwnd);return 0
    if msg==0x800D:show(hwnd,9);foreground(hwnd);pick();return 0
    if msg in (0x0113,0x800C):update();return 0
    if msg==0x0111:
     ident=wp&0xffff
     if ident==106 and wp>>16==1:self.player.command({'op':'language','value':'en' if send(controls[106],0x0147,0,0)==1 else 'he'});update()
     elif wp>>16==0:
      if ident==101:pick()
      elif ident==102:
       if self.player.root:self.player.scan()
       else:pick()
       update()
      elif ident==103:send(controls[113],0x00B1,0,-1);send(controls[113],0x0301,0,0);settext(controls[112],labels(self.player)[0]['copied'])
      elif ident==104:destroy(hwnd)
      elif ident==105:show(hwnd,0)
      elif ident==107:
       if self.player.floating_bar:self.player.floating_bar.toggle()
     return 0
   except Exception as error:self.player.error=str(error);update();return 0
   return default(hwnd,msg,wp,lp)
  callback=proc_type(proc);instance=module(None)
  cls=WNDCLASS(0,callback,0,0,instance,None,cursor(None,ctypes.c_void_p(32512)),sysbrush(5),None,'ShiurPlayerSetupWindow')
  if not register(ctypes.byref(cls)):raise OSError(ctypes.get_last_error(),'Could not create setup window.')
  try:
   self.hwnd=create(0x10000,cls.name,'נגן שיעורים',0x00CA0000,100,100,660,510,None,None,instance,None)
   if not self.hwnd:raise OSError(ctypes.get_last_error(),'Could not open setup window.')
   font=fontfn(-17,0,0,0,400,0,0,0,1,0,0,5,0,'Segoe UI')
   items=[(114,'STATIC','1.1.0',22,18,200,30),(100,'STATIC','',22,60,600,24),(110,'EDIT','',22,88,600,30),(101,'BUTTON','',22,132,270,38),(102,'BUTTON','',306,132,160,38),(111,'STATIC','',22,182,600,24),(112,'STATIC','',22,210,600,48),(108,'STATIC','',22,265,600,24),(113,'EDIT',self.token,22,293,450,32),(103,'BUTTON','',484,291,138,36),(107,'BUTTON','',22,342,190,38),(105,'BUTTON','',222,342,220,38),(104,'BUTTON','',454,342,168,38),(109,'STATIC','',22,392,600,40)]
   for ident,kind,value,x,y,width,height in items:
    style=0x50000000|(0x10000 if kind!='STATIC' else 0)|(0x00800880 if kind=='EDIT' else 0)
    controls[ident]=create(0,kind,value,style,x,y,width,height,self.hwnd,ident,instance,None)
   controls[106]=create(0,'COMBOBOX','',0x50210003,410,16,210,150,self.hwnd,106,instance,None)
   for label in ['עברית','English']:
    value=ctypes.c_wchar_p(label);send(controls[106],0x0143,0,ctypes.cast(value,ctypes.c_void_p).value)
   for handle in controls.values():
    if not handle:raise RuntimeError('Could not create setup controls.')
    send(handle,0x0030,font,1)
   self.player.show_window=lambda:post(self.hwnd,0x800B,0,0)
   self.player.hide_window=lambda:post(self.hwnd,0x800E,0,0)
   self.player.choose_folder=lambda:post(self.hwnd,0x800D,0,0)
   update();timer(self.hwnd,1,500,None);show(self.hwnd,5)
   message=w.MSG()
   while getmessage(ctypes.byref(message),None,0,0)>0:
    if not dialogmsg(self.hwnd,ctypes.byref(message)):translate(ctypes.byref(message));dispatch(ctypes.byref(message))
  finally:
   self.player.show_window=None;self.player.choose_folder=None;self.player.hide_window=None
   if font:delete(font)
