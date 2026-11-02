"""Local library actions shared by the native desktop controls and tests."""
import hashlib,re,secrets

def natural_key(value):
 """Keep numbered shiurim in listening order, including nested source folders."""
 return tuple((0,int(part)) if part.isdecimal() else (1,part) for part in re.split(r'(\d+)',value.casefold()))

def clock(seconds):
 seconds=max(0,int(seconds));h,m,s=seconds//3600,seconds%3600//60,seconds%60
 return f'{h}:{m:02}:{s:02}' if h else f'{m}:{s:02}'

class LibraryController:
 def __init__(self,player):
  self.player=player;self.view='all';self.query='';self.selected=player.saved['currentId'];self.revision=0
  self.sort=player.saved.get('librarySort','name');self.descending=bool(player.saved.get('librarySortDescending',False));self.explicit_sort=False
  self.player.saved.setdefault('bookmarks',{})
 def tracks(self):
  with self.player.lock:
   values=self.player.library();folder=next((f for f in self.player.saved['folders'] if f['id']==self.view),None)
   if folder:values=[t for t in values if t['id'] in folder['trackIds']]
   elif self.view=='continue':values=sorted([t for t in values if t.get('position',0)>0 and not t.get('completed',False)],key=lambda t:t.get('lastListenedAt',0),reverse=True)
   elif self.view=='favorites':values=[t for t in values if t.get('favorite',False)]
   elif self.view=='unplayed':values=[t for t in values if not t.get('position',0) and not t.get('completed',False)]
   elif self.view=='finished':values=[t for t in values if t.get('completed',False)]
   terms=self.query.casefold().split();values=[t for t in values if all(term in (t['name']+' '+t['source']).casefold() for term in terms)]
   if self.view!='continue' or self.explicit_sort:
    key={'name':lambda t:(natural_key(t['name']),natural_key(t['source'])),'resume':lambda t:(t.get('position',0),natural_key(t['name'])),'duration':lambda t:(t.get('duration',0),natural_key(t['name']))}.get(self.sort)
    if key:values.sort(key=key,reverse=self.descending)
   return values
 def set_sort(self,column):
  if column not in ('name','resume','duration'):raise ValueError('Unknown sort column.')
  with self.player.lock:
   self.descending=not self.descending if column==self.sort and self.explicit_sort else False
   self.sort=column;self.explicit_sort=True
   self.player.saved.update(librarySort=column,librarySortDescending=self.descending);self.player.persist()
 def _available_ids(self,ids):
  ids=list(dict.fromkeys(ids))
  if not ids or any(ident not in self.player.paths for ident in ids):raise ValueError('Select available recordings first.')
  return ids
 def favorite(self,ids,value=None):
  if value is not None and not isinstance(value,bool):raise ValueError('Choose whether to add or remove favorites.')
  with self.player.lock:
   ids=self._available_ids(ids)
   for ident in ids:
    progress=self.player.saved['tracks'].setdefault(ident,{})
    progress['favorite']=not progress.get('favorite',False) if value is None else value
   self.player.persist();self.revision+=1
 def _queue(self):
  values=list(dict.fromkeys(ident for ident in self.player.saved['queue'] if ident in self.player.paths))
  current=self.player.saved['currentId']
  if current in self.player.paths and current not in values:values.insert(0,current)
  return values
 def queue_add(self,ids,next_up=False):
  with self.player.lock:
   ids=self._available_ids(ids);values=self._queue();current=self.player.saved['currentId']
   if next_up:
    ids=[ident for ident in ids if ident!=current]
    values=[ident for ident in values if ident not in ids]
    index=values.index(current)+1 if current in values else 0
    values[index:index]=ids
   else:values.extend(ident for ident in ids if ident not in values)
   self.player.saved['queue']=values;self.player.persist();self.revision+=1
   return list(values)
 def queue_remove(self,ids):
  with self.player.lock:
   ids=set(self._available_ids(ids));current=self.player.saved['currentId']
   if ids=={current}:raise ValueError('The current recording stays in the queue. Select another recording to remove.')
   self.player.saved['queue']=[ident for ident in self._queue() if ident==current or ident not in ids]
   self.player.persist();self.revision+=1
   return list(self.player.saved['queue'])
 def queue_move(self,ident,delta):
  if not isinstance(delta,int) or isinstance(delta,bool) or delta not in (-1,1):raise ValueError('Move a recording up or down one place.')
  with self.player.lock:
   values=self._queue()
   if ident not in values:raise ValueError('Select a recording in the queue first.')
   index=values.index(ident);target=max(0,min(len(values)-1,index+delta))
   values.insert(target,values.pop(index));self.player.saved['queue']=values
   self.player.persist();self.revision+=1
   return list(values)
 def _validate_collection_name(self,name):
  name=str(name).strip()
  if (not name or len(name)>160 or any(ch in '<>:"/|?*' or ch==chr(92) or ord(ch)<32 for ch in name)
      or name.endswith(('.', ' ')) or name.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}):
   raise ValueError('Choose a collection name that is a valid folder name.')
  return name
 def _collection_directory(self,folder,create=False):
  root=self.player.root
  if root is None:raise ValueError('Choose a recordings folder before creating a collection.')
  relative=folder.get('directory') or folder['name']
  directory=(root/relative)
  if directory.resolve()==root.resolve() or not directory.resolve().is_relative_to(root.resolve()):
   raise ValueError('The collection folder must stay inside the recordings folder.')
  if directory.is_symlink():raise ValueError('A collection cannot use a symbolic-link folder.')
  if directory.exists() and not directory.is_dir():raise ValueError('A file already uses the collection folder name.')
  if create:directory.mkdir(parents=True,exist_ok=True)
  folder['directory']=directory.relative_to(root).as_posix()
  return directory
 def _move_track_to_collection(self,ident,folder):
  import pathlib
  source=self.player.paths.get(ident)
  if source is None:raise ValueError('Recording not found.')
  root=self.player.root.resolve()
  if not source.resolve().is_relative_to(root):raise ValueError('The recording is outside the selected recordings folder.')
  directory=self._collection_directory(folder,create=True)
  target=directory/source.name
  if source.resolve()!=target.resolve() and target.exists():
   stem,suffix=source.stem,source.suffix;number=2
   while target.exists():
    target=directory/f'{stem} ({number}){suffix}';number+=1
  if source.resolve()!=target.resolve():
   was_active=self.player.active==ident
   if was_active:
    self.player.capture()
    raw=self.player.backend.state()
    autoplay=self.player.pending['autoplay'] if self.player.pending else raw['status']=='playing'
    position=self.player.saved['tracks'].get(ident,{}).get('position',0)
    self.player.backend.stop();self.player.active=None;self.player.pending=None;self.player.seek_target=None
   try:
    target.parent.mkdir(parents=True,exist_ok=True)
    source.rename(target)
   except OSError:
    if was_active:
     try:self.player.load(ident,position=position,autoplay=autoplay)
     except Exception:pass
    raise
   relative=target.relative_to(root).as_posix()
   new_id=hashlib.sha256((str(root)+'/'+relative).encode()).hexdigest()[:24]
   if new_id!=ident:
    if new_id in self.player.paths:raise ValueError('The destination recording is already in the library.')
    self.player.paths.pop(ident);self.player.paths[new_id]=target
    for track in self.player.tracks:
     if track['id']==ident:track.update(id=new_id,name=target.name,source=relative)
    if ident in self.player.saved['tracks']:self.player.saved['tracks'][new_id]=self.player.saved['tracks'].pop(ident)
    if ident in self.player.saved['bookmarks']:self.player.saved['bookmarks'][new_id]=self.player.saved['bookmarks'].pop(ident)
    self.player.saved['queue']=[new_id if value==ident else value for value in self.player.saved['queue']]
    if self.player.saved['currentId']==ident:self.player.saved['currentId']=new_id
    for item in self.player.saved['folders']:
     item['trackIds']=[new_id if value==ident else value for value in item['trackIds']]
    if self.selected==ident:self.selected=new_id
    if self.player.loop_track==ident:self.player.loop_track=new_id
    ident=new_id
   self.player.library_revision+=1
   if was_active:self.player.load(ident,position=position,autoplay=autoplay)
  for item in self.player.saved['folders']:
   if item is not folder:item['trackIds']=[value for value in item['trackIds'] if value!=ident]
  if ident not in folder['trackIds']:folder['trackIds'].append(ident)
  self.player.persist()
  return ident
 def assign_many(self,ids,name):
  name=self._validate_collection_name(name);ids=list(dict.fromkeys(ids))
  if not ids or any(ident not in self.player.paths for ident in ids):raise ValueError('Select available recordings first.')
  with self.player.lock:
   folder=next((f for f in self.player.saved['folders'] if f['name'].casefold()==name.casefold()),None)
   if folder is None:
    self.collection('folder_create',name)
    folder=next(f for f in self.player.saved['folders'] if f['name'].casefold()==name.casefold())
   for ident in ids:self._move_track_to_collection(ident,folder)
   self.revision+=1
   return folder['id']
 def play(self,force=False):
  with self.player.lock:
   if not force and self.player.active and ((self.player.pending and self.player.pending['autoplay']) or (not self.player.pending and self.player.backend.state()['status']=='playing')):
    return self.player.command({'op':'pause'})
   ids=[t['id'] for t in self.tracks()]
   selected=self.selected if self.selected in ids else (self.player.saved['currentId'] if self.player.saved['currentId'] in ids else (ids[0] if ids else None))
   if selected is None:
    if self.player.saved['currentId'] in self.player.paths:return self.player.command({'op':'play' if force else 'toggle'})
    raise ValueError('Choose a recordings folder first.')
   self.selected=selected
   if selected!=self.player.saved['currentId']:
    self.player.command({'op':'load','id':selected,'queue':ids});return self.player.command({'op':'play'})
   self.player.saved['queue']=ids
   return self.player.command({'op':'play' if force else 'toggle'})
 def collection(self,op,name=''):
  with self.player.lock:
   if op=='folder_create':
    name=self._validate_collection_name(name)
    if self.player.root is None:raise ValueError('Choose a recordings folder before creating a collection.')
    result=self.player.command({'op':op,'name':name});folder=next(f for f in self.player.saved['folders'] if f['id']==result['folders'][-1]['id'])
    try:self._collection_directory(folder,create=True);self.player.persist()
    except Exception:
     self.player.command({'op':'folder_delete','id':folder['id']});raise
    self.view=folder['id']
   elif op=='folder_rename':
    folder=next((f for f in self.player.saved['folders'] if f['id']==self.view),None)
    if folder is None:raise ValueError('Folder not found.')
    name=self._validate_collection_name(name);old_directory=self._collection_directory(folder,create=True);new_directory=self.player.root/name
    if old_directory.resolve()!=new_directory.resolve():
     if new_directory.exists():raise ValueError('A folder with that name already exists in the recordings folder.')
     old_directory.rename(new_directory)
    result=self.player.command({'op':op,'id':self.view,'name':name})
    folder['directory']=new_directory.relative_to(self.player.root).as_posix();self.player.persist()
   else:result=self.player.command({'op':op,'id':self.view,'name':name})
  if op=='folder_delete':self.view='all'
  self.revision+=1;return result
 def add_to(self,folder):
  if not self.selected:raise ValueError('Select a recording first.')
  with self.player.lock:
   target=next((f for f in self.player.saved['folders'] if f['id']==folder),None)
   if target is None:raise ValueError('Collection not found.')
   self._move_track_to_collection(self.selected,target)
   self.revision+=1
 def reset(self):
  with self.player.lock:
   ident=self.selected
   if not ident or ident not in self.player.paths:raise ValueError('Select a recording first.')
   if self.player.active==ident:
    self.player.clear_loop()
    if self.player.backend.state()['status'] in ('ended','stopped','error'):
     self.player.load(ident,position=0,autoplay=False)
    elif self.player.pending:
     self.player.pending['position']=0;self.player.pending['autoplay']=False;self.player.seek_target=None
    else:
     self.player.backend.pause();self.player.seek_backend(0)
   previous=self.player.saved['tracks'].get(ident,{})
   self.player.saved['tracks'][ident]={**previous,'position':0,'completed':False};self.player.persist();self.revision+=1
 def bookmarks(self):return sorted(self.player.saved['bookmarks'].get(self.player.saved['currentId'],[]),key=lambda mark:mark['position'])
 def mark(self,name):
  with self.player.lock:
   state=self.player.snapshot();ident=state['currentId']
   if not ident:raise ValueError('Select a recording first.')
   self.player.saved['bookmarks'].setdefault(ident,[]).append({'id':secrets.token_hex(12),'position':state['position'],'name':name.strip()[:160] or clock(state['position'])})
   self.player.persist();self.revision+=1
 def bookmark_action(self,ident,delete=False,track_id=None):
  with self.player.lock:
   current=track_id or self.player.saved['currentId'];marks=self.player.saved['bookmarks'].get(current,[]);mark=next((m for m in marks if m['id']==ident),None)
   if not mark:raise ValueError('Select a bookmark first.')
   if delete:self.player.saved['bookmarks'][current]=[m for m in marks if m['id']!=ident];self.player.persist();self.revision+=1
   elif self.player.active!=current:self.player.load(current,position=mark['position'],autoplay=False)
   else:self.player.command({'op':'seek','value':mark['position']})

 def rename(self,ident,name):
  import hashlib,json,os,re
  with self.player.lock:
   if ident not in self.player.paths:raise ValueError('Select an available recording.')
   source=self.player.paths[ident];name=str(name).strip()
   if name.lower().endswith(source.suffix.lower()):name=name[:-len(source.suffix)]
   if not name or len(name)>180 or re.search(r'[<>:"/\\|?*\x00-\x1f]',name) or name.endswith(('.', ' ')) or name.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}:raise ValueError('Choose a valid filename without slashes or special characters.')
   target=source.with_name(name+source.suffix)
   if target==source:return ident
   if target.exists() or target.is_symlink():raise ValueError('A recording with that filename already exists.')
   root=self.player.root.resolve()
   if not source.resolve().is_relative_to(root):raise ValueError('The recording is outside the audio folder.')
   relative_source=source.relative_to(root).as_posix()
   relative_target=target.relative_to(root).as_posix()
   new_id=hashlib.sha256((str(root)+'/'+relative_target).encode()).hexdigest()[:24]
   if new_id in self.player.paths:raise ValueError('The destination recording is already in the library.')
   journal=self.player.data_dir/'rename-recovery.json'
   if journal.exists():raise ValueError('A previous recording rename still needs recovery. Restart the player before renaming another recording.')
   temporary=journal.with_suffix('.tmp')
   record={'root':str(root),'source':relative_source,'target':relative_target,'old_id':ident,'new_id':new_id}
   state=self.player.snapshot();active=self.player.active==ident
   position=self.player.saved['tracks'].get(ident,{}).get('position',0)
   was_playing=state['status']=='playing' or state.get('playRequested',False)
   # Write and fsync the recovery intent before touching the audio file.
   with temporary.open('w',encoding='utf-8') as stream:
    json.dump(record,stream,ensure_ascii=False);stream.flush();os.fsync(stream.fileno())
   os.replace(temporary,journal)
   try:
    if active:
     self.player.backend.stop();self.player.active=None;self.player.pending=None;self.player.seek_target=None
    source.rename(target)
   except OSError:
    try:journal.unlink(missing_ok=True)
    except OSError:pass
    if active:
     try:self.player.load(ident,position=position,autoplay=was_playing)
     except Exception:pass
    raise
   self.player.paths.pop(ident);self.player.paths[new_id]=target
   for track in self.player.tracks:
    if track['id']==ident:track.update(id=new_id,name=target.name,source=relative_target)
   if ident in self.player.saved['tracks']:
    self.player.saved['tracks'][new_id]={**self.player.saved['tracks'].get(new_id,{}),**self.player.saved['tracks'].pop(ident)}
   marks=self.player.saved['bookmarks']
   if ident in marks:
    previous=marks.pop(ident);current=marks.setdefault(new_id,[])
    known={item['id'] for item in current};current.extend(item for item in previous if item['id'] not in known)
   self.player.saved['queue']=list(dict.fromkeys(new_id if i==ident else i for i in self.player.saved['queue']))
   for folder in self.player.saved['folders']:folder['trackIds']=list(dict.fromkeys(new_id if value==ident else value for value in folder['trackIds']))
   if self.player.saved['currentId']==ident:self.player.saved['currentId']=new_id
   if self.selected==ident:self.selected=new_id
   if self.player.loop_track==ident:self.player.loop_track=new_id
   self.player.library_revision+=1;self.revision+=1
   # If this fails, leave the journal in place so startup can finish the migration.
   self.player.persist()
   journal.unlink()
   if active:self.player.load(new_id,position=position,autoplay=was_playing)
   return new_id

