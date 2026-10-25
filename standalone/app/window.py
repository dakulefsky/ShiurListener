"""Local desktop library. UI work stays on the Tk thread; audio runs independently."""
import queue,sys
import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox
from controller import clock

TITLE='Shiur Player — Your listening library'
FONT='Segoe UI' if sys.platform=='win32' else 'Helvetica'
BG='#E8EDF5'; PAPER='#FFFFFF'; INK='#0D172B'; MUTED='#475569'; GREEN='#214CDB'; LINE='#C6D1E1'; SIDEBAR='#111E36'


class SlimScrollbar(tk.Canvas):
 """Arrowless scrollbar with a narrow, draggable thumb."""
 def __init__(self,parent,command):
  super().__init__(parent,width=10,bg=PAPER,highlightthickness=0,bd=0)
  self.command=command;self.first=0.;self.last=1.;self.offset=0;self.last_paint=None
  self.thumb=self.create_line(5,0,5,1,width=4,fill='#8597B2',capstyle='round',state='hidden')
  self.bind('<Configure>',lambda _:self.paint());self.bind('<Button-1>',self.press);self.bind('<B1-Motion>',self.drag)
 def set(self,first,last):self.first=float(first);self.last=float(last);self.paint()
 def paint(self):
  height=self.winfo_height();key=(height,self.first,self.last)
  if key==self.last_paint:return
  self.last_paint=key;self.itemconfigure(self.thumb,state='normal' if self.last-self.first<.999 else 'hidden')
  self.coords(self.thumb,5,max(8,self.first*height),5,min(height-8,max(self.first*height+22,self.last*height)))
 def press(self,event):
  height=max(1,self.winfo_height());self.offset=event.y-self.first*height
  if not self.first*height<=event.y<=self.last*height:self.offset=0;self.command('moveto',max(0,min(1,event.y/height)))
 def drag(self,event):self.command('moveto',max(0,min(1,(event.y-self.offset)/max(1,self.winfo_height()))))

class ModernScale(tk.Canvas):
 """Flat seek/volume track; updates from playback do not send seek commands."""
 def __init__(self,parent,from_=0,to=1,value=0,command=None):
  super().__init__(parent,height=26,bg=PAPER,highlightthickness=0,bd=0,takefocus=1,cursor='hand2')
  self.maximum=to;self.minimum=from_;self.value=value;self.command=command;self.last_paint=None
  self.track=self.create_line(8,13,9,13,fill=LINE,width=4,capstyle='round')
  self.fill=self.create_line(8,13,9,13,fill=GREEN,width=4,capstyle='round')
  self.dot=self.create_oval(2,7,14,19,fill=GREEN,outline='')
  self.bind('<Configure>',lambda _:self.paint());self.bind('<Button-1>',self.pointer);self.bind('<B1-Motion>',self.pointer)
  self.bind('<Left>',lambda _:self.step(-1));self.bind('<Right>',lambda _:self.step(1))
 def configure(self,**kw):
  if 'to' in kw:self.maximum=kw.pop('to')
  if kw:super().configure(**kw)
  self.paint()
 def get(self):return self.value
 def set(self,value):self.value=max(self.minimum,min(self.maximum,float(value)));self.paint()
 def paint(self):
  width=max(20,self.winfo_width());key=(width,self.minimum,self.maximum,self.value)
  if key==self.last_paint:return
  self.last_paint=key;ratio=(self.value-self.minimum)/max(.001,self.maximum-self.minimum);x=8+ratio*(width-16)
  self.coords(self.track,8,13,width-8,13);self.coords(self.fill,8,13,x,13)
  self.itemconfigure(self.fill,state='normal' if x>8 else 'hidden');self.coords(self.dot,x-6,7,x+6,19)
 def pointer(self,event):
  self.focus_set();self.set(self.minimum+(event.x-8)/max(1,self.winfo_width()-16)*(self.maximum-self.minimum))
  if self.command:self.command(self.value)
 def step(self,direction):
  self.set(self.value+direction*(self.maximum-self.minimum)/100)
  if self.command:self.command(self.value)
  self.event_generate('<<ScaleChanged>>');return 'break'

class PlayerWindow:
 def __init__(self,player,library,shortcuts):
  self.player=player;self.library=library;self.shortcuts=shortcuts;self.requests=queue.SimpleQueue();self.closed=False;self.dragging=False;self.rows={};self.nav_signature=None;self.minimized=False;self.auto_bar=False;self.column_drag_blocked=False
  self.root=tk.Tk();self.root.title(TITLE);self.root.configure(bg=BG)
  screen_w,screen_h=self.root.winfo_screenwidth(),self.root.winfo_screenheight()
  self.minimum_size=(min(980,screen_w-40),min(640,screen_h-80))
  size=player.saved.get('windowSize',[1260,820])
  if not isinstance(size,list) or len(size)!=2 or not all(isinstance(n,int) for n in size):size=[1260,820]
  width=max(self.minimum_size[0],min(size[0],screen_w-40));height=max(self.minimum_size[1],min(size[1],screen_h-80))
  self.root.geometry(f'{width}x{height}');self.root.minsize(*self.minimum_size)
  self.root.option_add('*Font',(FONT,10));self.root.option_add('*Foreground',INK)
  style=ttk.Style(self.root);style.theme_use('clam')
  style.configure('TCombobox',fieldbackground=PAPER,background=PAPER,bordercolor=LINE,lightcolor=PAPER,darkcolor=PAPER,arrowsize=12,padding=5)
  style.map('TCombobox',fieldbackground=[('readonly',PAPER)],background=[('readonly',PAPER)],foreground=[('readonly',INK)],selectbackground=[('readonly',PAPER)],selectforeground=[('readonly',INK)])
  style.configure('TScale',sliderlength=14,sliderthickness=14,borderwidth=0,background=PAPER,troughcolor=LINE)
  style.layout('Treeview',[('Treeview.treearea',{'sticky':'nswe'})])
  style.configure('Treeview',background=PAPER,fieldbackground=PAPER,foreground=INK,rowheight=57,borderwidth=0,font=(FONT,11))
  style.configure('Treeview.Heading',background='#D6DFED',foreground=INK,font=(FONT,9,'bold'),padding=(8,14),relief='flat',borderwidth=0,lightcolor=BG,darkcolor=BG)
  style.map('Treeview',background=[('selected','#C9DAFF')],foreground=[('selected',INK)])
  style.configure('TScale',background=PAPER,troughcolor=LINE)
  self.player.show_window=lambda:self.requests.put('show');self.player.hide_window=lambda:self.requests.put('hide');self.player.choose_folder=lambda:self.requests.put('folder')
  self.build();self.root.protocol('WM_DELETE_WINDOW',self.close)
  for key,fn in [('<space>',self.toggle),('<Left>',lambda:self.skip(-1)),('<Right>',lambda:self.skip(1)),('<Control-b>',self.bookmark),('<Control-f>',lambda:self.search.focus_set())]:
   self.root.bind(key,lambda event,f=fn:self.key(event,f))
  self.root.bind('<Control-o>',lambda _:self.safe(self.choose_folder));self.root.bind('<Escape>',lambda _:self.root.focus_set())
  self.root.bind('<Unmap>',lambda event:self.root.after(80,self.check_window_state) if event.widget is self.root and not self.closed else None)
  self.root.bind('<Map>',lambda event:self.root.after(80,self.check_window_state) if event.widget is self.root and not self.closed else None)
  self.refresh()
 def label(self,parent,text,size=10,color=INK,bg=None,**kw):
  background=bg or parent.cget('bg')
  if background==SIDEBAR:color='#FFFFFF' if color==INK else '#B4C1D8' if color==MUTED else color
  return tk.Label(parent,text=text,font=(FONT,size,'bold') if size>=15 else (FONT,size),fg=color,bg=background,**kw)
 def button(self,parent,text,fn,primary=False,**kw):
  dark=parent.cget('bg')==SIDEBAR
  return tk.Button(parent,text=text,command=lambda:self.safe(fn),bg=GREEN if primary else parent.cget('bg'),fg='white' if primary or dark else INK,activebackground='#163BA5' if primary else '#263A5B' if dark else '#DCE6F5',activeforeground='white' if primary or dark else INK,relief='flat',bd=0,highlightthickness=1,highlightbackground=GREEN if primary else parent.cget('bg'),highlightcolor=GREEN,padx=14,pady=9,cursor='hand2',font=(FONT,10,'bold'),**kw)
 def set_options(self,widget,**options):
  changed={key:value for key,value in options.items() if str(widget.cget(key))!=str(value)}
  if changed:widget.configure(**changed)

 def build(self):
  self.sidebar=tk.Frame(self.root,bg=SIDEBAR,width=220);self.sidebar.pack(side='left',fill='y');self.sidebar.pack_propagate(False)
  self.label(self.sidebar,'Shiur Player',20,bg=SIDEBAR,anchor='w').pack(fill='x',padx=24,pady=(32,5))
  self.label(self.sidebar,'COLLECTIONS',9,MUTED).pack(anchor='w',padx=24,pady=(26,12))
  self.nav=tk.Frame(self.sidebar,bg=SIDEBAR);self.nav.pack(fill='x',padx=12)
  self.button(self.sidebar,'+  New collection',self.new_collection).pack(fill='x',padx=12,pady=14)
  bottom=tk.Frame(self.sidebar,bg=SIDEBAR);bottom.pack(side='bottom',fill='x',padx=12,pady=20)
  self.folder_label=self.label(bottom,'No folder selected',9,MUTED,wraplength=180,anchor='w');self.folder_label.pack(fill='x',padx=12,pady=10)
  self.button(bottom,'Open audio folder...',self.choose_folder).pack(fill='x')
  self.button(bottom,'Refresh recordings',lambda:self.command('rescan')).pack(fill='x')
  self.button(bottom,'Settings & shortcuts',self.settings).pack(fill='x')
  content=tk.Frame(self.root,bg=BG);content.pack(side='left',fill='both',expand=True,padx=28,pady=28)
  header=tk.Frame(content,bg=BG);header.pack(fill='x')
  self.heading=self.label(header,'All recordings',28,anchor='w');self.heading.pack(side='left',fill='x',expand=True,pady=(6,4))
  self.mini_button=self.button(header,'Mini player',lambda:self.command('floating_toggle'),True);self.mini_button.pack(side='right',padx=(12,0))
  self.subtitle=self.label(content,'0 recordings',10,MUTED,anchor='w');self.subtitle.pack(fill='x',pady=(0,22))
  body=tk.Frame(content,bg=BG);body.pack(fill='both',expand=True)
  left=tk.Frame(body,bg=BG);left.pack(side='left',fill='both',expand=True,padx=(0,20))
  self.label(left,'Search',10,MUTED,anchor='w').pack(fill='x',pady=(0,8))
  self.query=tk.StringVar();self.search=tk.Entry(left,textvariable=self.query,relief='flat',bg=PAPER,fg=INK,insertbackground=INK,font=(FONT,11));self.search.pack(fill='x',ipady=12)
  self.query.trace_add('write',lambda *_:self.search_changed())
  tk.Frame(left,bg=BG,height=16).pack()
  table=tk.Frame(left,bg=PAPER);table.pack(fill='both',expand=True)
  self.tree=ttk.Treeview(table,columns=('name','resume','duration'),show='headings',selectmode='extended',height=5)
  for name,title,width in [('name','RECORDING',260),('resume','RESUME AT',110),('duration','LENGTH',80)]:
   self.tree.heading(name,text=title,command=lambda column=name:self.safe(lambda:self.sort_by(column)));self.tree.column(name,width=width,minwidth=75,stretch=name=='name',anchor='w' if name=='name' else 'center')
  self.tree.tag_configure('current',foreground=GREEN)
  scroll=SlimScrollbar(table,self.tree.yview);self.tree.configure(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y');self.tree.pack(fill='both',expand=True)
  self.tree.bind('<<TreeviewSelect>>',self.select);self.tree.bind('<Double-1>',self.double_click);self.tree.bind('<Return>',lambda _:self.safe(self.resume))
  self.tree.bind('<ButtonPress-1>',self.list_press);self.tree.bind('<B1-Motion>',self.list_drag);self.tree.bind('<ButtonRelease-1>',self.list_release);self.tree.bind('<Motion>',self.list_motion)
  self.tree.bind('<Control-a>',self.select_all);self.tree.bind('<Button-3>',self.context_menu)
  actions=tk.Frame(left,bg=BG);actions.pack(fill='x',pady=(12,0))
  self.resume_button=self.button(actions,'Play selected',self.resume,True);self.resume_button.pack(side='left')
  self.organize_button=self.button(actions,'Add to collection',self.add_collection);self.organize_button.pack(side='left',padx=8)
  self.button(actions,'More',self.more).pack(side='right')
  self.selection_info=self.label(left,'',9,MUTED,anchor='w');self.selection_info.pack(fill='x',pady=(8,0))
  right=tk.Frame(body,bg=PAPER,width=310);right.pack(side='right',fill='y');right.pack_propagate(False)
  card_scroll=SlimScrollbar(right,lambda *args:card_canvas.yview(*args));card_scroll.pack(side='right',fill='y')
  card_canvas=tk.Canvas(right,bg=PAPER,highlightthickness=0,yscrollcommand=card_scroll.set);card_canvas.pack(fill='both',expand=True);card_canvas.bind('<MouseWheel>',lambda event:card_canvas.yview_scroll(-int(event.delta/120),'units'))
  self.card=tk.Frame(card_canvas,bg=PAPER,padx=18,pady=20)
  card_window=card_canvas.create_window(0,0,anchor='nw',window=self.card)
  self.card.bind('<Configure>',lambda _:card_canvas.configure(scrollregion=card_canvas.bbox('all')))
  card_canvas.bind('<Configure>',lambda event:card_canvas.itemconfigure(card_window,width=event.width))
  self.label(self.card,'NOW PLAYING',9,MUTED,anchor='w').pack(fill='x')
  tk.Frame(self.card,bg=PAPER,height=20).pack()
  self.track_title=self.label(self.card,'No recording selected',17,anchor='nw',justify='left',wraplength=260);self.track_title.pack(fill='x')
  self.source=self.label(self.card,'Choose a recording to begin.',9,MUTED,anchor='w',wraplength=260,justify='left');self.source.pack(fill='x',pady=(8,14))
  self.state_label=self.label(self.card,'Paused',9,GREEN,anchor='w',wraplength=260);self.state_label.pack(fill='x',pady=(0,12))
  self.seek=ModernScale(self.card,from_=0,to=1);self.seek.pack(fill='x');self.seek.bind('<ButtonPress-1>',lambda _:setattr(self,'dragging',True),add='+');self.seek.bind('<ButtonRelease-1>',self.seek_release);self.seek.bind('<<ScaleChanged>>',self.seek_release)
  self.time=self.label(self.card,'0:00 / 0:00',10,MUTED,anchor='w');self.time.pack(fill='x',pady=(4,12))
  controls=tk.Frame(self.card,bg=PAPER);controls.pack(fill='x')
  self.back=self.button(controls,'−15s',lambda:self.skip(-1));self.back.pack(side='left')
  self.play_button=self.button(controls,'Play',self.toggle,True);self.play_button.pack(side='left',expand=True,fill='x',padx=6)
  self.forward=self.button(controls,'+15s',lambda:self.skip(1));self.forward.pack(side='right')
  opts=tk.Frame(self.card,bg=PAPER);opts.pack(fill='x',pady=16)
  self.label(opts,'Speed',9,MUTED).pack(side='left');self.speed=ttk.Combobox(opts,values=['0.5','0.75','1','1.25','1.5','1.75','2'],state='readonly',width=5);self.speed.set(str(self.player.saved['speed']));self.speed.pack(side='left',padx=8);self.speed.bind('<<ComboboxSelected>>',lambda _:self.safe(lambda:self.command('speed',value=float(self.speed.get()))))
  self.label(opts,'Skip',9,MUTED).pack(side='left');self.interval=ttk.Combobox(opts,values=['10','15','60'],state='readonly',width=4);self.interval.set(str(self.player.saved['skipSeconds']));self.interval.pack(side='left',padx=8);self.interval.bind('<<ComboboxSelected>>',lambda _:self.safe(lambda:self.command('skip_interval',value=int(self.interval.get()))))
  self.label(self.card,'VOLUME',9,MUTED,anchor='w').pack(fill='x')
  volume=ModernScale(self.card,from_=0,to=1,value=self.player.saved['volume'],command=lambda value:self.safe(lambda:self.command('volume',value=float(value))));volume.pack(fill='x',pady=(6,12))
  self.button(self.card,'Mini player',lambda:self.command('floating_toggle')).pack(fill='x')
  self.button(self.card,'Add bookmark',self.bookmark).pack(fill='x')
  self.button(self.card,'View bookmarks',self.bookmarks).pack(fill='x')
  self.status=self.label(content,'',9,MUTED,anchor='w',wraplength=850);self.status.pack(fill='x',pady=(18,0))
 def safe(self,fn):
  try:return fn()
  except Exception as error:messagebox.showerror('Shiur Player',str(error),parent=self.root)
 def command(self,op,**kw):return self.player.command({'op':op,**kw})
 def key(self,event,fn):
  if isinstance(event.widget,(tk.Entry,ttk.Entry,ttk.Combobox,tk.Text,tk.Scale,ttk.Scale,ModernScale)):return
  if isinstance(event.widget,(tk.Button,ttk.Button,tk.Checkbutton)) and event.keysym in ('space','Return'):return
  self.safe(fn);return 'break'
 def search_changed(self):self.library.query=self.query.get();self.update_rows()
 def select(self,_=None):
  ids=self.tree.selection()
  if ids:self.library.selected=self.tree.focus() if self.tree.focus() in ids else ids[0]
  if hasattr(self,'selection_info'):
   self.set_options(self.selection_info,text=f'{len(ids)} selected' if ids else '')
   self.set_options(self.organize_button,state='normal' if ids else 'disabled');self.set_options(self.resume_button,state='normal' if ids else 'disabled')
 def selected_ids(self):return list(self.tree.selection()) or ([self.library.selected] if self.library.selected in self.player.paths else [])
 def select_all(self,_=None):self.tree.selection_set(self.tree.get_children());self.select();return 'break'
 def list_press(self,event):
  self.column_drag_blocked=self.tree.identify_region(event.x,event.y)=='separator'
  if self.column_drag_blocked:return 'break'
 def list_drag(self,event):
  if self.column_drag_blocked:return 'break'
 def list_release(self,event):
  blocked=self.column_drag_blocked;self.column_drag_blocked=False
  if blocked:return 'break'
 def list_motion(self,event):
  if self.tree.identify_region(event.x,event.y)=='separator':self.tree.configure(cursor='arrow');return 'break'
 def double_click(self,event):
  if self.tree.identify_region(event.x,event.y)=='separator':return 'break'
  ident=self.tree.identify_row(event.y)
  if ident:self.tree.selection_set(ident);self.tree.focus(ident);self.select();self.safe(self.resume)
 def context_menu(self,event):
  ident=self.tree.identify_row(event.y)
  if not ident:return
  if ident not in self.tree.selection():self.tree.selection_set(ident)
  self.tree.focus(ident);self.select();menu=tk.Menu(self.root,tearoff=False)
  menu.add_command(label='Play from saved position',command=lambda:self.safe(self.resume))
  menu.add_command(label=f'Add {len(self.selected_ids())} to collection…',command=lambda:self.safe(self.add_collection))
  if self.library.view not in ('all','continue'):menu.add_command(label='Remove selected from collection',command=lambda:self.safe(self.remove_selected))
  try:menu.tk_popup(event.x_root,event.y_root)
  finally:menu.grab_release()
 def sort_by(self,column):self.library.set_sort(column);self.update_rows()
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
 def navigate(self,view):
  self.library.view=view;self.library.explicit_sort=False;self.nav_signature=None;self.tree.selection_remove(self.tree.selection());self.update_rows()
 def choose_folder(self):
  path=filedialog.askdirectory(title='Choose your shiur audio folder',parent=self.root)
  if path:self.player.scan(path);self.library.selected=None;self.update_rows()
 def new_collection(self):
  name=simpledialog.askstring('New collection','Collection name:',parent=self.root)
  if name:self.library.collection('folder_create',name);self.nav_signature=None;self.update_rows()
 def add_collection(self):
  ids=self.selected_ids()
  if not ids:raise ValueError('Select a recording first.')
  selected=next(t for t in self.player.tracks if t['id']==ids[0])
  pop=tk.Toplevel(self.root);pop.title('Add recording to collection');pop.geometry('460x340');pop.configure(bg=PAPER);pop.transient(self.root)
  self.label(pop,selected['name'] if len(ids)==1 else f'{len(ids)} recordings selected',12,wraplength=410,justify='left').pack(anchor='w',padx=24,pady=(22,16))
  folders=list(self.player.saved['folders']);names=[f['name'] for f in folders]
  self.label(pop,'Choose a collection, or type a new name:',10,MUTED).pack(anchor='w',padx=24)
  target=ttk.Combobox(pop,values=names);target.pack(fill='x',padx=24,pady=12);target.focus_set()
  if names:target.current(0)
  self.label(pop,'Audio files stay in their original folder.',9,MUTED).pack(anchor='w',padx=24)
  def add():
   self.assign_collection(target.get(),ids);pop.destroy()
  self.button(pop,'Add recording' if len(ids)==1 else 'Add recordings',add,True).pack(anchor='e',padx=24,pady=22)
  pop.bind('<Return>',lambda _:self.safe(add))
 def assign_collection(self,name,ids=None):
  self.library.assign_many(self.selected_ids() if ids is None else ids,name)
  self.nav_signature=None;self.update_rows()
 def remove_selected(self):
  with self.player.lock:
   folder=next((f for f in self.player.saved['folders'] if f['id']==self.library.view),None)
   if not folder:raise ValueError('Open a collection first.')
   ids=set(self.selected_ids());folder['trackIds']=[ident for ident in folder['trackIds'] if ident not in ids];self.player.persist()
  self.update_rows()
 def check_window_state(self):
  if not self.closed:self.window_state_changed(self.root.state()=='iconic')
 def window_state_changed(self,minimized):
  if minimized==self.minimized:return
  self.minimized=minimized
  bar=self.player.floating_bar
  if not bar or not self.player.saved.get('miniOnMinimize',True):return
  try:
   if minimized:
    self.auto_bar=not self.player.saved.get('floatingVisible',False)
    bar.set_visible(True)
   elif self.auto_bar:bar.set_visible(False);self.auto_bar=False
  except Exception as error:
   self.auto_bar=False;self.player.error='Mini player: '+str(error)
   if minimized:self.root.deiconify()
 def more(self):
  menu=tk.Menu(self.root,tearoff=False);menu.add_command(label='Reset selected recording to the beginning',command=lambda:self.safe(self.reset_selected))
  if self.library.view not in ('all','continue'):
   menu.add_command(label='Remove selected from this collection',command=lambda:self.safe(self.remove_selected))
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
  pop=tk.Toplevel(self.root);pop.title('Settings & shortcuts');pop.geometry('530x570');pop.configure(bg=BG)
  self.label(pop,'Settings',20).pack(anchor='w',padx=24,pady=20)
  auto=tk.BooleanVar(value=self.player.saved['autoNext']);tk.Checkbutton(pop,text='Automatically play the next recording',variable=auto,command=lambda:self.safe(lambda:self.command('autonext',value=auto.get())),bg=BG).pack(anchor='w',padx=24)
  mini=tk.BooleanVar(value=self.player.saved.get('miniOnMinimize',True))
  def save_mini():
   with self.player.lock:self.player.saved['miniOnMinimize']=mini.get();self.player.persist()
  tk.Checkbutton(pop,text='Show mini player when minimized',variable=mini,command=save_mini,bg=BG).pack(anchor='w',padx=24,pady=8)
  speed_row=tk.Frame(pop,bg=BG);speed_row.pack(fill='x',padx=24,pady=6)
  self.label(speed_row,'Mini-player speed steps',10).pack(side='left')
  middle=ttk.Combobox(speed_row,values=['1 / 0.5 / 2 / 0.5','1 / 1.5 / 2 / 1.5'],state='readonly',width=20)
  middle.current(1 if self.player.saved.get('miniSpeedMiddle',.5)==1.5 else 0);middle.pack(side='right')
  def save_cycle(_):
   with self.player.lock:self.player.saved['miniSpeedMiddle']=1.5 if middle.current()==1 else .5;self.player.saved['miniSpeedCycleIndex']=None;self.player.persist()
  middle.bind('<<ComboboxSelected>>',save_cycle)
  global_keys=tk.BooleanVar(value=self.player.saved.get('globalShortcuts',False));tk.Checkbutton(pop,text='Enable shortcuts while using other apps',variable=global_keys,command=lambda:self.safe(lambda:self.shortcuts(global_keys.get())),bg=BG).pack(anchor='w',padx=24,pady=12)
  self.label(pop,'Space: play/pause  ·  Left / Right: skip\nCtrl+F: search  ·  Ctrl+O: choose folder  ·  Ctrl+B: bookmark\n\nGlobal keys: Ctrl+Alt+Shift+P: play/pause\nCtrl+Alt+Shift+Left / Right: skip',10,MUTED,justify='left').pack(anchor='w',padx=24,pady=12)
  self.button(pop,'Set sleep timer',self.timer).pack(anchor='w',padx=24)
  self.label(pop,'Minimize for mini player. Close to save and stop.',9,MUTED,justify='left').pack(anchor='w',padx=24,pady=18)
 def timer(self):
  minutes=simpledialog.askinteger('Sleep timer','Minutes until pause (0 turns it off):',minvalue=0,maxvalue=180,parent=self.root)
  if minutes is not None:self.command('sleep_timer',minutes=minutes)
 def update_rows(self):
  with self.player.lock:tracks=self.library.tracks()
  ids=[t['id'] for t in tracks];previous=list(self.tree.get_children());reorder=previous!=ids
  for ident in self.tree.get_children():
   if ident not in ids:self.tree.delete(ident);self.rows.pop(ident,None)
  for index,track in enumerate(tracks):
   position=track.get('position',0);resume='Finished' if track.get('completed') else clock(position) if position else 'New'
   values=(track['name'],resume,clock(track['duration']) if track.get('duration') else '-')
   if not self.tree.exists(track['id']):self.tree.insert('',index,iid=track['id'],values=values)
   elif self.rows.get(track['id'])!=values:self.tree.item(track['id'],values=values)
   if reorder:self.tree.move(track['id'],'',index)
   tags=('current',) if track['id']==self.player.saved['currentId'] else ()
   if tuple(self.root.tk.splitlist(self.tree.item(track['id'],'tags')))!=tags:self.tree.item(track['id'],tags=tags)
   self.rows[track['id']]=values
  if self.library.selected in ids and not self.tree.selection():self.tree.selection_set(self.library.selected)
  self.select()
  for column,title in [('name','RECORDING'),('resume','RESUME AT'),('duration','LENGTH')]:
   active=column==self.library.sort and (self.library.view!='continue' or self.library.explicit_sort)
   text=title+(' v' if self.library.descending else ' ^') if active else title
   if self.tree.heading(column,'text')!=text:self.tree.heading(column,text=text)
  folders=self.player.saved['folders'];name=next((f['name'] for f in folders if f['id']==self.library.view),'Continue listening' if self.library.view=='continue' else 'All recordings')
  self.set_options(self.heading,text=name);self.set_options(self.subtitle,text=f'{len(tracks)} recordings' if tracks else 'No recordings here yet. Choose a folder or try another search.')
  signature=(self.library.view,tuple((f['id'],f['name']) for f in folders))
  if signature!=self.nav_signature:
   self.nav_signature=signature
   for widget in self.nav.winfo_children():widget.destroy()
   for ident,title in [('all','All shiurim'),('continue','Continue listening')]+[(f['id'],f['name']) for f in folders]:
    b=self.button(self.nav,title,lambda i=ident:self.navigate(i),anchor='w');b.configure(bg=GREEN if ident==self.library.view else SIDEBAR);b.pack(fill='x',pady=3)
 def refresh(self):
  if self.closed:return
  try:
   self.check_window_state()
   while not self.requests.empty():
    action=self.requests.get_nowait()
    if action=='show':self.root.deiconify();self.root.lift();self.root.focus_force()
    elif action=='hide':self.root.iconify()
    elif action=='folder':self.safe(self.choose_folder)
   with self.player.lock:state=self.player.snapshot();current=next((t for t in self.player.tracks if t['id']==state['currentId']),None)
   self.update_rows()
   if self.speed.get()!=f"{state['speed']:g}":self.speed.set(f"{state['speed']:g}")
   if self.interval.get()!=str(state['skipSeconds']):self.interval.set(str(state['skipSeconds']))
   self.set_options(self.folder_label,text=str(self.player.root) if self.player.root else 'No folder selected')
   self.set_options(self.track_title,text=current['name'].rsplit('.',1)[0] if current else 'No recording selected');self.set_options(self.source,text=current['source'] if current and current['source']!=current['name'] else '' if current else 'Choose a recording to begin.')
   playing=state['status']=='playing' or bool(self.player.pending and self.player.pending['autoplay']);self.set_options(self.play_button,text='Pause' if playing else 'Play')
   self.set_options(self.state_label,text='Loading…' if state['status']=='loading' else 'Playing' if playing else 'Paused' if current else '')
   if not self.dragging:self.seek.configure(to=max(1,state['duration']));self.seek.set(state['position'])
   self.set_options(self.time,text=f"{clock(state['position'])} / {clock(state['duration'])}");self.set_options(self.back,text=f"-{state['skipSeconds']}s");self.set_options(self.forward,text=f"+{state['skipSeconds']}s")
   self.set_options(self.status,text=state['error'] or (f"Sleep timer · pauses in {clock(state['sleepRemaining'])}" if state['sleepRemaining'] else ''))
  except Exception as error:self.set_options(self.status,text=str(error))
  self.root.after(500,self.refresh)
 def close(self):
  try:
   with self.player.lock:
    self.player.capture()
    if self.root.state()=='normal':self.player.saved['windowSize']=[self.root.winfo_width(),self.root.winfo_height()]
    self.player.persist()
  except Exception as error:messagebox.showerror('Could not save your place',str(error),parent=self.root);return
  self.closed=True
  for callback in self.root.tk.call('after','info'):self.root.tk.call('after','cancel',callback)
  self.root.destroy()
 def run(self):self.root.mainloop()
