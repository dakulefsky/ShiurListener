"""Local library actions shared by the native desktop controls and tests."""
import secrets

def clock(seconds):
 seconds=max(0,int(seconds));h,m,s=seconds//3600,seconds%3600//60,seconds%60
 return f'{h}:{m:02}:{s:02}' if h else f'{m}:{s:02}'

class LibraryController:
 def __init__(self,player):
  self.player=player;self.view='all';self.query='';self.selected=player.saved['currentId'];self.revision=0
  self.player.saved.setdefault('bookmarks',{})
 def tracks(self):
  with self.player.lock:
   values=self.player.library();folder=next((f for f in self.player.saved['folders'] if f['id']==self.view),None)
   if folder:values=[t for t in values if t['id'] in folder['trackIds']]
   elif self.view=='continue':values=[t for t in values if t.get('position',0)>0 and (not t.get('duration') or t['position']<t['duration']-.2)]
   q=self.query.casefold();return [t for t in values if q in (t['name']+' '+t['source']).casefold()]
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
   self.player.saved['tracks'][ident]={**previous,'position':0};self.player.persist();self.revision+=1
 def bookmarks(self):return self.player.saved['bookmarks'].get(self.player.saved['currentId'],[])
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
