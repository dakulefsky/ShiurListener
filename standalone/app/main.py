"""Standalone local shiur player entrypoint. No network service or pairing."""
import argparse,ctypes,os,pathlib,sys,threading
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
runtime=pathlib.Path(__file__).resolve().parent/'runtime'
if (runtime/'tcl/tcl8.6').is_dir():
 os.environ['TCL_LIBRARY']=str(runtime/'tcl/tcl8.6')
 os.environ['TK_LIBRARY']=str(runtime/'tcl/tk8.6')
from engine import Player,VLC
from controller import LibraryController
from floating_bar import FloatingBar
from hotkeys import GlobalHotkeys
from window import PlayerWindow

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--folder');parser.add_argument('--data-dir');args=parser.parse_args()
 if sys.platform!='win32':raise RuntimeError('This desktop build is for Windows.')
 data=args.data_dir or str(pathlib.Path(os.environ.get('LOCALAPPDATA',pathlib.Path.home()))/'ShiurPlayerStandalone')
 backend=VLC();player=None;bar=None;keys=None;worker=None;stop=threading.Event()
 try:
  player=Player(args.folder,data,backend);controller=LibraryController(player);player.saved['language']='en'
  player.saved.setdefault('floatingVisible',False)
  player.saved.setdefault('floatingTheme',{'primary':'#4169E1','onPrimary':'#FFFFFF','surface':'#FFFFFF','onSurface':'#182235','surfaceContainer':'#EDF1F8','fontFamily':'Rubik'})
  if player.saved['floatingTheme'].get('primary')=='#245C49':
   player.saved['floatingTheme'].update(primary='#4169E1',surface='#FFFFFF',onSurface='#182235',surfaceContainer='#EDF1F8')
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
  finally:backend.close()

if __name__=='__main__':
 try:main()
 except Exception as error:
  if sys.platform=='win32':ctypes.windll.user32.MessageBoxW(None,str(error),'Shiur Player',0x10)
  else:print(str(error),file=sys.stderr)
  sys.exit(1)
