"""Standalone local shiur player entrypoint. No network service or pairing."""
import argparse,ctypes,json,os,pathlib,sys,threading
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
runtime=pathlib.Path(__file__).resolve().parent/'runtime'
if (runtime/'tcl/tcl8.6').is_dir():
 os.environ['TCL_LIBRARY']=str(runtime/'tcl/tcl8.6')
 os.environ['TK_LIBRARY']=str(runtime/'tcl/tk8.6')
from windows_identity import acquire_instance,configure_taskbar,configure_dpi
from engine import Player,VLC
from controller import LibraryController
from floating_bar import FloatingBar
from hotkeys import GlobalHotkeys
from window import PlayerWindow

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--folder');parser.add_argument('--data-dir');parser.add_argument('--open-file');args=parser.parse_args()
 if sys.platform!='win32':raise RuntimeError('This desktop build is for Windows.')
 data=pathlib.Path(args.data_dir or pathlib.Path(os.environ.get('LOCALAPPDATA',pathlib.Path.home()))/'ShiurPlayerStandalone')
 open_file=pathlib.Path(args.open_file).expanduser().resolve() if args.open_file else None
 if open_file:
  from engine import EXTENSIONS
  if not open_file.is_file() or open_file.suffix.lower() not in EXTENSIONS:raise ValueError('Choose an existing supported audio recording.')
  if args.folder and pathlib.Path(args.folder).resolve()!=open_file.parent:raise ValueError('The selected audio file and library folder do not match.')
  args.folder=str(open_file.parent)
 configure_dpi()
 configure_taskbar()
 instance=acquire_instance()
 if instance is None:
  if open_file:
   data.mkdir(parents=True,exist_ok=True)
   request=data/'open-request.json';temporary=data/'open-request.tmp'
   temporary.write_text(json.dumps({'path':str(open_file)}),encoding='utf-8')
   os.replace(temporary,request)
  return
 backend=None;player=None;bar=None;keys=None;worker=None;stop=threading.Event()
 try:
  backend=VLC()
  player=Player(args.folder,data,backend);controller=LibraryController(player);player.saved['language']='en'
  if open_file:
   ident=next((ident for ident,path in player.paths.items() if path.resolve()==open_file),None)
   if ident is None:raise ValueError('The selected audio file could not be added to the library.')
   controller.view='all';controller.selected=ident;player.load(ident,autoplay=True)
  player.saved.setdefault('floatingVisible',False)
  player.saved.setdefault('floatingTheme',{'primary':'#6558D3','onPrimary':'#FFFFFF','surface':'#FFFFFF','onSurface':'#242332','surfaceContainer':'#E9E7F0','fontFamily':'Rubik'})
  if player.saved['floatingTheme'].get('primary') in ('#245C49','#4169E1','#214CDB','#526BFF','#4263EB'):
   player.saved['floatingTheme'].update(primary='#6558D3',surface='#FFFFFF',onSurface='#242332',surfaceContainer='#E9E7F0')
  bar=FloatingBar(player);player.floating_bar=bar
  def shortcuts(enabled):
   nonlocal keys
   if keys:keys.close();keys=None
   if enabled:keys=GlobalHotkeys(player);keys.start()
   else:player.hotkey_status=[]
   with player.lock:player.saved['globalShortcuts']=bool(enabled);player.persist()
  shortcuts(player.saved.get('globalShortcuts',False));bar.start()
  def tick():
   while not stop.wait(.15):
    try:player.tick()
    except Exception as error:player.error=str(error)
  worker=threading.Thread(target=tick,daemon=True);worker.start()
  PlayerWindow(player,controller,shortcuts).run()
 finally:
  stop.set()
  if worker:worker.join(timeout=2)
  if keys:keys.close()
  if bar:bar.close()
  try:
   if player:
    with player.lock:player.capture();player.persist()
  finally:
   try:
    if backend:backend.close()
   finally:instance.close()

if __name__=='__main__':
 try:main()
 except Exception as error:
  if sys.platform=='win32':ctypes.windll.user32.MessageBoxW(None,str(error),'Shiur Player',0x10)
  else:print(str(error),file=sys.stderr)
  sys.exit(1)

