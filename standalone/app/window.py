"""Local desktop library. UI work stays on the Tk thread; audio runs independently."""
import queue,sys
import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox
from controller import clock

TITLE='Shiur Player — Your listening library'
FONT='Segoe UI' if sys.platform=='win32' else 'Helvetica'
BG='#F5F3ED'; PAPER='#FFFFFF'; INK='#20352F'; MUTED='#748078'; GREEN='#245C49'; LINE='#E3E7DF'

class PlayerWindow:
 def __init__(self,player,library,shortcuts):
  self.player=player;self.library=library;self.shortcuts=shortcuts;self.requests=queue.SimpleQueue();self.closed=False;self.dragging=False;self.rows={};self.nav_signature=None
  self.root=tk.Tk();self.root.title(TITLE);self.root.geometry('1260x850');self.root.minsize(1080,700);self.root.configure(bg=BG)
  self.root.option_add('*Font',(FONT,10));self.root.option_add('*Foreground',INK)
  style=ttk.Style(self.root);style.theme_use('clam')
  style.configure('Treeview',background=PAPER,fieldbackground=PAPER,foreground=INK,rowheight=57,borderwidth=0,font=(FONT,10))
  style.configure('Treeview.Heading',background=BG,foreground=MUTED,font=(FONT,9),padding=(12,12),relief='flat')
  style.map('Treeview',background=[('selected','#E2EFE7')],foreground=[('selected',INK)])
  style.configure('TScale',background=PAPER,troughcolor=LINE)
  self.player.show_window=lambda:self.requests.put('show');self.player.hide_window=lambda:self.requests.put('hide');self.player.choose_folder=lambda:self.requests.put('folder')
  self.build();self.root.protocol('WM_DELETE_WINDOW',self.close)
  for key,fn in [('<space>',self.toggle),('<Left>',lambda:self.skip(-1)),('<Right>',lambda:self.skip(1)),('<Control-b>',self.bookmark),('<Control-f>',lambda:self.search.focus_set())]:
   self.root.bind(key,lambda event,f=fn:self.key(event,f))
  self.root.bind('<Control-o>',lambda _:self.choose_folder());self.root.bind('<Escape>',lambda _:self.root.focus_set())
  self.refresh()
 def label(self,parent,text,size=10,color=INK,bg=None,**kw):
  return tk.Label(parent,text=text,font=(FONT,size),fg=color,bg=bg or parent.cget('bg'),**kw)
 def button(self,parent,text,fn,primary=False,**kw):
  return tk.Button(parent,text=text,command=lambda:self.safe(fn),bg=GREEN if primary else parent.cget('bg'),fg='white' if primary else INK,activebackground='#DDE9E0',activeforeground=INK,relief='flat',bd=0,padx=14,pady=8,cursor='hand2',**kw)
 def build(self):
  self.sidebar=tk.Frame(self.root,bg='#EAEDE5',width=220);self.sidebar.pack(side='left',fill='y');self.sidebar.pack_propagate(False)
  self.label(self.sidebar,'SHIUR / PLAYER',15,bg='#EAEDE5',anchor='w').pack(fill='x',padx=24,pady=(32,5))
  self.label(self.sidebar,'A little more listening.',10,MUTED).pack(anchor='w',padx=24,pady=(0,35))
  self.nav=tk.Frame(self.sidebar,bg='#EAEDE5');self.nav.pack(fill='x',padx=12)
  self.button(self.sidebar,'+  New collection',self.new_collection).pack(fill='x',padx=12,pady=14)
  bottom=tk.Frame(self.sidebar,bg='#EAEDE5');bottom.pack(side='bottom',fill='x',padx=12,pady=20)
  self.folder_label=self.label(bottom,'No folder selected',9,MUTED,wraplength=180,anchor='w');self.folder_label.pack(fill='x',padx=12,pady=10)
  self.button(bottom,'Choose audio folder',self.choose_folder).pack(fill='x')
  self.button(bottom,'Rescan folder',lambda:self.command('rescan')).pack(fill='x')
  self.button(bottom,'Settings & shortcuts',self.settings).pack(fill='x')
  content=tk.Frame(self.root,bg=BG);content.pack(side='left',fill='both',expand=True,padx=28,pady=28)
  self.label(content,'MAKE TIME TO LISTEN',9,MUTED,anchor='w').pack(fill='x')
  self.heading=self.label(content,'Your listening library',25,anchor='w');self.heading.pack(fill='x',pady=(6,4))
  self.subtitle=self.label(content,'A separate place saved for every shiur.',10,MUTED,anchor='w');self.subtitle.pack(fill='x',pady=(0,22))
  body=tk.Frame(content,bg=BG);body.pack(fill='both',expand=True)
  left=tk.Frame(body,bg=BG);left.pack(side='left',fill='both',expand=True,padx=(0,20))
  self.query=tk.StringVar();self.search=tk.Entry(left,textvariable=self.query,relief='flat',bg=PAPER,fg=INK,insertbackground=INK,font=(FONT,11));self.search.pack(fill='x',ipady=12)
  self.query.trace_add('write',lambda *_:self.search_changed())
  self.label(left,'Search recordings above · double-click to resume',9,MUTED,anchor='w').pack(fill='x',pady=(8,16))
  table=tk.Frame(left,bg=PAPER);table.pack(fill='both',expand=True)
  self.tree=ttk.Treeview(table,columns=('name','resume','duration'),show='headings',selectmode='browse',height=5)
  for name,title,width in [('name','RECORDING',260),('resume','RESUME AT',110),('duration','LENGTH',80)]:self.tree.heading(name,text=title);self.tree.column(name,width=width,minwidth=75,stretch=name=='name')
  scroll=ttk.Scrollbar(table,orient='vertical',command=self.tree.yview);self.tree.configure(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y');self.tree.pack(fill='both',expand=True)
  self.tree.bind('<<TreeviewSelect>>',self.select);self.tree.bind('<Double-1>',lambda _:self.safe(self.resume));self.tree.bind('<Return>',lambda _:self.safe(self.resume))
  actions=tk.Frame(left,bg=BG);actions.pack(fill='x',pady=(12,0))
  self.button(actions,'Resume selected',self.resume,True).pack(side='left')
  self.button(actions,'Add to collection',self.add_collection).pack(side='left',padx=8)
  self.button(actions,'More',self.more).pack(side='right')
  right=tk.Frame(body,bg=PAPER,width=310);right.pack(side='right',fill='y');right.pack_propagate(False)
  card_scroll=ttk.Scrollbar(right,orient='vertical');card_scroll.pack(side='right',fill='y')
  card_canvas=tk.Canvas(right,bg=PAPER,highlightthickness=0,yscrollcommand=card_scroll.set);card_canvas.pack(fill='both',expand=True);card_scroll.configure(command=card_canvas.yview)
  self.card=tk.Frame(card_canvas,bg=PAPER,padx=18,pady=20)
  card_window=card_canvas.create_window(0,0,anchor='nw',window=self.card)
  self.card.bind('<Configure>',lambda _:card_canvas.configure(scrollregion=card_canvas.bbox('all')))
  card_canvas.bind('<Configure>',lambda event:card_canvas.itemconfigure(card_window,width=event.width))
  self.label(self.card,'NOW PLAYING',9,MUTED,anchor='w').pack(fill='x')
  art=tk.Canvas(self.card,height=90,bg='#E7EEE7',highlightthickness=0);art.pack(fill='x',pady=(14,16))
  for x,h in enumerate([14,28,48,68,42,82,58,36,65,90,50,30,56,38,20]):
   xx=22+x*15;art.create_line(xx,45-h*.4,xx,45+h*.4,fill=GREEN,width=5,capstyle='round')
  self.track_title=self.label(self.card,'Ready when you are',17,anchor='nw',justify='left',wraplength=260);self.track_title.pack(fill='x')
  self.source=self.label(self.card,'Choose a recording to begin.',9,MUTED,anchor='w',wraplength=260,justify='left');self.source.pack(fill='x',pady=(8,14))
  self.state_label=self.label(self.card,'Your place is remembered automatically',9,GREEN,anchor='w',wraplength=260);self.state_label.pack(fill='x',pady=(0,12))
  self.seek=ttk.Scale(self.card,from_=0,to=1);self.seek.pack(fill='x');self.seek.bind('<ButtonPress-1>',lambda _:setattr(self,'dragging',True));self.seek.bind('<ButtonRelease-1>',self.seek_release)
  self.time=self.label(self.card,'0:00 / 0:00',10,MUTED,anchor='w');self.time.pack(fill='x',pady=(4,12))
  controls=tk.Frame(self.card,bg=PAPER);controls.pack(fill='x')
  self.back=self.button(controls,'−15s',lambda:self.skip(-1));self.back.pack(side='left')
  self.play_button=self.button(controls,'Play',self.toggle,True);self.play_button.pack(side='left',expand=True,fill='x',padx=6)
  self.forward=self.button(controls,'+15s',lambda:self.skip(1));self.forward.pack(side='right')
  opts=tk.Frame(self.card,bg=PAPER);opts.pack(fill='x',pady=16)
  self.label(opts,'Speed',9,MUTED).pack(side='left');self.speed=ttk.Combobox(opts,values=['0.75','1','1.25','1.5','1.75','2'],state='readonly',width=5);self.speed.set(str(self.player.saved['speed']));self.speed.pack(side='left',padx=8);self.speed.bind('<<ComboboxSelected>>',lambda _:self.safe(lambda:self.command('speed',value=float(self.speed.get()))))
  self.label(opts,'Skip',9,MUTED).pack(side='left');self.interval=ttk.Combobox(opts,values=['10','15','60'],state='readonly',width=4);self.interval.set(str(self.player.saved['skipSeconds']));self.interval.pack(side='left',padx=8);self.interval.bind('<<ComboboxSelected>>',lambda _:self.safe(lambda:self.command('skip_interval',value=int(self.interval.get()))))
  self.label(self.card,'VOLUME',9,MUTED,anchor='w').pack(fill='x')
  volume=ttk.Scale(self.card,from_=0,to=1,value=self.player.saved['volume'],command=lambda value:self.safe(lambda:self.command('volume',value=float(value))));volume.pack(fill='x',pady=(6,12))
  self.button(self.card,'Open floating controls',lambda:self.command('floating_toggle')).pack(fill='x')
  self.button(self.card,'+ Bookmark this moment',self.bookmark).pack(fill='x')
  self.button(self.card,'View bookmarks',self.bookmarks).pack(fill='x')
  self.status=self.label(content,'',9,MUTED,anchor='w',wraplength=850);self.status.pack(fill='x',pady=(18,0))
 def safe(self,fn):
  try:return fn()
  except Exception as error:messagebox.showerror('Shiur Player',str(error),parent=self.root)
 def command(self,op,**kw):return self.player.command({'op':op,**kw})
 def key(self,event,fn):
  if isinstance(event.widget,(tk.Entry,ttk.Entry,ttk.Combobox,tk.Text,tk.Scale,ttk.Scale)):return
  self.safe(fn);return 'break'
 def search_changed(self):self.library.query=self.query.get();self.update_rows()
 def select(self,_=None):
  ids=self.tree.selection()
  if ids:self.library.selected=ids[0]
 def resume(self):self.library.play(force=True)
 def toggle(self):
  if self.player.saved['currentId']:self.command('toggle')
  else:self.library.play()
 def skip(self,direction):self.command('skip',direction=direction)
 def seek_release(self,_):
  value=float(self.seek.get());self.dragging=False
  def apply():
   if not self.player.active and self.player.saved['currentId']:self.player.load(self.player.saved['currentId'],position=value,autoplay=False)
   else:self.command('seek',value=value)
  self.safe(apply)
 def navigate(self,view):self.library.view=view;self.nav_signature=None;self.update_rows()
 def choose_folder(self):
  path=filedialog.askdirectory(title='Choose your shiur audio folder',parent=self.root)
  if path:self.player.scan(path);self.library.selected=None;self.update_rows()
 def new_collection(self):
  name=simpledialog.askstring('New collection','Collection name:',parent=self.root)
  if name:self.library.collection('folder_create',name);self.nav_signature=None;self.update_rows()
 def add_collection(self):
  menu=tk.Menu(self.root,tearoff=False)
  for folder in self.player.saved['folders']:menu.add_command(label=folder['name'],command=lambda f=folder:self.safe(lambda:self.library.add_to(f['id'])))
  menu.add_command(label='New collection…',command=lambda:self.safe(self.new_collection));menu.tk_popup(self.root.winfo_pointerx(),self.root.winfo_pointery())
 def more(self):
  menu=tk.Menu(self.root,tearoff=False);menu.add_command(label='Reset selected recording to the beginning',command=lambda:self.safe(self.reset_selected))
  if self.library.view not in ('all','continue'):
   menu.add_command(label='Remove selected from this collection',command=lambda:self.safe(lambda:self.command('folder_remove',id=self.library.view,trackId=self.library.selected)))
   menu.add_command(label='Rename collection',command=lambda:self.safe(self.rename_collection));menu.add_command(label='Delete collection',command=lambda:self.safe(self.delete_collection))
  menu.tk_popup(self.root.winfo_pointerx(),self.root.winfo_pointery())
 def reset_selected(self):
  if messagebox.askyesno('Reset position','Reset only the selected recording to 0:00?',parent=self.root):self.library.reset()
 def rename_collection(self):
  name=simpledialog.askstring('Rename collection','New name:',parent=self.root)
  if name:self.library.collection('folder_rename',name);self.nav_signature=None
 def delete_collection(self):
  if messagebox.askyesno('Delete collection','Delete this collection? Audio files will remain.',parent=self.root):self.library.collection('folder_delete');self.nav_signature=None
 def bookmark(self):
  name=simpledialog.askstring('Bookmark','Name this moment:',parent=self.root)
  if name is not None:self.library.mark(name)
 def bookmarks(self):
  pop=tk.Toplevel(self.root);pop.title('Bookmarks for the current shiur');pop.geometry('430x330');items=tk.Listbox(pop,relief='flat');items.pack(fill='both',expand=True,padx=16,pady=16);marks=list(self.library.bookmarks())
  for mark in marks:items.insert('end',f"{clock(mark['position'])}   {mark['name']}")
  def action(delete=False):
   if items.curselection():self.library.bookmark_action(marks[items.curselection()[0]]['id'],delete);pop.destroy()
  self.button(pop,'Jump to bookmark',lambda:action()).pack(side='left',padx=16,pady=12);self.button(pop,'Delete',lambda:action(True)).pack(side='right',padx=16)
 def settings(self):
  pop=tk.Toplevel(self.root);pop.title('Settings & shortcuts');pop.geometry('490x440');pop.configure(bg=BG)
  self.label(pop,'Make it yours',20).pack(anchor='w',padx=24,pady=20)
  auto=tk.BooleanVar(value=self.player.saved['autoNext']);tk.Checkbutton(pop,text='Automatically play the next recording',variable=auto,command=lambda:self.safe(lambda:self.command('autonext',value=auto.get())),bg=BG).pack(anchor='w',padx=24)
  global_keys=tk.BooleanVar(value=self.player.saved.get('globalShortcuts',False));tk.Checkbutton(pop,text='Enable shortcuts while using other apps',variable=global_keys,command=lambda:self.safe(lambda:self.shortcuts(global_keys.get())),bg=BG).pack(anchor='w',padx=24,pady=12)
  self.label(pop,'Space: play/pause  ·  Left / Right: skip\nCtrl+F: search  ·  Ctrl+O: choose folder  ·  Ctrl+B: bookmark\n\nGlobal keys: Ctrl+Alt+Shift+P: play/pause\nCtrl+Alt+Shift+Left / Right: skip',10,MUTED,justify='left').pack(anchor='w',padx=24,pady=12)
  self.button(pop,'Set sleep timer',self.timer).pack(anchor='w',padx=24)
  self.label(pop,'Minimize to keep listening. Closing the player saves and stops.\nAll recordings and listening positions stay on this computer.',9,MUTED,justify='left').pack(anchor='w',padx=24,pady=18)
 def timer(self):
  minutes=simpledialog.askinteger('Sleep timer','Minutes until pause (0 turns it off):',minvalue=0,maxvalue=180,parent=self.root)
  if minutes is not None:self.command('sleep_timer',minutes=minutes)
 def update_rows(self):
  with self.player.lock:tracks=self.library.tracks()
  ids=[t['id'] for t in tracks]
  for ident in self.tree.get_children():
   if ident not in ids:self.tree.delete(ident);self.rows.pop(ident,None)
  for index,track in enumerate(tracks):
   position=track.get('position',0);resume='Finished' if track.get('completed') else clock(position) if position else 'New'
   values=(track['name'],resume,clock(track['duration']) if track.get('duration') else '-')
   if not self.tree.exists(track['id']):self.tree.insert('',index,iid=track['id'],values=values)
   elif self.rows.get(track['id'])!=values:self.tree.item(track['id'],values=values)
   self.tree.move(track['id'],'',index);self.rows[track['id']]=values
  if self.library.selected in ids and not self.tree.selection():self.tree.selection_set(self.library.selected)
  folders=self.player.saved['folders'];name=next((f['name'] for f in folders if f['id']==self.library.view),'Continue listening' if self.library.view=='continue' else 'Your listening library')
  self.heading.configure(text=name);self.subtitle.configure(text=f'{len(tracks)} recordings · A separate place saved for every shiur.' if tracks else 'No recordings here yet. Choose a folder or try another search.')
  signature=(self.library.view,tuple((f['id'],f['name']) for f in folders))
  if signature!=self.nav_signature:
   self.nav_signature=signature
   for widget in self.nav.winfo_children():widget.destroy()
   for ident,title in [('all','All shiurim'),('continue','Continue listening')]+[(f['id'],f['name']) for f in folders]:
    b=self.button(self.nav,title,lambda i=ident:self.navigate(i),anchor='w');b.configure(bg='#D5E3D6' if ident==self.library.view else '#EAEDE5');b.pack(fill='x',pady=3)
 def refresh(self):
  if self.closed:return
  try:
   while not self.requests.empty():
    action=self.requests.get_nowait()
    if action=='show':self.root.deiconify();self.root.lift();self.root.focus_force()
    elif action=='hide':self.root.iconify()
    elif action=='folder':self.safe(self.choose_folder)
   with self.player.lock:state=self.player.snapshot();current=next((t for t in self.player.tracks if t['id']==state['currentId']),None)
   self.update_rows();self.folder_label.configure(text=str(self.player.root) if self.player.root else 'No folder selected')
   self.track_title.configure(text=current['name'] if current else 'Ready when you are');self.source.configure(text=current['source'] if current else 'Choose a recording to begin.')
   playing=state['status']=='playing' or bool(self.player.pending and self.player.pending['autoplay']);self.play_button.configure(text='Pause' if playing else 'Play')
   self.state_label.configure(text='Loading your saved place…' if state['status']=='loading' else 'Listening · your place is remembered' if playing else 'Paused · your place is remembered' if current else 'Every shiur keeps its own place')
   if not self.dragging:self.seek.configure(to=max(1,state['duration']));self.seek.set(state['position'])
   self.time.configure(text=f"{clock(state['position'])} / {clock(state['duration'])}");self.back.configure(text=f"-{state['skipSeconds']}s");self.forward.configure(text=f"+{state['skipSeconds']}s")
   self.status.configure(text=state['error'] or (f"Sleep timer · pauses in {clock(state['sleepRemaining'])}" if state['sleepRemaining'] else 'Saved automatically on this computer · Pick up any shiur where you left off.'))
  except Exception as error:self.status.configure(text=str(error))
  self.root.after(500,self.refresh)
 def close(self):
  try:
   with self.player.lock:self.player.capture();self.player.persist()
  except Exception as error:messagebox.showerror('Could not save your place',str(error),parent=self.root);return
  self.closed=True;self.root.destroy()
 def run(self):self.root.mainloop()
