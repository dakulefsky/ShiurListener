#!/usr/bin/env python3
"""Loopback-only shiur companion. Portable Windows bundle includes Python and VLC; source mode requires matching runtimes."""
import argparse, ctypes, ctypes.util, hmac, http.server, json, os, pathlib, secrets, sys, threading, time
EXTENSIONS={'.mp3','.m4a','.m4b','.wav','.ogg','.oga','.opus','.flac','.aac','.aiff','.aif','.wma'}
PORT=18473

class VLC:
    def __init__(self,options=()):
        if sys.platform=='win32':
            candidates=[pathlib.Path(__file__).resolve().parent/'runtime/vlc',pathlib.Path(os.environ.get('PROGRAMFILES','C:/Program Files'))/'VideoLAN/VLC',pathlib.Path(os.environ.get('PROGRAMFILES(X86)','C:/Program Files (x86)'))/'VideoLAN/VLC']
            directory=next((p for p in candidates if (p/'libvlc.dll').exists()),None)
            if not directory:raise RuntimeError('Install VLC from https://www.videolan.org/vlc/ (same architecture as Python).')
            self.dll_directory=os.add_dll_directory(str(directory));os.environ['VLC_PLUGIN_PATH']=str(directory/'plugins');lib=str(directory/'libvlc.dll')
        elif sys.platform=='darwin':
            os.environ.setdefault('VLC_PLUGIN_PATH','/Applications/VLC.app/Contents/MacOS/plugins');lib='/Applications/VLC.app/Contents/MacOS/lib/libvlc.dylib'
        else:lib=ctypes.util.find_library('vlc')
        if not lib:raise RuntimeError('VLC runtime not found. Install VLC first.')
        self.lib=ctypes.CDLL(lib)
        signatures={'libvlc_new':(ctypes.c_void_p,[ctypes.c_int,ctypes.POINTER(ctypes.c_char_p)]),'libvlc_release':(None,[ctypes.c_void_p]),'libvlc_media_player_new':(ctypes.c_void_p,[ctypes.c_void_p]),'libvlc_media_player_release':(None,[ctypes.c_void_p]),'libvlc_media_new_path':(ctypes.c_void_p,[ctypes.c_void_p,ctypes.c_char_p]),'libvlc_media_release':(None,[ctypes.c_void_p]),'libvlc_media_player_set_media':(None,[ctypes.c_void_p,ctypes.c_void_p]),'libvlc_media_player_play':(ctypes.c_int,[ctypes.c_void_p]),'libvlc_media_player_set_pause':(None,[ctypes.c_void_p,ctypes.c_int]),'libvlc_media_player_stop':(None,[ctypes.c_void_p]),'libvlc_media_player_get_time':(ctypes.c_longlong,[ctypes.c_void_p]),'libvlc_media_player_get_length':(ctypes.c_longlong,[ctypes.c_void_p]),'libvlc_media_player_set_time':(None,[ctypes.c_void_p,ctypes.c_longlong]),'libvlc_media_player_get_state':(ctypes.c_int,[ctypes.c_void_p]),'libvlc_media_player_set_rate':(ctypes.c_int,[ctypes.c_void_p,ctypes.c_float]),'libvlc_audio_set_volume':(ctypes.c_int,[ctypes.c_void_p,ctypes.c_int])}
        for name,(result,args) in signatures.items():fn=getattr(self.lib,name);fn.restype=result;fn.argtypes=args
        arguments=[b'--ignore-config',b'--no-video',b'--no-video-title-show',b'--no-lua',b'--no-metadata-network-access',b'--no-plugins-cache']+[option.encode('utf-8') for option in options]
        args=(ctypes.c_char_p*len(arguments))(*arguments)
        self.instance=self.lib.libvlc_new(len(arguments),args)
        if not self.instance:raise RuntimeError('VLC initialization failed.')
        self.player=self.lib.libvlc_media_player_new(self.instance)
        if not self.player:raise RuntimeError('VLC player initialization failed.')
    def load(self,path):
        media=self.lib.libvlc_media_new_path(self.instance,os.fsencode(path))
        if not media:raise RuntimeError('VLC could not open the recording.')
        self.lib.libvlc_media_player_stop(self.player);self.lib.libvlc_media_player_set_media(self.player,media);self.lib.libvlc_media_release(media)
    def play(self):
        if self.lib.libvlc_media_player_play(self.player)<0:raise RuntimeError('VLC could not start playback.')
    def pause(self):self.lib.libvlc_media_player_set_pause(self.player,1)
    def stop(self):self.lib.libvlc_media_player_stop(self.player)
    def seek(self,value):self.lib.libvlc_media_player_set_time(self.player,int(value*1000))
    def speed(self,value):
        if self.lib.libvlc_media_player_set_rate(self.player,value)<0:raise RuntimeError('Playback speed is unavailable for this recording.')
    def volume(self,value):self.lib.libvlc_audio_set_volume(self.player,round(value*100))
    def state(self):return {'position':max(0,self.lib.libvlc_media_player_get_time(self.player)/1000),'duration':max(0,self.lib.libvlc_media_player_get_length(self.player)/1000),'status':{0:'stopped',1:'loading',2:'loading',3:'playing',4:'paused',5:'stopped',6:'ended',7:'error'}.get(self.lib.libvlc_media_player_get_state(self.player),'error')}
    def close(self):self.stop();self.lib.libvlc_media_player_release(self.player);self.lib.libvlc_release(self.instance)

class Player:
    def __init__(self,root,data_dir,backend):
        self.root=pathlib.Path(root).resolve();self.data_dir=pathlib.Path(data_dir);self.data_dir.mkdir(parents=True,exist_ok=True)
        self.file=self.data_dir/'state.json';self.lock=threading.RLock();self.backend=backend;self.error='';self.pending=None;self.was_playing=False
        self.saved={'tracks':{},'currentId':None,'queue':[],'autoNext':False,'speed':1,'volume':1,'skipSeconds':15,'folders':[]}
        if self.file.exists():
            try:self.saved.update(json.loads(self.file.read_text('utf-8')))
            except (ValueError,OSError):raise RuntimeError('Cannot read saved companion state. Back up state.json before resetting it.')
        self.paths={};self.tracks=[]
        for path in sorted(self.root.rglob('*')):
            if not path.is_file() or path.suffix.lower() not in EXTENSIONS:continue
            real=path.resolve()
            if not real.is_relative_to(self.root):continue
            relative=path.relative_to(self.root).as_posix()
            import hashlib
            ident=hashlib.sha256((str(self.root)+'/'+relative).encode()).hexdigest()[:24]
            self.paths[ident]=real;self.tracks.append({'id':ident,'name':path.name,'source':relative})
        self.saved['queue']=[i for i in self.saved['queue'] if i in self.paths]
        if self.saved['currentId'] not in self.paths:self.saved['currentId']=None
        self.active=None;self.last_save=0;self.previous_status='stopped';self.hotkey_status=[];self.floating_bar=None;self.sleep_deadline=None;self.sleep_minutes=0;self.sleep_paused=False
        self.saved.setdefault('folders',[]);self.saved.setdefault('skipSeconds',15)
        for folder in self.saved['folders']:folder['trackIds']=[i for i in folder['trackIds'] if i in self.paths]
    def persist(self):
        temporary=self.file.with_suffix('.tmp');temporary.write_text(json.dumps(self.saved,ensure_ascii=False),'utf-8');os.replace(temporary,self.file)
    def capture(self):
        raw=self.backend.state() if self.active else {'position':0,'duration':0,'status':'stopped'}
        if raw['status']=='ended' and raw['duration']:raw['position']=raw['duration']
        if self.active and self.pending is None and raw['status'] not in ('loading','stopped','error'):
            self.saved['tracks'][self.active]={'position':raw['duration'] if raw['status']=='ended' and raw['duration'] else raw['position'],'duration':raw['duration']}
        return raw
    def snapshot(self):
        raw=self.capture();ident=self.saved['currentId'];progress=self.saved['tracks'].get(ident,{})
        if not self.active:raw={'position':progress.get('position',0),'duration':progress.get('duration',0),'status':'paused'}
        return {**raw,'currentId':ident,'speed':self.saved['speed'],'volume':self.saved['volume'],'autoNext':self.saved['autoNext'],'queue':self.saved['queue'],'error':self.error,'skipSeconds':self.saved['skipSeconds'],'folders':self.saved['folders'],'hotkeys':self.hotkey_status,'sleepMinutes':self.sleep_minutes,'sleepRemaining':max(0,int(self.sleep_deadline-time.monotonic()+.999)) if self.sleep_deadline else 0,'floatingAvailable':bool(self.floating_bar and self.floating_bar.hwnd),'floatingStatus':self.floating_bar.status if self.floating_bar else ''}
    def library(self):return [{**t,**self.saved['tracks'].get(t['id'],{})} for t in self.tracks]
    def load(self,ident,position=None,autoplay=False):
        if ident not in self.paths:raise ValueError('Unknown recording. Restart the companion to rescan your selected folder.')
        if not self.paths[ident].resolve().is_relative_to(self.root):raise ValueError('The recording no longer resolves inside the selected folder.')
        if not self.paths[ident].is_file():raise ValueError('The recording is missing or the drive is disconnected.')
        self.capture();self.backend.load(self.paths[ident]);self.active=ident;self.saved['currentId']=ident;self.error='';self.sleep_paused=False
        progress=self.saved['tracks'].get(ident,{})
        start=progress.get('position',0) if position is None else position
        self.pending={'position':max(0,float(start)),'autoplay':autoplay,'started':time.monotonic()};self.backend.volume(0);self.backend.play()
        self.persist()
    def advance(self,delta):
        queue=self.saved['queue'];current=self.saved['currentId']
        if current in queue:
            index=queue.index(current)+delta
            if 0<=index<len(queue):self.load(queue[index],autoplay=True)
    def command(self,data):
        with self.lock:
            op=data.get('op')
            if not isinstance(op,str):raise ValueError('Command op is required.')
            if op=='toggle':
                raw=self.backend.state() if self.active else {'status':'paused'}
                op='pause' if (self.pending and self.pending['autoplay']) or (not self.pending and raw['status']=='playing') else 'play'
            if op=='skip':
                if not self.active:raise ValueError('Select a recording first.')
                raw=self.backend.state();value=max(0,min(raw['duration'],raw['position']+float(data.get('direction',1))*self.saved['skipSeconds']))
                return self.command({'op':'seek','value':value})
            if op=='speed_step':
                rates=[.75,1,1.25,1.5,1.75,2];index=rates.index(self.saved['speed']);index=max(0,min(len(rates)-1,index+int(data.get('direction',1))))
                return self.command({'op':'speed','value':rates[index]})
            if op=='sleep_timer':
                minutes=data.get('minutes',0)
                if not isinstance(minutes,(int,float)) or not 0<=minutes<=180:raise ValueError('Sleep timer must be between 0 and 180 minutes.')
                self.sleep_minutes=minutes;self.sleep_deadline=time.monotonic()+minutes*60 if minutes else None
                return self.snapshot()
            if op=='floating_toggle':
                if not self.floating_bar:raise ValueError('Floating bar is available in the Windows companion.')
                self.floating_bar.toggle();return self.snapshot()
            if op=='floating_theme':
                theme=data.get('theme',{})
                if not isinstance(theme,dict):raise ValueError('Invalid floating bar theme.')
                import re
                clean={}
                for key in ['primary','onPrimary','surface','onSurface','surfaceContainer']:
                    value=theme.get(key)
                    if isinstance(value,str) and re.fullmatch(r'#[0-9a-fA-F]{6}',value):clean[key]=value
                family=theme.get('fontFamily')
                if isinstance(family,str) and 0<len(family)<=100:clean['fontFamily']=family
                self.saved['floatingTheme']=clean;self.persist();return self.snapshot()
            if op.startswith('folder_'):
                folders=self.saved['folders'];folder=next((f for f in folders if f['id']==data.get('id')),None)
                if op in ('folder_create','folder_rename'):
                    name=str(data.get('name','')).strip()
                    if not name or len(name)>160:raise ValueError('Use a folder name of 1–160 characters.')
                if op=='folder_create':folders.append({'id':secrets.token_hex(12),'name':name,'trackIds':[]})
                elif not folder:raise ValueError('Folder not found.')
                elif op=='folder_rename':folder['name']=name
                elif op=='folder_delete':self.saved['folders']=[f for f in folders if f is not folder]
                elif op in ('folder_add','folder_remove'):
                    ident=data.get('trackId')
                    if ident not in self.paths:raise ValueError('Recording not found.')
                    if op=='folder_add' and ident not in folder['trackIds']:folder['trackIds'].append(ident)
                    if op=='folder_remove':folder['trackIds']=[i for i in folder['trackIds'] if i!=ident]
                else:raise ValueError('Unknown folder operation.')
                self.persist();return self.snapshot()
            if op=='skip_interval':
                value=data.get('value')
                if value not in (10,15,60):raise ValueError('Choose 10, 15 or 60 seconds.')
                self.saved['skipSeconds']=value;self.persist();return self.snapshot()
            if op=='load':
                queue=data.get('queue',[])
                if not isinstance(queue,list) or any(i not in self.paths for i in queue):raise ValueError('Invalid queue.')
                self.saved['queue']=list(dict.fromkeys(queue));self.load(data['id'],data.get('position'),False)
            elif op=='play':
                self.sleep_paused=False
                if not self.active:
                    if not self.saved['currentId']:raise ValueError('Select a recording first.')
                    self.load(self.saved['currentId'],autoplay=True)
                elif self.pending:self.pending['autoplay']=True
                else:self.backend.play()
            elif op=='pause':
                if self.pending:self.pending['autoplay']=False
                self.backend.pause();self.capture()
            elif op=='seek':
                value=float(data['value'])
                if not 0<=value<1e8:raise ValueError('Invalid position.')
                if self.pending:self.pending['position']=value
                else:self.backend.seek(value)
            elif op=='speed':
                value=float(data['value'])
                if value not in (.75,1,1.25,1.5,1.75,2):raise ValueError('Invalid speed.')
                self.backend.speed(value);self.saved['speed']=value
            elif op=='volume':
                value=float(data['value'])
                if not 0<=value<=1:raise ValueError('Invalid volume.')
                self.backend.volume(value);self.saved['volume']=value
            elif op=='autonext':self.saved['autoNext']=data.get('value') is True
            elif op=='next':self.advance(1)
            elif op=='previous':self.advance(-1)
            elif op=='stop':self.sleep_deadline=None;self.sleep_minutes=0;self.capture();self.backend.stop();self.pending=None;self.active=None
            else:raise ValueError('Unknown command.')
            result=self.snapshot();self.persist();return result
    def tick(self):
        with self.lock:
            if self.sleep_deadline and time.monotonic()>=self.sleep_deadline:
                self.sleep_deadline=None;self.sleep_minutes=0;self.sleep_paused=True;self.command({'op':'pause'})
            raw=self.capture()
            if self.pending:
                if raw['status']=='error' or time.monotonic()-self.pending['started']>20:
                    self.pending=None;self.backend.stop();self.error='VLC could not load this recording.'
                elif raw['status'] in ('playing','paused') and raw['duration']>0:
                    pending=self.pending;self.pending=None
                    self.backend.seek(min(pending['position'],raw['duration']))
                    self.backend.speed(self.saved['speed'])
                    if not pending['autoplay']:self.backend.pause()
                    self.backend.volume(self.saved['volume'])
            elif raw['status']=='ended' and self.was_playing and self.saved['autoNext'] and not self.sleep_paused:self.advance(1)
            self.was_playing=raw['status']=='playing'
            if raw['status']=='error':self.error='VLC playback failed. Check the recording and your audio output.'
            if time.monotonic()-self.last_save>=1 or raw['status']!=self.previous_status:self.persist();self.last_save=time.monotonic()
            self.previous_status=raw['status']

class Server(http.server.ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,address,player,token):self.player=player;self.token=token;super().__init__(address,Handler)
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def reply(self,code,data):
        body=json.dumps(data,ensure_ascii=False).encode();self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
    def authorized(self):
        if self.headers.get('Origin') is not None:return False
        if self.headers.get('Host') not in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'):return False
        return hmac.compare_digest(self.headers.get('Authorization','').encode('utf-8'),('Bearer '+self.server.token).encode('utf-8'))
    def do_GET(self):
        if not self.authorized():return self.reply(403,{'error':'Pairing required. Browser-origin requests are not accepted.'})
        with self.server.player.lock:
            if self.path=='/v1/state':return self.reply(200,self.server.player.snapshot())
            if self.path=='/v1/library':return self.reply(200,{'tracks':self.server.player.library()})
        self.reply(404,{'error':'Unknown route.'})
    def do_POST(self):
        if not self.authorized():return self.reply(403,{'error':'Pairing required.'})
        if self.path!='/v1/command':return self.reply(404,{'error':'Unknown route.'})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=262144:return self.reply(413,{'error':'Invalid request size.'})
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.reply(415,{'error':'JSON required.'})
            self.connection.settimeout(5);data=json.loads(self.rfile.read(size))
            if not isinstance(data,dict):raise ValueError('Expected an object.')
            result=self.server.player.command(data);self.reply(200,result)
        except (ValueError,KeyError,TypeError,OverflowError) as e:self.reply(400,{'error':str(e)})
        except Exception as e:self.reply(500,{'error':str(e)})

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--folder');parser.add_argument('--data-dir');parser.add_argument('--no-floating-bar',action='store_true');args=parser.parse_args()
    folder=args.folder
    if not folder:
        if sys.platform=='win32':
            # Embedded Python excludes tkinter; use the native Windows folder picker.
            import base64,subprocess
            script="""[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName System.Windows.Forms
$picker = New-Object System.Windows.Forms.FolderBrowserDialog
$picker.Description = 'Select your shiur recordings folder'
$picker.ShowNewFolderButton = $false
if ($picker.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { [Console]::Write($picker.SelectedPath) }
$picker.Dispose()
"""
            powershell=pathlib.Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
            result=subprocess.run([str(powershell),'-NoProfile','-STA','-NonInteractive','-EncodedCommand',base64.b64encode(script.encode('utf-16le')).decode('ascii')],capture_output=True,text=True,encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW,check=True)
            folder=result.stdout.strip()
        else:
            import tkinter as tk
            from tkinter import filedialog
            ui=tk.Tk();ui.withdraw();folder=filedialog.askdirectory(title='Select your shiur recordings folder');ui.destroy()
    if not folder:return
    if not pathlib.Path(folder).is_dir():raise RuntimeError('Select an existing recordings folder.')
    data_dir=args.data_dir or str(pathlib.Path(os.environ.get('LOCALAPPDATA',pathlib.Path.home()/'.local/share'))/'ShiurPlayerCompanion')
    backend=VLC();player=Player(folder,data_dir,backend);token=secrets.token_urlsafe(24)
    server=Server(('127.0.0.1',PORT),player,token)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    import importlib.util
    spec=importlib.util.spec_from_file_location('shiur_hotkeys',pathlib.Path(__file__).with_name('hotkeys.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    hotkeys=module.GlobalHotkeys(player)
    bar_spec=importlib.util.spec_from_file_location('shiur_floating_bar',pathlib.Path(__file__).with_name('floating_bar.py'));bar_module=importlib.util.module_from_spec(bar_spec);bar_spec.loader.exec_module(bar_module)
    if args.no_floating_bar:player.saved['floatingVisible']=False
    bar=bar_module.FloatingBar(player);player.floating_bar=bar;bar.start();hotkeys.start()
    print('\nSHIUR PLAYER COMPANION\nKeep this window open. Closing it stops audio.\n')
    print('Pairing code (paste into the Otzaria plugin):\n\n'+token+'\n',flush=True)
    print(f'{len(player.tracks)} recordings found. Listening only on 127.0.0.1:{PORT}.\nPress Ctrl+C to stop. No audio starts automatically.',flush=True)
    try:
        while True:player.tick();time.sleep(.15)
    except KeyboardInterrupt:pass
    finally:
        hotkeys.close();bar.close();server.shutdown()
        with player.lock:player.capture();player.persist();backend.close()
if __name__=='__main__':
    try:main()
    except Exception as e:print('\nCompanion could not start: '+str(e),file=sys.stderr);sys.exit(1)
