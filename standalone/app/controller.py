"""Local library actions shared by the native desktop controls and tests."""
import re,secrets

def natural_key(value):
 """Keep numbered shiurim in listening order, including nested source folders."""
 return tuple(int(part) if part.isdecimal() else part for part in re.split(r'(\d+)',value.casefold()))

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
 def assign_many(self,ids,name):
  name=name.strip();ids=list(dict.fromkeys(ids))
  if not name or len(name)>160:raise ValueError('Enter a collection name of 1–160 characters.')
  if not ids or any(ident not in self.player.paths for ident in ids):raise ValueError('Select available recordings first.')
  with self.player.lock:
   folder=next((f for f in self.player.saved['folders'] if f['name'].casefold()==name.casefold()),None)
   if folder is None:
    folder={'id':secrets.token_hex(12),'name':name,'trackIds':[]};self.player.saved['folders'].append(folder)
   folder['trackIds']=list(dict.fromkeys(folder['trackIds']+ids));self.player.persist();self.revision+=1
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
  if op=='folder_create':
   result=self.player.command({'op':op,'name':name});self.view=result['folders'][-1]['id']
  else:result=self.player.command({'op':op,'id':self.view,'name':name})
  if op=='folder_delete':self.view='all'
  self.revision+=1;return result
 def add_to(self,folder):
  if not self.selected:raise ValueError('Select a recording first.')
  self.player.command({'op':'folder_add','id':folder,'trackId':self.selected});self.revision+=1
 def reset(self):
  with self.player.lock:
   ident=self.selected
   if not ident or ident not in self.player.paths:raise ValueError('Select a recording first.')
   if self.player.active==ident:
    self.player.backend.pause()
    if self.player.pending:self.player.pending['position']=0;self.player.pending['autoplay']=False
    else:self.player.backend.seek(0)
   previous=self.player.saved['tracks'].get(ident,{})
   self.player.saved['tracks'][ident]={**previous,'position':0,'completed':False};self.player.persist();self.revision+=1
 def bookmarks(self):return sorted(self.player.saved['bookmarks'].get(self.player.saved['currentId'],[]),key=lambda mark:mark['position'])
 def mark(self,name):
  with self.player.lock:
   state=self.player.snapshot();ident=state['currentId']
   if not ident:raise ValueError('Select a recording first.')
   self.player.saved['bookmarks'].setdefault(ident,[]).append({'id':secrets.token_hex(12),'position':state['position'],'name':name.strip()[:160] or clock(state['position'])})
   self.player.persist();self.revision+=1
 def bookmark_action(self,ident,delete=False):
  with self.player.lock:
   current=self.player.saved['currentId'];marks=self.bookmarks();mark=next((m for m in marks if m['id']==ident),None)
   if not mark:raise ValueError('Select a bookmark first.')
   if delete:self.player.saved['bookmarks'][current]=[m for m in marks if m['id']!=ident];self.player.persist();self.revision+=1
   elif not self.player.active:self.player.load(current,position=mark['position'],autoplay=False)
   else:self.player.command({'op':'seek','value':mark['position']})

 def rename(self,ident,name):
  import hashlib,re
  with self.player.lock:
   if ident not in self.player.paths:raise ValueError('Select an available recording.')
   source=self.player.paths[ident];name=str(name).strip()
   if name.lower().endswith(source.suffix.lower()):name=name[:-len(source.suffix)]
   if not name or len(name)>180 or re.search(r'[<>:"/\\|?*\x00-\x1f]',name) or name.endswith(('.', ' ')) or name.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}:raise ValueError('Choose a valid filename without slashes or special characters.')
   target=source.with_name(name+source.suffix)
   if target==source:return ident
   if target.exists():raise ValueError('A recording with that filename already exists.')
   if not source.resolve().is_relative_to(self.player.root):raise ValueError('The recording is outside the audio folder.')
   state=self.player.snapshot();active=self.player.active==ident;position=self.player.saved['tracks'].get(ident,{}).get('position',0)
   if active:
    self.player.backend.stop();self.player.active=None;self.player.pending=None;self.player.seek_target=None
   try:source.rename(target)
   except OSError:
    if active:self.player.load(ident,position=position,autoplay=False)
    raise
   relative=target.relative_to(self.player.root).as_posix();new_id=hashlib.sha256((str(self.player.root)+'/'+relative).encode()).hexdigest()[:24]
   self.player.paths.pop(ident);self.player.paths[new_id]=target
   for track in self.player.tracks:
    if track['id']==ident:track.update(id=new_id,name=target.name,source=relative)
   if ident in self.player.saved['tracks']:self.player.saved['tracks'][new_id]=self.player.saved['tracks'].pop(ident)
   marks=self.player.saved['bookmarks']
   if ident in marks:marks[new_id]=marks.pop(ident)
   self.player.saved['queue']=[new_id if i==ident else i for i in self.player.saved['queue']]
   for folder in self.player.saved['folders']:folder['trackIds']=[new_id if i==ident else i for i in folder['trackIds']]
   if self.player.saved['currentId']==ident:self.player.saved['currentId']=new_id
   if self.selected==ident:self.selected=new_id
   if self.player.loop_track==ident:self.player.loop_track=new_id
   self.player.library_revision+=1;self.revision+=1;self.player.persist()
   if active:self.player.load(new_id,position=position,autoplay=state['status']=='playing' or state.get('playRequested',False))
   return new_id
