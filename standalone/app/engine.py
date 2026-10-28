#!/usr/bin/env python3
"""Local shiur audio engine. No server, browser, plugin or pairing process."""
import ctypes, ctypes.util, functools, json, math, os, pathlib, secrets, sys, threading, time
EXTENSIONS={'.mp3','.m4a','.m4b','.wav','.ogg','.oga','.opus','.flac','.aac','.aiff','.aif','.wma'}

def synchronized(method):
    @functools.wraps(method)
    def call(self,*args,**kwargs):
        with self.lock:return method(self,*args,**kwargs)
    return call

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
        signatures={'libvlc_new':(ctypes.c_void_p,[ctypes.c_int,ctypes.POINTER(ctypes.c_char_p)]),'libvlc_release':(None,[ctypes.c_void_p]),'libvlc_media_player_new':(ctypes.c_void_p,[ctypes.c_void_p]),'libvlc_media_player_release':(None,[ctypes.c_void_p]),'libvlc_media_new_path':(ctypes.c_void_p,[ctypes.c_void_p,ctypes.c_char_p]),'libvlc_media_release':(None,[ctypes.c_void_p]),'libvlc_media_player_set_media':(None,[ctypes.c_void_p,ctypes.c_void_p]),'libvlc_media_player_play':(ctypes.c_int,[ctypes.c_void_p]),'libvlc_media_player_set_pause':(None,[ctypes.c_void_p,ctypes.c_int]),'libvlc_media_player_stop':(None,[ctypes.c_void_p]),'libvlc_media_player_get_time':(ctypes.c_longlong,[ctypes.c_void_p]),'libvlc_media_player_get_length':(ctypes.c_longlong,[ctypes.c_void_p]),'libvlc_media_player_set_time':(None,[ctypes.c_void_p,ctypes.c_longlong]),'libvlc_media_player_get_state':(ctypes.c_int,[ctypes.c_void_p]),'libvlc_media_player_set_rate':(ctypes.c_int,[ctypes.c_void_p,ctypes.c_float]),'libvlc_audio_set_volume':(ctypes.c_int,[ctypes.c_void_p,ctypes.c_int]),'libvlc_audio_equalizer_new':(ctypes.c_void_p,[]),'libvlc_audio_equalizer_release':(None,[ctypes.c_void_p]),'libvlc_audio_equalizer_get_band_count':(ctypes.c_uint,[]),'libvlc_audio_equalizer_set_preamp':(ctypes.c_int,[ctypes.c_void_p,ctypes.c_float]),'libvlc_audio_equalizer_set_amp_at_index':(ctypes.c_int,[ctypes.c_void_p,ctypes.c_float,ctypes.c_uint]),'libvlc_media_player_set_equalizer':(ctypes.c_int,[ctypes.c_void_p,ctypes.c_void_p])}
        for name,(result,args) in signatures.items():fn=getattr(self.lib,name);fn.restype=result;fn.argtypes=args
        arguments=[b'--ignore-config',b'--no-video',b'--no-video-title-show',b'--no-lua',b'--no-metadata-network-access',b'--no-plugins-cache']+[option.encode('utf-8') for option in options]
        args=(ctypes.c_char_p*len(arguments))(*arguments)
        self.instance=self.lib.libvlc_new(len(arguments),args)
        if not self.instance:raise RuntimeError('VLC initialization failed.')
        self.player=self.lib.libvlc_media_player_new(self.instance)
        self.equalizer=None
        if not self.player:
            self.lib.libvlc_release(self.instance)
            raise RuntimeError('VLC player initialization failed.')
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
    def audio_settings(self,settings):
        values={name:max(-6.0,min(6.0,float(settings.get(name,0)))) for name in ('bass','body','clarity','treble')}
        if not any(values.values()):
            if self.equalizer:
                self.lib.libvlc_media_player_set_equalizer(self.player,None)
                self.lib.libvlc_audio_equalizer_release(self.equalizer);self.equalizer=None
            return
        eq=self.lib.libvlc_audio_equalizer_new()
        if not eq:raise RuntimeError('VLC could not create the audio equalizer.')
        try:
            self.lib.libvlc_audio_equalizer_set_preamp(eq,0.0)
            bands=int(self.lib.libvlc_audio_equalizer_get_band_count())
            gains=[values['bass'],values['bass']*.65,values['body']*.65,values['body'],values['body']*.6,values['clarity']*.75,values['clarity'],values['treble']*.8,values['treble'],values['treble']*.7]
            for index,gain in enumerate(gains[:bands]):self.lib.libvlc_audio_equalizer_set_amp_at_index(eq,float(gain),index)
            if self.lib.libvlc_media_player_set_equalizer(self.player,eq)<0:raise RuntimeError('VLC could not apply the audio equalizer.')
            previous=self.equalizer;self.equalizer=eq;eq=None
            if previous:self.lib.libvlc_audio_equalizer_release(previous)
        finally:
            if eq:self.lib.libvlc_audio_equalizer_release(eq)
    def state(self):return {'position':max(0,self.lib.libvlc_media_player_get_time(self.player)/1000),'duration':max(0,self.lib.libvlc_media_player_get_length(self.player)/1000),'status':{0:'stopped',1:'loading',2:'loading',3:'playing',4:'paused',5:'stopped',6:'ended',7:'error'}.get(self.lib.libvlc_media_player_get_state(self.player),'error')}
    def close(self):
        self.stop()
        if self.equalizer:self.lib.libvlc_audio_equalizer_release(self.equalizer);self.equalizer=None
        self.lib.libvlc_media_player_release(self.player);self.lib.libvlc_release(self.instance)

class Player:
    def __init__(self,root,data_dir,backend):
        self.root=pathlib.Path(root).resolve() if root else None;self.data_dir=pathlib.Path(data_dir);self.data_dir.mkdir(parents=True,exist_ok=True)
        self.file=self.data_dir/'state.json';self.lock=threading.RLock();self.backend=backend;self.error='';self.pending=None;self.was_playing=False
        self.saved={'tracks':{},'currentId':None,'queue':[],'autoNext':False,'speed':1,'volume':1,'audioEnhancement':{'bass':0,'body':0,'clarity':0,'treble':0},'speechEnhancementEnabled':False,'skipSeconds':15,'folders':[],'language':'en'}
        if self.file.exists():
            try:
                from profile_backup import FORMAT,_read,_validate
                stored=_read(self.file)
                if not isinstance(stored,dict):raise ValueError('Saved state must be an object.')
                self.saved=_validate({'format':FORMAT,'version':1,'state':{**self.saved,**stored}})
            except (ValueError,OSError):raise RuntimeError('Cannot read saved player state. Back up state.json before resetting it.')
        self.active=None;self.last_save=0;self.previous_status='stopped';self.hotkey_status=[];self.floating_bar=None;self.sleep_deadline=None;self.sleep_minutes=0;self.sleep_paused=False
        self.sleep_at_end=False;self.loop_a=None;self.loop_b=None;self.loop_track=None;self.loop_seek_at=0
        self.seek_target=None
        self.paths={};self.tracks=[];self.library_revision=0;self.choose_folder=None;self.show_window=None;self.hide_window=None
        self.saved.setdefault('folders',[]);self.saved.setdefault('skipSeconds',15);self.saved.setdefault('audioEnhancement',{'bass':0,'body':0,'clarity':0,'treble':0});self.saved.setdefault('speechEnhancementEnabled',False)
        selected=self.root or (pathlib.Path(self.saved['libraryRoot']) if self.saved.get('libraryRoot') else None)
        if selected:
            self.root=selected.resolve()
            if self.root.is_dir():self.scan(self.root)
            else:self.error='The recordings folder is missing or disconnected. Reconnect it, then click Refresh.'
    def speech_cache_path(self,ident):
        source=self.paths.get(ident)
        if source is None:return None
        try:stat=source.stat()
        except OSError:return None
        return self.data_dir/'speech-cache'/f'{ident}-{stat.st_size}-{stat.st_mtime_ns}-hush-v1.0.0.wav'
    def scan(self,root=None):
        with self.lock:
            selected=pathlib.Path(root).resolve() if root else self.root
            if selected is None:raise ValueError('Choose a recordings folder first.')
            if not selected.is_dir():raise ValueError('The recordings folder is missing or disconnected.')
            paths={};tracks=[]
            import hashlib
            for path in sorted(selected.rglob('*')):
                if not path.is_file() or path.suffix.lower() not in EXTENSIONS:continue
                real=path.resolve()
                if not real.is_relative_to(selected):continue
                relative=path.relative_to(selected).as_posix()
                ident=hashlib.sha256((str(selected)+'/'+relative).encode()).hexdigest()[:24]
                paths[ident]=path;tracks.append({'id':ident,'name':path.name,'source':relative})
            self.capture()
            if self.active and self.active not in paths:self.backend.stop();self.active=None;self.pending=None;self.clear_loop()
            self.root=selected;self.paths=paths;self.tracks=tracks;self.library_revision+=1;self.error=''
            self.saved['libraryRoot']=str(selected)
            self.saved['queue']=[i for i in self.saved['queue'] if i in paths]
            if self.saved['currentId'] not in paths:self.saved['currentId']=None
            self.persist()
            return self.snapshot()
    @synchronized
    def persist(self):
        temporary=self.file.with_suffix('.tmp')
        with temporary.open('w',encoding='utf-8') as stream:
            json.dump(self.saved,stream,ensure_ascii=False);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,self.file)
    @synchronized
    def capture(self):
        raw=self.backend.state() if self.active else {'position':0,'duration':0,'status':'stopped'}
        if self.seek_target and raw['status'] in ('playing','paused'):
            target=self.seek_target
            if abs(raw['position']-target['position'])<=.3 or time.monotonic()>=target['expires']:self.seek_target=None
            else:raw={**raw,'position':target['position']}
        if raw['status']=='ended' and raw['duration']:raw['position']=raw['duration']
        if self.active and (self.pending is not None or raw['status'] not in ('loading','stopped','error')):
            previous=self.saved['tracks'].get(self.active,{})
            position=self.pending['position'] if self.pending else raw['position']
            completed=not self.pending and raw['status']=='ended' and self.loop_b is None
            if raw['status']=='ended' and self.loop_b is not None and not self.pending:position=self.loop_a
            changed=position!=previous.get('position') or completed!=previous.get('completed',False)
            self.saved['tracks'][self.active]={**previous,'position':position,'duration':raw['duration'] or previous.get('duration',0),'completed':bool(completed),'lastListenedAt':time.time_ns() if changed else previous.get('lastListenedAt',0)}
        return raw
    @synchronized
    def snapshot(self):
        raw=self.capture();ident=self.saved['currentId'];progress=self.saved['tracks'].get(ident,{})
        if self.pending:raw={**raw,'position':self.pending['position'],'duration':raw['duration'] or progress.get('duration',0),'status':'loading','playRequested':self.pending['autoplay']}
        if not self.active:raw={'position':progress.get('position',0),'duration':progress.get('duration',0),'status':'paused'}
        if self.sleep_paused and raw['status']=='ended':raw={**raw,'status':'paused'}
        return {**raw,'currentId':ident,'speed':self.saved['speed'],'volume':self.saved['volume'],'autoNext':self.saved['autoNext'],'queue':self.saved['queue'],'error':self.error,'skipSeconds':self.saved['skipSeconds'],'folders':self.saved['folders'],'hotkeys':self.hotkey_status,'sleepMinutes':self.sleep_minutes,'sleepAtEnd':self.sleep_at_end,'loopA':self.loop_a,'loopB':self.loop_b,'sleepRemaining':max(0,int(self.sleep_deadline-time.monotonic()+.999)) if self.sleep_deadline else 0,'floatingAvailable':bool(self.floating_bar and self.floating_bar.hwnd),'floatingStatus':self.floating_bar.status if self.floating_bar else '', 'loaded':self.active is not None,'libraryCount':len(self.tracks),'folderName':self.root.name if self.root else '', 'hasFolder':self.root is not None,'libraryRevision':self.library_revision,'language':self.saved.get('language','en')}
    @synchronized
    def library(self):return [{**t,**self.saved['tracks'].get(t['id'],{})} for t in self.tracks]
    @synchronized
    def clear_loop(self):self.loop_a=None;self.loop_b=None;self.loop_track=None;self.loop_seek_at=0
    @synchronized
    def seek_backend(self,value):
        self.backend.seek(value)
        # VLC applies seeks asynchronously; keep a requested place through an
        # immediate pause/close until the decoder reports the new position.
        reported=self.backend.state()['position']
        self.seek_target=None if abs(reported-value)<=.3 else {'position':value,'expires':time.monotonic()+2}
    @synchronized
    def load(self,ident,position=None,autoplay=False):
        if ident not in self.paths:raise ValueError('Unknown recording. Rescan your selected recordings folder.')
        if not self.paths[ident].resolve().is_relative_to(self.root):raise ValueError('The recording no longer resolves inside the selected folder.')
        if not self.paths[ident].is_file():raise ValueError('The recording is missing or the drive is disconnected.')
        self.capture()
        progress=self.saved['tracks'].get(ident,{})
        start=(0 if progress.get('completed') else progress.get('position',0)) if position is None else position
        start=float(start)
        if not math.isfinite(start) or not 0<=start<1e8:raise ValueError('Invalid position.')
        if progress.get('duration'):start=min(start,progress['duration'])
        self.active=None;self.pending=None;self.saved['currentId']=ident;self.error='';self.sleep_paused=False;self.seek_target=None
        rate=progress.get('speed',1)
        self.saved['speed']=rate if rate in (.5,.75,1,1.25,1.5,1.75,2) else 1
        if self.loop_track!=ident:self.clear_loop()
        try:
            source=self.paths[ident]
            if self.saved.get('speechEnhancementEnabled'):
                enhanced=self.speech_cache_path(ident)
                if enhanced and enhanced.is_file():source=enhanced
            self.backend.load(source);self.active=ident
            self.pending={'position':start,'autoplay':autoplay,'started':time.monotonic()}
            if hasattr(self.backend,'audio_settings'):self.backend.audio_settings(self.saved.get('audioEnhancement',{}))
            self.backend.volume(0);self.backend.play()
        except Exception as error:
            self.fail_load(str(error));self.persist();raise
        self.capture()
        self.persist()
    def fail_load(self,message):
        # Keep the captured resume position and make the next Play a fresh load.
        self.pending=None;self.active=None;self.seek_target=None;self.was_playing=False
        try:self.backend.stop()
        except Exception:pass # Preserve the original decoder failure.
        self.error=message
    @synchronized
    def advance(self,delta):
        queue=self.saved['queue'];current=self.saved['currentId']
        if current in queue:
            index=queue.index(current)+delta
            if 0<=index<len(queue):self.load(queue[index],autoplay=True)
    def command(self,data):
        with self.lock:
            op=data.get('op')
            if not isinstance(op,str):raise ValueError('Command op is required.')
            if op=='rescan':return self.scan()
            if op=='choose_folder':
                if not self.choose_folder:raise ValueError('Open the player window to choose a recordings folder.')
                self.choose_folder();return self.snapshot()
            if op=='show_window':
                if self.show_window:self.show_window()
                return self.snapshot()
            if op=='hide_window':
                if self.hide_window:self.hide_window()
                return self.snapshot()
            if op=='language':
                if data.get('value') not in ('he','en'):raise ValueError('Choose Hebrew or English.')
                self.saved['language']=data['value'];self.persist();return self.snapshot()
            if op=='toggle':
                raw=self.backend.state() if self.active else {'status':'paused'}
                op='pause' if (self.pending and self.pending['autoplay']) or (not self.pending and raw['status']=='playing') else 'play'
            if op=='skip':
                if not self.saved['currentId']:raise ValueError('Select a recording first.')
                raw=self.snapshot();value=max(0,raw['position']+float(data.get('direction',1))*self.saved['skipSeconds'])
                if raw['duration']:value=min(raw['duration'],value)
                return self.command({'op':'seek','value':value})
            if op=='speed_step':
                rates=[.5,.75,1,1.25,1.5,1.75,2];index=rates.index(self.saved['speed']);index=max(0,min(len(rates)-1,index+int(data.get('direction',1))))
                return self.command({'op':'speed','value':rates[index]})
            if op=='speed_cycle':
                cycle=[1,1.5,2,.5]
                phase=cycle.index(self.saved['speed']) if self.saved['speed'] in cycle else -1
                return self.command({'op':'speed','value':cycle[(phase+1)%len(cycle)]})
            if op=='sleep_timer':
                if data.get('mode')=='end':
                    if not self.saved['currentId']:raise ValueError('Select a recording first.')
                    self.sleep_at_end=True;self.sleep_minutes=0;self.sleep_deadline=None;self.clear_loop()
                    return self.snapshot()
                minutes=data.get('minutes',0)
                if not isinstance(minutes,(int,float)) or not math.isfinite(minutes) or not 0<=minutes<=180:raise ValueError('Sleep timer must be between 0 and 180 minutes.')
                self.sleep_at_end=False;self.sleep_minutes=minutes;self.sleep_deadline=time.monotonic()+minutes*60 if minutes else None
                return self.snapshot()
            if op in ('loop_a','loop_b','loop_clear'):
                if op=='loop_clear':self.clear_loop();return self.snapshot()
                state=self.snapshot()
                if not state['currentId']:raise ValueError('Select a recording first.')
                if op=='loop_a':self.loop_track=state['currentId'];self.loop_a=state['position'];self.loop_b=None
                else:
                    if self.loop_a is None or self.loop_track!=state['currentId']:raise ValueError('Set the start of the repeat section first.')
                    if state['position']<self.loop_a+.5:raise ValueError('The end must be at least half a second after the start.')
                    self.loop_b=state['position'];self.sleep_at_end=False
                self.loop_seek_at=0;return self.snapshot()
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
                    if any(f['name'].casefold()==name.casefold() and (op=='folder_create' or f['id']!=data.get('id')) for f in folders):raise ValueError('A collection with that name already exists.')
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
                self.load(data['id'],data.get('position'),False);self.saved['queue']=list(dict.fromkeys(queue))
            elif op=='play':
                self.sleep_paused=False
                if not self.active:
                    if not self.saved['currentId']:
                        if not self.tracks:raise ValueError('No recordings found. Choose a recordings folder, then rescan.')
                        self.saved['currentId']=self.tracks[0]['id'];self.saved['queue']=[t['id'] for t in self.tracks]
                    self.load(self.saved['currentId'],autoplay=True)
                elif self.pending:self.pending['autoplay']=True
                elif self.backend.state()['status'] in ('ended','stopped','error'):
                    self.load(self.saved['currentId'],autoplay=True)
                else:self.backend.play()
            elif op=='pause':
                if self.pending:self.pending['autoplay']=False
                else:self.backend.pause()
                self.capture()
            elif op=='seek':
                value=float(data['value'])
                if not math.isfinite(value) or not 0<=value<1e8:raise ValueError('Invalid position.')
                if not self.saved['currentId']:raise ValueError('Select a recording first.')
                raw=self.snapshot()
                if raw['duration']:value=min(raw['duration'],value)
                if not self.active or raw['status'] in ('ended','stopped','error'):
                    self.load(self.saved['currentId'],position=value,autoplay=False)
                    return self.snapshot()
                if self.pending:self.pending['position']=value
                else:self.seek_backend(value)
            elif op=='speed':
                value=float(data['value'])
                if value not in (.5,.75,1,1.25,1.5,1.75,2):raise ValueError('Invalid speed.')
                if self.active and not self.pending and self.backend.state()['status'] in ('playing','paused'):self.backend.speed(value)
                self.saved['speed']=value;self.saved['miniSpeedCycleIndex']=None
                ident=self.saved['currentId']
                if ident:self.saved['tracks'].setdefault(ident,{})['speed']=value
            elif op=='audio_enhancement':
                settings=data.get('value',{})
                if not isinstance(settings,dict):raise ValueError('Audio settings must be an object.')
                clean={name:float(settings.get(name,0)) for name in ('bass','body','clarity','treble')}
                if any(not math.isfinite(v) or not -6<=v<=6 for v in clean.values()):raise ValueError('Audio controls must be between -6 and +6 dB.')
                if hasattr(self.backend,'audio_settings'):self.backend.audio_settings(clean)
                self.saved['audioEnhancement']=clean
            elif op=='speech_enhancement_enabled':
                enabled=data.get('value')
                if type(enabled) is not bool:raise ValueError('Choose whether enhanced audio should be used.')
                ident=self.saved.get('currentId')
                current=self.snapshot() if ident else None
                self.saved['speechEnhancementEnabled']=enabled
                if ident in self.paths:
                    position=current.get('position',0) if current else 0
                    autoplay=bool((self.pending and self.pending['autoplay']) or (current and current['status']=='playing'))
                    self.load(ident,position=position,autoplay=autoplay)
            elif op=='volume':
                value=float(data['value'])
                if not 0<=value<=1:raise ValueError('Invalid volume.')
                if not self.pending:self.backend.volume(value)
                self.saved['volume']=value
            elif op=='autonext':self.saved['autoNext']=data.get('value') is True
            elif op=='next':self.advance(1)
            elif op=='previous':self.advance(-1)
            elif op=='stop':self.sleep_deadline=None;self.sleep_minutes=0;self.sleep_at_end=False;self.clear_loop();self.capture();self.backend.stop();self.pending=None;self.active=None;self.seek_target=None
            else:raise ValueError('Unknown command.')
            result=self.snapshot();self.persist();return result
    def tick(self):
        with self.lock:
            if self.sleep_deadline and time.monotonic()>=self.sleep_deadline:
                self.sleep_deadline=None;self.sleep_minutes=0;self.sleep_paused=True;self.command({'op':'pause'})
            raw=self.capture()
            if self.pending:
                if raw['status']=='error' or time.monotonic()-self.pending['started']>20:
                    self.fail_load('VLC could not load this recording. Press Play to try again.')
                elif raw['status'] in ('playing','paused') and raw['duration']>0:
                    pending=self.pending
                    try:
                        self.seek_backend(min(pending['position'],raw['duration']))
                        self.backend.speed(self.saved['speed'])
                        if not pending['autoplay']:self.backend.pause()
                        self.backend.volume(self.saved['volume']);self.pending=None
                    except Exception as error:self.fail_load('Could not restore playback: '+str(error))
            elif raw['status']=='ended' and self.sleep_at_end:
                self.sleep_at_end=False;self.sleep_paused=True
            elif self.loop_b is not None and not self.sleep_paused and raw['status'] in ('playing','ended') and raw['position']>=self.loop_b:
                if raw['status']=='ended':self.load(self.saved['currentId'],position=self.loop_a,autoplay=True)
                elif time.monotonic()-self.loop_seek_at>=.3:
                    self.seek_backend(self.loop_a);self.loop_seek_at=time.monotonic();self.capture()
            elif raw['status']=='ended' and self.was_playing and self.saved['autoNext'] and not self.sleep_paused:self.advance(1)
            self.was_playing=raw['status']=='playing'
            if raw['status']=='error':self.error='VLC playback failed. Check the recording and your audio output.'
            if time.monotonic()-self.last_save>=1 or raw['status']!=self.previous_status:self.persist();self.last_save=time.monotonic()
            self.previous_status=raw['status']
