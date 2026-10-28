"""Local desktop library. UI work stays on the Tk thread; audio runs independently."""
import queue,sys,threading,pathlib
from rendering import rounded_png,icon_png
from version import APP_VERSION
import updater,profile_backup,hotkeys,speech_enhancement
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from controller import clock

TITLE='Shiur Player'
FONT='Segoe UI' if sys.platform=='win32' else 'Helvetica'
BG='#F3F2F7'; PAPER='#FFFFFF'; INK='#242332'; MUTED='#727080'; GREEN='#6558D3'; LINE='#E9E7F0'; SIDEBAR=BG
TINT='#EEEBFC'; HOVER='#EAE7F4'; ERROR='#B33D50'
VIEWS={'all':'All shiurim','continue':'Continue listening','unplayed':'Unplayed','finished':'Finished'}


def rounded_points(x,y,width,height,radius=18):
 r=min(radius,max(0,width/2),max(0,height/2));right=x+width;bottom=y+height
 return [x+r,y,right-r,y,right,y,right,y+r,right,bottom-r,right,bottom,right-r,bottom,x+r,bottom,x,bottom,x,bottom-r,x,y+r,x,y]

def single_line(value):
 """Keep external recording and collection names from adding layout rows."""
 return ' '.join(str(value).split())

class HoverTip:
 """Read clipped label text without expanding its surrounding panel."""
 def __init__(self,widget):
  self.widget=widget;self.pending=None;self.popup=None
  widget.bind('<Enter>',self.schedule,add='+')
  for event in ('<Leave>','<ButtonPress>','<Unmap>','<Destroy>'):widget.bind(event,self.hide,add='+')
 def schedule(self,event=None):
  self.hide();self.pending=self.widget.after(600,self.show)
 def hide(self,event=None):
  if self.pending is not None:
   self.widget.after_cancel(self.pending);self.pending=None
  if self.popup is not None:self.popup.destroy();self.popup=None
 def show(self):
  self.hide()
  if not self.widget.winfo_viewable():return
  text=self.widget.cget('text')
  if not text:return
  popup=tk.Toplevel(self.widget);self.popup=popup
  popup.withdraw();popup.overrideredirect(True)
  popup.attributes('-topmost',True)
  screen_w=self.widget.winfo_screenwidth();screen_h=self.widget.winfo_screenheight()
  tk.Label(popup,text=text,font=(FONT,10),bg=PAPER,fg=INK,justify='left',wraplength=min(480,max(80,screen_w-40)),padx=12,pady=8,relief='solid',bd=1).pack()
  popup.update_idletasks()
  x=max(0,min(self.widget.winfo_rootx(),screen_w-popup.winfo_reqwidth()))
  y=self.widget.winfo_rooty()+self.widget.winfo_height()+6
  if y+popup.winfo_reqheight()>screen_h:y=max(0,self.widget.winfo_rooty()-popup.winfo_reqheight()-6)
  popup.geometry(f'+{x}+{y}');popup.deiconify()

class RoundedCard(tk.Canvas):
 """Rounded surface with a real frame inside, preserving normal widget behavior."""
 def __init__(self,parent,inset=14,stretch=False,**kw):
  super().__init__(parent,bg=parent.cget('bg'),bd=0,highlightthickness=0,**kw)
  self.inset=inset;self.stretch=stretch
  self.shadow=self.create_image(1,3,anchor='nw')
  self.surface=self.create_image(1,1,anchor='nw');self.surface_key=None
  self.body=tk.Frame(self,bg=PAPER)
  self.window=self.create_window(inset,inset,anchor='nw',window=self.body)
  self.bind('<Configure>',self.resize)
  self.body.bind('<Configure>',self.content_changed)
 def content_changed(self,event=None):
  if not self.stretch:
   wanted=self.body.winfo_reqheight()+2*self.inset+3
   if self.winfo_reqheight()!=wanted:self.configure(height=wanted)
 def resize(self,event=None):
  width=self.winfo_width();height=self.winfo_height()
  key=(max(1,width-2),max(1,height-5))
  if key!=self.surface_key:
   self.surface_key=key
   self.shadow_image=tk.PhotoImage(master=self,data=rounded_png(*key,18,'#E4E1ED'))
   self.surface_image=tk.PhotoImage(master=self,data=rounded_png(*key,18,PAPER,LINE))
   self.itemconfigure(self.shadow,image=self.shadow_image);self.itemconfigure(self.surface,image=self.surface_image)
  options={'width':max(1,width-2*self.inset)}
  if self.stretch:options['height']=max(1,height-2*self.inset-3)
  self.itemconfigure(self.window,**options)

class SoftToggle(tk.Canvas):
 """A keyboard-operable switch paired with its label; keeps BooleanVar semantics."""
 def __init__(self,parent,text,variable,command):
  super().__init__(parent,height=40,bg=parent.cget('bg'),highlightthickness=0,bd=0,takefocus=1,cursor='hand2')
  self.variable=variable;self.command=command;self.focused=False
  self.track=self.create_image(1,7,anchor='nw');self.track_key=None
  self.thumb_image=tk.PhotoImage(master=self,data=rounded_png(16,16,8,PAPER))
  self.thumb=self.create_image(5,11,anchor='nw',image=self.thumb_image)
  self.caption=self.create_text(56,19,text=text,anchor='w',fill=INK,font=(FONT,10))
  self.bind('<ButtonRelease-1>',self.toggle);self.bind('<KeyRelease-space>',self.toggle);self.bind('<Return>',self.toggle)
  self.bind('<FocusIn>',lambda _:self.focus(True));self.bind('<FocusOut>',lambda _:self.focus(False))
  self.trace=variable.trace_add('write',lambda *_:self.paint())
  self.bind('<Destroy>',self.cleanup);self.paint()
 def cleanup(self,event):
  if event.widget is self:self.variable.trace_remove('write',self.trace)
 def focus(self,value):self.focused=value;self.paint()
 def paint(self):
  on=self.variable.get();key=(on,self.focused)
  if key!=self.track_key:
   self.track_key=key;self.track_image=tk.PhotoImage(master=self,data=rounded_png(40,24,12,GREEN if on else '#D8D5E2',GREEN if self.focused else ''));self.itemconfigure(self.track,image=self.track_image)
  x=23 if on else 5;self.coords(self.thumb,x,11)
 def toggle(self,event=None):
  self.focus_set();self.variable.set(not self.variable.get());self.command();return 'break'

class SlimScrollbar(tk.Canvas):
 """Arrowless scrollbar with a narrow, draggable thumb."""
 def __init__(self,parent,command):
  super().__init__(parent,width=10,bg=PAPER,highlightthickness=0,bd=0)
  self.command=command;self.first=0.;self.last=1.;self.offset=0;self.last_paint=None
  self.thumb=self.create_line(5,0,5,1,width=4,fill='#C3BFCE',capstyle='round',state='hidden')
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
 def __init__(self,parent,from_=0,to=1,value=0,command=None,dark=False):
  super().__init__(parent,height=26,bg=SIDEBAR if dark else PAPER,highlightthickness=0,bd=0,takefocus=1,cursor='hand2')
  self.maximum=to;self.minimum=from_;self.value=value;self.command=command;self.last_paint=None;self.focused=False
  self.track=self.create_line(8,13,9,13,fill=LINE,width=4,capstyle='round')
  self.fill=self.create_line(8,13,9,13,fill=GREEN,width=4,capstyle='round')
  self.dot_image=tk.PhotoImage(master=self,data=rounded_png(12,12,6,GREEN))
  self.dot=self.create_image(8,13,image=self.dot_image)
  self.bind('<Configure>',lambda _:self.paint());self.bind('<Button-1>',self.pointer);self.bind('<B1-Motion>',self.pointer)
  self.bind('<Left>',lambda _:self.step(-1));self.bind('<Right>',lambda _:self.step(1))
  self.bind('<FocusIn>',lambda _:self.focus(True));self.bind('<FocusOut>',lambda _:self.focus(False))
 def configure(self,**kw):
  if 'to' in kw:self.maximum=kw.pop('to')
  if kw:super().configure(**kw)
  self.paint()
 def focus(self,value):
  self.focused=value;size=18 if value else 12
  self.dot_image=tk.PhotoImage(master=self,data=rounded_png(size,size,size/2,GREEN,TINT if value else ''));self.itemconfigure(self.dot,image=self.dot_image)
 def get(self):return self.value
 def set(self,value):self.value=max(self.minimum,min(self.maximum,float(value)));self.paint()
 def paint(self):
  width=max(20,self.winfo_width());key=(width,self.minimum,self.maximum,self.value)
  if key==self.last_paint:return
  self.last_paint=key;ratio=(self.value-self.minimum)/max(.001,self.maximum-self.minimum);x=8+ratio*(width-16)
  self.coords(self.track,8,13,width-8,13);self.coords(self.fill,8,13,x,13)
  self.itemconfigure(self.fill,state='normal' if x>8 else 'hidden');self.coords(self.dot,x,13)
 def pointer(self,event):
  self.focus_set();self.set(self.minimum+(event.x-8)/max(1,self.winfo_width()-16)*(self.maximum-self.minimum))
  if self.command:self.command(self.value)
 def step(self,direction):
  self.set(self.value+direction*(self.maximum-self.minimum)/100)
  if self.command:self.command(self.value)
  self.event_generate('<<ScaleChanged>>');return 'break'

class SoftButton(tk.Canvas):
 """Compact rounded control with a native focus target and keyboard activation."""
 def __init__(self,parent,text,command,primary=False,**kw):
  import tkinter.font as tkfont
  self.caption=text;self.action=command;self.primary=primary;self.disabled=False;self.hover=False;self.focused=False
  self.align=kw.pop('anchor','center');characters=kw.pop('width',0)
  self.fill_color=GREEN if primary else parent.cget('bg');self.text_color='#FFFFFF' if primary else INK
  self.typeface=tkfont.Font(family=FONT,size=10,weight='bold' if primary else 'normal')
  width=46 if text in ('Play','Pause','Prev','Next') else max(self.typeface.measure(text)+28,self.typeface.measure('0')*characters+24)
  super().__init__(parent,width=width,height=40,bg=parent.cget('bg'),highlightthickness=0,bd=0,takefocus=1,cursor='hand2')
  self.shape=self.create_image(1,1,anchor='nw');self.shape_key=None
  self.icon_image_item=self.create_image(0,0);self.icon_key=None
  self.word=self.create_text(14,19,text=text,font=self.typeface,fill=self.text_color,anchor='w')
  self.glyph=self.create_polygon(0,0,1,1,fill=self.text_color,outline='')
  self.bar1=self.create_line(0,0,0,1,fill=self.text_color,width=3)
  self.bar2=self.create_line(0,0,0,1,fill=self.text_color,width=3)
  self.bind('<Configure>',lambda _:self.paint());self.bind('<Enter>',lambda _:self.set_hover(True));self.bind('<Leave>',lambda _:self.set_hover(False))
  self.bind('<ButtonPress-1>',lambda _:self.focus_set());self.bind('<ButtonRelease-1>',lambda e:self.invoke() if 0<=e.x<self.winfo_width() and 0<=e.y<self.winfo_height() else None)
  self.bind('<KeyRelease-space>',lambda _:self.invoke());self.bind('<Return>',lambda _:self.invoke())
  self.bind('<FocusIn>',lambda _:self.set_focus(True));self.bind('<FocusOut>',lambda _:self.set_focus(False))
 def set_hover(self,value):self.hover=value;self.paint()
 def set_focus(self,value):self.focused=value;self.paint()
 def invoke(self):
  if not self.disabled:return self.action()
 def cget(self,key):
  if key=='text':return self.caption
  if key=='state':return 'disabled' if self.disabled else 'normal'
  if key=='bg':return self.fill_color
  return super().cget(key)
 def configure(self,**kw):
  if 'text' in kw:self.caption=kw.pop('text')
  if 'state' in kw:self.disabled=kw.pop('state')=='disabled'
  if 'bg' in kw:self.fill_color=kw.pop('bg')
  if kw:super().configure(**kw)
  self.paint()
 def paint(self):
  width=max(1,self.winfo_width());height=max(1,self.winfo_height())

  fill=('#7568DF' if self.primary else HOVER) if self.hover and not self.disabled else self.fill_color
  key=(max(1,width-2),max(1,height-2),fill,self.focused)
  if key!=self.shape_key:
   self.shape_key=key;self.shape_image=tk.PhotoImage(master=self,data=rounded_png(key[0],key[1],16,fill,GREEN if self.focused else ''))
   self.itemconfigure(self.shape,image=self.shape_image)
  self.coords(self.word,14 if self.align=='w' else width/2,height/2)
  self.itemconfigure(self.word,text=self.caption,anchor='w' if self.align=='w' else 'center',fill='#A6A1B1' if self.disabled else self.text_color)
  icon=self.caption in ('Play','Pause','Prev','Next');cx,cy=width/2,height/2
  self.itemconfigure(self.word,state='hidden' if icon else 'normal')
  for item in (self.glyph,self.bar1,self.bar2):self.itemconfigure(item,state='hidden')
  self.itemconfigure(self.icon_image_item,state='normal' if icon else 'hidden')
  if icon:
   color='#A6A1B1' if self.disabled else self.text_color;key=(self.caption,color)
   if key!=self.icon_key:
    self.icon_key=key;self.icon_image=tk.PhotoImage(master=self,data=icon_png(*key));self.itemconfigure(self.icon_image_item,image=self.icon_image)
   self.coords(self.icon_image_item,cx,cy)



class PlayerWindow:
 def __init__(self,player,library,shortcuts):
  self.player=player;self.library=library;self.shortcuts=shortcuts;self.requests=queue.SimpleQueue();self.closed=False;self.dragging=False;self.rows={};self.nav_signature=None;self.minimized=False;self.auto_bar=False;self.column_drag_blocked=False;self.update_busy=False;self.speech_job=None;self.queue_window=None;self.tools_window=None;self.last_volume=1;self.dock_collapsed=bool(player.saved.get('mainDockCollapsed',False))
  global FONT
  self.root=tk.Tk();self.root.title(TITLE);self.root.configure(bg=BG)
  if sys.platform=='win32':
   import tkinter.font as tkfont
   if 'Rubik' in tkfont.families(self.root):FONT='Rubik'
  screen_w,screen_h=self.root.winfo_screenwidth(),self.root.winfo_screenheight()
  self.minimum_size=(min(980,screen_w-40),min(640,screen_h-80))
  size=player.saved.get('windowSize',[1260,820])
  if not isinstance(size,list) or len(size)!=2 or not all(isinstance(n,int) for n in size):size=[1260,820]
  width=max(self.minimum_size[0],min(size[0],screen_w-40));height=max(self.minimum_size[1],min(size[1],screen_h-80))
  self.root.geometry(f'{width}x{height}');self.root.minsize(*self.minimum_size)
  self.root.option_add('*Font',(FONT,10));self.root.option_add('*Foreground',INK)
  for key,value in [('*Background',BG),('*Entry.Background',PAPER),('*Entry.relief','flat'),('*Entry.highlightThickness',1),('*Entry.highlightBackground',LINE),('*Entry.highlightColor',GREEN),('*Listbox.background',PAPER),('*Listbox.selectBackground',TINT),('*Listbox.selectForeground',INK),('*Button.Background',PAPER),('*Button.relief','flat'),('*Button.borderWidth',0),('*Button.padX',16),('*Button.padY',8)]:self.root.option_add(key,value)
  style=ttk.Style(self.root);style.theme_use('clam')
  style.configure('TCombobox',fieldbackground=PAPER,background=PAPER,bordercolor=LINE,lightcolor=PAPER,darkcolor=PAPER,arrowsize=12,padding=5)
  style.map('TCombobox',fieldbackground=[('readonly',PAPER)],background=[('readonly',PAPER)],foreground=[('readonly',INK)],selectbackground=[('readonly',PAPER)],selectforeground=[('readonly',INK)])
  style.configure('TScale',sliderlength=14,sliderthickness=14,borderwidth=0,background=PAPER,troughcolor=LINE)
  style.layout('Treeview',[('Treeview.treearea',{'sticky':'nswe'})])
  style.configure('Treeview',background=PAPER,fieldbackground=PAPER,foreground=INK,rowheight=44,borderwidth=0,font=(FONT,11))
  style.configure('Treeview.Heading',background=PAPER,foreground=MUTED,font=(FONT,9),padding=(8,14),relief='flat',borderwidth=0,lightcolor=BG,darkcolor=BG)
  style.map('Treeview',background=[('selected',TINT)],foreground=[('selected',INK)])
  style.configure('TScale',background=PAPER,troughcolor=LINE)
  self.player.show_window=lambda:self.requests.put('show');self.player.hide_window=lambda:self.requests.put('hide');self.player.choose_folder=lambda:self.requests.put('folder')
  self.build();self.root.protocol('WM_DELETE_WINDOW',self.close)
  for key,fn in [('<space>',self.toggle),('<Left>',lambda:self.skip(-1)),('<Right>',lambda:self.skip(1)),('<Control-b>',self.bookmark),('<Control-f>',lambda:self.search.focus_set()),('<Control-j>',self.jump_to),('<Control-m>',lambda:self.command('floating_toggle'))]:
   self.root.bind(key,lambda event,f=fn:self.key(event,f))
  self.root.bind('<Control-o>',lambda _:self.safe(self.choose_folder));self.root.bind('<Escape>',lambda _:self.root.focus_set())
  self.root.bind('<Unmap>',lambda event:self.root.after(80,self.check_window_state) if event.widget is self.root and not self.closed else None)
  self.root.bind('<Map>',lambda event:self.root.after(80,self.check_window_state) if event.widget is self.root and not self.closed else None)
  self.refresh()
 def label(self,parent,text,size=10,color=INK,bg=None,**kw):
  background=bg or parent.cget('bg');kw.setdefault('anchor','w')
  return tk.Label(parent,text=text,font=(FONT,size,'bold') if size>=15 else (FONT,size),fg=color,bg=background,**kw)
 def button(self,parent,text,fn,primary=False,**kw):
  return SoftButton(parent,text,lambda:self.safe(fn),primary=primary,**kw)
 def ask_value(self,title,prompt,initialvalue='',minvalue=None,maxvalue=None):
  pop=tk.Toplevel(self.root);pop.title(title);pop.configure(bg=BG);pop.transient(self.root);pop.resizable(False,False)
  result=None
  self.label(pop,title,19).pack(anchor='w',padx=24,pady=(24,12))
  self.label(pop,prompt,10,MUTED,wraplength=420,justify='left').pack(anchor='w',padx=24,pady=(0,12))
  card=RoundedCard(pop,inset=12,width=440);card.pack(fill='x',padx=24)
  value=tk.StringVar(value=initialvalue)
  entry=tk.Entry(card.body,textvariable=value,relief='flat',bd=0,highlightthickness=0,bg=PAPER,fg=INK,insertbackground=GREEN,font=(FONT,12));entry.pack(fill='x',ipady=5)
  error=self.label(pop,'',9,ERROR,wraplength=420,justify='left');error.pack(fill='x',padx=24,pady=(8,0))
  def accept(event=None):
   nonlocal result
   candidate=value.get()
   if minvalue is not None:
    try:candidate=int(candidate.strip())
    except ValueError:error.configure(text='Enter a whole number.');return 'break'
    if not minvalue<=candidate<=maxvalue:error.configure(text=f'Enter a number from {minvalue} to {maxvalue}.');return 'break'
   result=candidate;pop.destroy();return 'break'
  row=tk.Frame(pop,bg=BG);row.pack(fill='x',padx=24,pady=(12,24))
  self.button(row,'Save',accept,True).pack(side='right')
  self.button(row,'Cancel',pop.destroy).pack(side='right',padx=8)
  pop.bind('<Return>',accept);pop.bind('<Escape>',lambda _:pop.destroy())
  pop.update_idletasks();pop.geometry(f'+{self.root.winfo_rootx()+max(0,(self.root.winfo_width()-pop.winfo_reqwidth())//2)}+{self.root.winfo_rooty()+max(0,(self.root.winfo_height()-pop.winfo_reqheight())//2)}')
  if not pop.winfo_viewable():pop.wait_visibility()
  entry.selection_range(0,'end');pop.grab_set();pop.lift();entry.focus_force();self.root.wait_window(pop)
  return result
 def set_options(self,widget,**options):
  changed={key:value for key,value in options.items() if str(widget.cget(key))!=str(value)}
  if changed:widget.configure(**changed)

 def build(self):
  self.dock_card=RoundedCard(self.root,inset=12);self.dock_card.pack(side='bottom',fill='x',padx=18,pady=(0,12))
  self.dock=self.dock_card.body
  top=tk.Frame(self.root,bg=BG);top.pack(fill='both',expand=True)
  self.sidebar=tk.Frame(top,bg=SIDEBAR,width=232);self.sidebar.pack(side='left',fill='y');self.sidebar.pack_propagate(False)
  brand=tk.Frame(self.sidebar,bg=SIDEBAR);brand.pack(fill='x',padx=16,pady=(30,30))
  self.brand_image=tk.PhotoImage(file=str(pathlib.Path(__file__).parent/'assets/brand-mark.png'))
  self.brand_small=self.brand_image.subsample(2,2)
  tk.Label(brand,image=self.brand_small,bg=SIDEBAR).pack(side='left',padx=(0,8))
  self.root.iconphoto(True,self.brand_image)
  if sys.platform=='win32':self.root.iconbitmap(default=str(pathlib.Path(__file__).parent/'assets/shiur-player.ico'))
  self.label(brand,'Shiur Player',15,anchor='w').pack(side='left',fill='x',expand=True)
  bottom=tk.Frame(self.sidebar,bg=SIDEBAR);bottom.pack(side='bottom',fill='x',padx=10,pady=(6,12))
  self.folder_label=self.label(bottom,'No folder selected',9,MUTED,wraplength=170,anchor='w');self.folder_label.pack(fill='x',padx=12,pady=(6,8))
  self.button(bottom,'Open audio folder...',self.choose_folder,anchor='w').pack(fill='x')
  self.button(bottom,'Settings & backup',self.settings,anchor='w').pack(fill='x')
  nav_canvas=tk.Canvas(self.sidebar,bg=SIDEBAR,highlightthickness=0);nav_canvas.pack(fill='both',expand=True,padx=10)
  self.nav=tk.Frame(nav_canvas,bg=SIDEBAR);nav_id=nav_canvas.create_window(0,0,anchor='nw',window=self.nav)
  self.nav.bind('<Configure>',lambda _:nav_canvas.configure(scrollregion=nav_canvas.bbox('all')))
  nav_canvas.bind('<Configure>',lambda e:nav_canvas.itemconfigure(nav_id,width=e.width))
  nav_canvas.bind('<MouseWheel>',lambda e:nav_canvas.yview_scroll(-int(e.delta/120),'units'))
  self.nav_canvas=nav_canvas
  content=tk.Frame(top,bg=BG);content.pack(side='left',fill='both',expand=True,padx=(8,24),pady=(12,8))
  title_row=tk.Frame(content,bg=BG);title_row.pack(fill='x')
  self.heading=self.label(title_row,'All shiurim',20,anchor='w',width=1);self.heading.pack(side='left',fill='x',expand=True)
  self.mini_button=self.button(title_row,'Mini player',lambda:self.command('floating_toggle'));self.mini_button.pack(side='right')
  self.update_button=self.button(title_row,'Check for updates',self.check_updates);self.update_button.pack(side='right',padx=(0,6))
  self.heading_tip=HoverTip(self.heading)
  self.subtitle=self.label(content,'0 recordings',10,MUTED,anchor='w');self.subtitle.pack(fill='x',pady=(0,8))
  self.search_card=RoundedCard(content,inset=8);self.search_card.pack(fill='x',pady=(0,8))
  search_row=self.search_card.body
  self.label(search_row,'Search',10,MUTED).pack(side='left',padx=(0,12))
  self.query=tk.StringVar();self.search=tk.Entry(search_row,textvariable=self.query,relief='flat',bg=PAPER,fg=INK,insertbackground=INK,font=(FONT,11),highlightthickness=0,bd=0);self.search.pack(side='left',fill='x',expand=True,ipady=6)
  self.query.trace_add('write',lambda *_:self.search_changed())
  self.button(search_row,'Clear',lambda:self.query.set('')).pack(side='right')
  self.button(search_row,'Refresh',lambda:self.command('rescan')).pack(side='right')
  actions=tk.Frame(content,bg=BG);actions.pack(side='bottom',fill='x',pady=(12,0))
  self.resume_button=self.button(actions,'Play selected',self.resume,True);self.resume_button.pack(side='left')
  self.organize_button=self.button(actions,'Add to collection',self.add_collection);self.organize_button.pack(side='left',padx=5)
  self.button(actions,'More ···',self.more).pack(side='right')
  self.selection_info=self.label(actions,'',9,MUTED,anchor='w');self.selection_info.pack(side='left',padx=6)
  self.library_card=RoundedCard(content,inset=8,stretch=True);self.library_card.pack(fill='both',expand=True)
  table=self.library_card.body
  self.tree=ttk.Treeview(table,columns=('name','resume','duration'),show='headings',selectmode='extended',height=4)
  for name,title,width in [('name','Recording',400),('resume','Saved place',112),('duration','Length',90)]:
   self.tree.heading(name,text=title,anchor='w' if name=='name' else 'center',command=lambda column=name:self.safe(lambda:self.sort_by(column)));self.tree.column(name,width=width,minwidth=75,stretch=name=='name',anchor='w' if name=='name' else 'center')
  self.tree.tag_configure('current',foreground=GREEN,font=(FONT,11,'bold'))
  self.tree.tag_configure('alternate',background='#FCFBFE')
  scroll=SlimScrollbar(table,self.tree.yview);self.tree.configure(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y');self.tree.pack(fill='both',expand=True)
  self.empty=self.label(table,'',14,MUTED,justify='center')
  self.tree.bind('<<TreeviewSelect>>',self.select);self.tree.bind('<Double-1>',self.double_click);self.tree.bind('<Return>',lambda _:self.safe(self.resume))
  self.tree.bind('<ButtonPress-1>',self.list_press);self.tree.bind('<B1-Motion>',self.list_drag);self.tree.bind('<ButtonRelease-1>',self.list_release);self.tree.bind('<Motion>',self.list_motion)
  self.tree.bind('<Control-a>',self.select_all);self.tree.bind('<Button-3>',self.context_menu)
  self.tree.bind('<Control-q>',lambda _:self.safe(lambda:self.add_queue(False)))
  info=tk.Frame(self.dock,bg=PAPER);info.pack(fill='x')
  track_info=tk.Frame(info,bg=PAPER);track_info.pack(side='left',fill='x',expand=True)
  eyebrow=tk.Frame(track_info,bg=PAPER);self.dock_eyebrow=eyebrow;eyebrow.pack(fill='x')
  self.label(eyebrow,'Now playing',9,MUTED).pack(side='left')
  self.state_label=self.label(eyebrow,'',9,MUTED);self.state_label.pack(side='left',padx=14)
  self.track_title=self.label(track_info,'No recording selected',13,anchor='w',width=1);self.track_title.pack(fill='x',pady=(4,0))
  self.source=self.label(track_info,'Choose an audio folder to begin.',9,MUTED,anchor='w',width=1);self.source.pack(fill='x',pady=(2,0))
  self.title_tip=HoverTip(self.track_title);self.source_tip=HoverTip(self.source)
  self.dock_toggle=self.button(info,'Collapse player',self.toggle_dock);self.dock_toggle.pack(side='right',padx=(8,0))
  self.compact_play=self.button(info,'Play',self.toggle,True)
  self.compact_speed=self.button(info,'1×',lambda:self.command('speed_cycle'))
  self.queue_button=self.button(info,'Queue',self.show_queue);self.queue_button.pack(side='right')
  timeline=tk.Frame(self.dock,bg=PAPER);self.dock_timeline=timeline;timeline.pack(fill='x',pady=(8,4))
  self.time=self.label(timeline,'0:00 / 0:00',10,MUTED,width=17,anchor='w');self.time.pack(side='left')
  self.remaining=self.label(timeline,'',10,MUTED,width=16,anchor='e');self.remaining.pack(side='right')
  self.seek=ModernScale(timeline,from_=0,to=1,dark=False);self.seek.pack(fill='x',expand=True);self.seek.bind('<ButtonPress-1>',lambda _:setattr(self,'dragging',True),add='+');self.seek.bind('<ButtonRelease-1>',self.seek_release);self.seek.bind('<<ScaleChanged>>',self.seek_release)
  controls=tk.Frame(self.dock,bg=PAPER);self.dock_controls=controls;controls.pack(fill='x')
  self.button(controls,'Prev',lambda:self.command('previous')).pack(side='left')
  self.back=self.button(controls,'−15s',lambda:self.skip(-1));self.back.pack(side='left')
  self.play_button=self.button(controls,'Play',self.toggle,True,width=8);self.play_button.pack(side='left',padx=8)
  self.forward=self.button(controls,'+15s',lambda:self.skip(1));self.forward.pack(side='left')
  self.button(controls,'Next',lambda:self.command('next')).pack(side='left')
  self.button(controls,'Listening tools',self.listening_tools).pack(side='right')
  self.volume=ModernScale(controls,from_=0,to=1,value=self.player.saved['volume'],command=lambda value:self.safe(lambda:self.command('volume',value=float(value))),dark=False);self.volume.configure(width=90);self.volume.pack(side='right',padx=8)
  self.mute_button=self.button(controls,'Volume',self.mute);self.mute_button.pack(side='right')
  self.speed=tk.StringVar(value=f"{self.player.saved['speed']:g}")
  self.speed_button=self.button(controls,f"{self.speed.get()}×",lambda:self.command('speed_cycle'));self.speed_button.pack(side='right',padx=8);self.speed_button.bind('<Button-3>',lambda _:self.speed_menu())
  self.speed.trace_add('write',lambda *_:self.set_options(self.speed_button,text=f"{self.speed.get()}×"))
  self.label(controls,'Speed',9,MUTED).pack(side='right')
  self.interval=None
  self.status=self.label(self.dock,'',9,MUTED,anchor='w');self.status.pack(fill='x',pady=(6,0))
  self.apply_dock_layout()
 def toggle_dock(self):
  self.dock_collapsed=not self.dock_collapsed
  with self.player.lock:self.player.saved['mainDockCollapsed']=self.dock_collapsed;self.player.persist()
  self.apply_dock_layout()
 def apply_dock_layout(self):
  for widget in (self.dock_eyebrow,self.source,self.queue_button,self.dock_timeline,self.dock_controls,self.status,self.compact_play,self.compact_speed):widget.pack_forget()
  self.set_options(self.dock_toggle,text='Expand player' if self.dock_collapsed else 'Collapse player')
  self.track_title.configure(font=(FONT,11,'bold') if self.dock_collapsed else (FONT,13,'bold'))
  self.dock_card.inset=10 if self.dock_collapsed else 12
  self.dock_card.coords(self.dock_card.window,self.dock_card.inset,self.dock_card.inset)
  if self.dock_collapsed:
   self.compact_speed.pack(side='right',padx=6);self.compact_play.pack(side='right',padx=6)
   if self.status.cget('text'):self.status.pack(fill='x',pady=(6,0))
  else:
   self.dock_eyebrow.pack(fill='x',before=self.track_title);self.source.pack(fill='x',pady=(2,0))
   self.queue_button.pack(side='right')
   self.dock_timeline.pack(fill='x',pady=(4,2));self.dock_controls.pack(fill='x')
   if self.status.cget('text'):self.status.pack(fill='x',pady=(6,0))
  self.dock_card.content_changed();self.dock_card.resize()
 def speed_menu(self):
  menu=tk.Menu(self.root,tearoff=False,bg=PAPER,fg=INK,activebackground=TINT,activeforeground=GREEN,font=(FONT,11),bd=0)
  for rate in [.5,.75,1,1.25,1.5,1.75,2]:menu.add_command(label=f'{rate:g}×',command=lambda r=rate:self.safe(lambda:self.command('speed',value=r)))
  try:menu.tk_popup(self.speed_button.winfo_rootx(),self.speed_button.winfo_rooty()-210)
  finally:menu.grab_release()
 def check_updates(self):
  if self.update_busy:return
  self.update_busy=True;self.set_options(self.update_button,text='Checking...',state='disabled')
  def work():
   try:self.requests.put(('update_checked',updater.check()))
   except Exception as error:self.requests.put(('update_error',str(error)))
  threading.Thread(target=work,daemon=True).start()
 def update_event(self,event):
  action,value=event
  if action=='update_error':
   self.update_busy=False;self.set_options(self.update_button,text='Check for updates',state='normal')
   messagebox.showerror('Update unavailable',value+'\nYou can keep using the player and try again later.',parent=self.root)
  elif action=='update_checked':
   if value is None:
    self.update_busy=False;self.set_options(self.update_button,text='Check for updates',state='normal');messagebox.showinfo('Shiur Player',f'You have the latest version ({APP_VERSION}).',parent=self.root);return
   if not messagebox.askyesno('Update available',f"Install Shiur Player {value['version']}? Your listening positions will be saved and the player will restart.",parent=self.root):
    self.update_busy=False;self.set_options(self.update_button,text='Check for updates',state='normal');return
   self.set_options(self.update_button,text='Downloading...')
   def work():
    try:self.requests.put(('update_downloaded',updater.download(value)))
    except Exception as error:self.requests.put(('update_error',str(error)))
   threading.Thread(target=work,daemon=True).start()
  elif action=='update_downloaded':
   try:
    with self.player.lock:self.player.capture();self.player.persist()
    process=updater.install(value)
    if not self.close():
     process.terminate();self.update_event(('update_error','The update was postponed because your listening position could not be saved.'))
   except Exception as error:self.update_event(('update_error',str(error)))
 def safe(self,fn):
  try:return fn()
  except Exception as error:messagebox.showerror('Shiur Player',str(error),parent=self.root)
 def command(self,op,**kw):return self.player.command({'op':op,**kw})
 def key(self,event,fn):
  if isinstance(event.widget,(tk.Entry,ttk.Entry,ttk.Combobox,tk.Text,tk.Scale,ttk.Scale,ModernScale)):return
  if isinstance(event.widget,(tk.Button,ttk.Button,tk.Checkbutton,SoftButton,SoftToggle)) and event.keysym in ('space','Return'):return
  self.safe(fn);return 'break'
 def search_changed(self):self.library.query=self.query.get();self.update_rows()
 def select(self,_=None):
  ids=self.tree.selection()
  if ids:self.library.selected=self.tree.focus() if self.tree.focus() in ids else ids[0]
  if hasattr(self,'selection_info'):
   self.set_options(self.selection_info,text=f'{len(ids)} selected' if ids else '')
   self.set_options(self.organize_button,state='normal' if ids else 'disabled');self.set_options(self.resume_button,state='normal' if ids else 'disabled')
 def selected_ids(self):return list(self.tree.selection())
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
  self.tree.focus(ident);self.select();menu=tk.Menu(self.root,tearoff=False,bg=PAPER,fg=INK,activebackground=TINT,activeforeground=GREEN,relief='flat',bd=0,font=(FONT,10))
  menu.add_command(label='Play from saved position',command=lambda:self.safe(self.resume))
  menu.add_command(label='Rename recording…',command=lambda:self.safe(self.rename_recording))
  menu.add_command(label='Play next',command=lambda:self.safe(lambda:self.add_queue(True)))
  menu.add_command(label='Add to queue',command=lambda:self.safe(lambda:self.add_queue(False)))
  menu.add_separator()
  menu.add_command(label=f'Add {len(self.selected_ids())} to collection…',command=lambda:self.safe(self.add_collection))
  if self.library.view not in VIEWS:menu.add_command(label='Remove selected from collection',command=lambda:self.safe(self.remove_selected))
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
  name=self.ask_value('New collection','Collection name:')
  if name:self.library.collection('folder_create',name);self.nav_signature=None;self.update_rows()
 def add_collection(self):
  ids=self.selected_ids()
  if not ids:raise ValueError('Select a recording first.')
  selected=next(t for t in self.player.tracks if t['id']==ids[0])
  pop=tk.Toplevel(self.root);pop.title('Add recording to collection');pop.geometry('460x340');pop.configure(bg=PAPER);pop.transient(self.root)
  self.label(pop,selected['name'] if len(ids)==1 else f'{len(ids)} recordings selected',12,wraplength=410,justify='left').pack(anchor='w',padx=24,pady=(22,16))
  folders=list(self.player.saved['folders']);names=[f['name'] for f in folders]
  self.label(pop,'Choose a collection, or type a new name:',10,MUTED).pack(anchor='w',fill='x',padx=24)
  target=ttk.Combobox(pop,values=names);target.pack(fill='x',padx=24,pady=12);target.focus_set()
  if names:target.current(0)
  self.label(pop,'Audio files stay in their original folder.',9,MUTED).pack(anchor='w',fill='x',padx=24)
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
  menu=tk.Menu(self.root,tearoff=False,bg=PAPER,fg=INK,activebackground=TINT,activeforeground=GREEN,relief='flat',bd=0,font=(FONT,10))
  menu.add_command(label='Rename recording…',command=lambda:self.safe(self.rename_recording))
  menu.add_command(label='Play next',command=lambda:self.safe(lambda:self.add_queue(True)))
  menu.add_command(label='Add to queue',command=lambda:self.safe(lambda:self.add_queue(False)))
  menu.add_separator();menu.add_command(label='Reset selected recording to the beginning',command=lambda:self.safe(self.reset_selected))
  if self.library.view not in VIEWS:
   menu.add_command(label='Remove selected from this collection',command=lambda:self.safe(self.remove_selected))
   menu.add_command(label='Rename collection',command=lambda:self.safe(self.rename_collection));menu.add_command(label='Delete collection',command=lambda:self.safe(self.delete_collection))
  menu.tk_popup(self.root.winfo_pointerx(),self.root.winfo_pointery())
 def reset_selected(self):
  ids=self.selected_ids()
  if len(ids)!=1:raise ValueError('Select one recording to reset.')
  self.library.selected=ids[0]
  if messagebox.askyesno('Reset position','Reset only the selected recording to 0:00?',parent=self.root):self.library.reset()
 def rename_recording(self):
  ids=self.selected_ids()
  if len(ids)!=1:raise ValueError('Select one recording to rename.')
  ident=ids[0];track=next(t for t in self.player.tracks if t['id']==ident)
  name=self.ask_value('Rename recording','New filename (audio extension stays the same):',initialvalue=track['name'].rsplit('.',1)[0])
  if name is None:return
  self.library.rename(ident,name);self.rows.clear();self.update_rows()
 def rename_collection(self):
  name=self.ask_value('Rename collection','New name:')
  if name:self.library.collection('folder_rename',name);self.nav_signature=None
 def delete_collection(self):
  if messagebox.askyesno('Delete collection','Delete this collection? Audio files will remain.',parent=self.root):self.library.collection('folder_delete');self.nav_signature=None
 def bookmark(self):
  name=self.ask_value('Bookmark','Name this moment:')
  if name is not None:self.library.mark(name)
 def bookmarks(self):
  pop=tk.Toplevel(self.root);pop.title('Bookmarks for the current shiur');pop.geometry('430x330');pop.configure(bg=BG);items=tk.Listbox(pop,relief='flat',bg=PAPER,fg=INK,selectbackground=TINT,selectforeground=INK,highlightthickness=0,bd=0,activestyle='none');items.pack(fill='both',expand=True,padx=16,pady=16)
  with self.player.lock:track_id=self.player.saved['currentId'];marks=list(self.library.bookmarks())
  for mark in marks:items.insert('end',f"{clock(mark['position'])}   {mark['name']}")
  def action(delete=False):
   if items.curselection():self.library.bookmark_action(marks[items.curselection()[0]]['id'],delete,track_id=track_id);pop.destroy()
  self.button(pop,'Jump to bookmark',lambda:action()).pack(side='left',padx=16,pady=12);self.button(pop,'Delete',lambda:action(True)).pack(side='right',padx=16)
 def settings(self):
  pop=tk.Toplevel(self.root);pop.title('Settings & backup');pop.geometry('600x660');pop.configure(bg=BG);pop.transient(self.root)
  self.label(pop,f'Settings · {APP_VERSION}',20).pack(anchor='w',padx=24,pady=20)
  auto=tk.BooleanVar(value=self.player.saved['autoNext']);SoftToggle(pop,text='Automatically play the next recording',variable=auto,command=lambda:self.safe(lambda:self.command('autonext',value=auto.get()))).pack(anchor='w',fill='x',padx=24)
  mini=tk.BooleanVar(value=self.player.saved.get('miniOnMinimize',True))
  def save_mini():
   with self.player.lock:self.player.saved['miniOnMinimize']=mini.get();self.player.persist()
  SoftToggle(pop,text='Show mini player when minimized',variable=mini,command=save_mini).pack(anchor='w',fill='x',padx=24,pady=8)
  self.label(pop,'Speed button: 1× → 1.5× → 2× → 0.5× → 1×',10,MUTED).pack(anchor='w',fill='x',padx=24,pady=8)
  global_keys=tk.BooleanVar(value=self.player.saved.get('globalShortcuts',False));SoftToggle(pop,text='Enable shortcuts while using other apps',variable=global_keys,command=lambda:self.safe(lambda:self.shortcuts(global_keys.get()))).pack(anchor='w',fill='x',padx=24,pady=12)
  self.label(pop,'Space: play/pause  ·  Left / Right: skip\nCtrl+F: search  ·  Ctrl+O: folder  ·  Ctrl+B: bookmark\nCtrl+J: jump to time  ·  Ctrl+M: mini player\nIn the list: Ctrl+Q: add to queue\nCustomize global keys below; they also work in other apps.',10,MUTED,justify='left').pack(anchor='w',fill='x',padx=24,pady=12)
  self.button(pop,'Customize keyboard shortcuts…',lambda:(pop.destroy(),self.edit_shortcuts())).pack(anchor='w',padx=24,pady=(0,4))
  self.button(pop,'Audio enhancements…',lambda:(pop.destroy(),self.audio_settings())).pack(anchor='w',padx=24,pady=(10,0))
  self.label(pop,'LISTENING BACKUP',9,MUTED).pack(anchor='w',padx=24,pady=(18,8))
  row=tk.Frame(pop,bg=BG);row.pack(fill='x',padx=24)
  self.button(row,'Export backup…',self.export_backup).pack(side='left');self.button(row,'Restore backup…',self.restore_backup).pack(side='left',padx=8)
  self.label(pop,'Includes positions, collections and bookmarks. Audio stays in its folder.',9,MUTED,justify='left').pack(anchor='w',fill='x',padx=24,pady=12)
 def audio_settings(self):
  pop=tk.Toplevel(self.root);pop.title('Audio enhancements');pop.geometry('600x720');pop.minsize(560,680);pop.configure(bg=BG);pop.transient(self.root)
  self.label(pop,'Make speech easier to hear',20).pack(anchor='w',padx=24,pady=(18,4))
  self.label(pop,'Adjust the sound for quiet, muffled shiurim. Changes apply immediately and are saved automatically.',10,MUTED,wraplength=540,justify='left').pack(anchor='w',padx=24,pady=(0,12))
  initial=self.player.saved.get('audioEnhancement',{'bass':0,'body':0,'clarity':0,'treble':0})
  values={name:tk.DoubleVar(pop,value=float(initial.get(name,0))) for name in ('bass','body','clarity','treble')}
  labels={'bass':'Reduce rumble / boost low end','body':'Voice body','clarity':'Speech presence','treble':'High-frequency detail'}
  scales={}
  def apply():
   config={name:round(var.get(),1) for name,var in values.items()}
   self.safe(lambda:self.command('audio_enhancement',value=config))
   for name,var in values.items():readouts[name].configure(text=f'{var.get():+.1f} dB')
  def set_preset(name):
   presets={'Off':(0,0,0,0),'Speech clarity':(-2,-1,3,1),'Strong speech':(-3,-1,5,2),'Warm voice':(-1,2,1,-1)}
   for key,value in zip(values,presets[name]):values[key].set(value)
   apply()
  presetrow=tk.Frame(pop,bg=BG);presetrow.pack(fill='x',padx=24,pady=(0,12))
  self.label(presetrow,'START WITH A PRESET',9,MUTED).pack(anchor='w',pady=(0,6))
  buttons=tk.Frame(presetrow,bg=BG);buttons.pack(anchor='w')
  for name in ('Off','Speech clarity','Strong speech','Warm voice'):self.button(buttons,name,lambda n=name:set_preset(n),primary=(name=='Speech clarity')).pack(side='left',padx=(0,6))
  self.label(pop,'FINE-TUNE THE SOUND',9,MUTED).pack(anchor='w',padx=24,pady=(6,8))
  readouts={}
  for name,var in values.items():
   row=tk.Frame(pop,bg=BG);row.pack(fill='x',padx=24,pady=5)
   self.label(row,labels[name],10,INK).pack(side='left')
   readouts[name]=self.label(row,f'{var.get():+.1f} dB',10,MUTED);readouts[name].pack(side='right')
   scale=ModernScale(pop,from_=-6,to=6,value=var.get(),command=lambda value,n=name:(values[n].set(float(value)),readouts[n].configure(text=f'{float(value):+.1f} dB'),apply()),dark=False)
   scale.configure(width=500);scale.pack(fill='x',padx=24,pady=(0,4));scales[name]=scale
  self.label(pop,'Tip: start with Speech clarity. If the voice sounds thin or sharp, lower Speech presence or raise Voice body slightly.',10,MUTED,wraplength=540,justify='left').pack(anchor='w',padx=24,pady=(10,8))
  self.label(pop,'The equalizer reshapes tone; it does not remove noise or separate competing voices.',9,MUTED,wraplength=540,justify='left').pack(anchor='w',padx=24,pady=(0,12))
  self.label(pop,'OFFLINE SPEECH ENHANCEMENT',9,MUTED).pack(anchor='w',padx=24,pady=(2,6))
  self.label(pop,'Create a cleaned copy using the local speech model. It can reduce background noise and some competing voices. Your original recording is never changed.',10,MUTED,wraplength=540,justify='left').pack(anchor='w',padx=24,pady=(0,8))
  self.button(pop,'Enhance current shiur…',lambda:(pop.destroy(),self.speech_enhancement_dialog())).pack(anchor='w',padx=24,pady=(0,10))
  self.button(pop,'Done',pop.destroy,True).pack(anchor='e',padx=24,pady=(0,16))
  self.audio_controls={'popup':pop,'values':values,'scales':scales,'preset':set_preset,'apply':apply}
 def speech_enhancement_dialog(self):
  if self.speech_job and self.speech_job.get('busy'):
   messagebox.showinfo('Speech enhancement','An enhancement is already running. Cancel or wait for it to finish.',parent=self.root);return
  ident=self.player.saved.get('currentId')
  source=self.player.paths.get(ident)
  if not ident or source is None:
   messagebox.showinfo('Speech enhancement','Play or select a shiur first, then open Audio enhancements.',parent=self.root);return
  output=self.player.speech_cache_path(ident)
  pop=tk.Toplevel(self.root);pop.title('Offline speech enhancement');pop.geometry('540x300');pop.minsize(500,280);pop.configure(bg=BG);pop.transient(self.root)
  self.label(pop,'Make this shiur easier to hear',18).pack(anchor='w',padx=24,pady=(22,6))
  self.label(pop,'The player processes a separate copy on this computer. It may reduce hiss, hum and some background voices; results depend on the recording.',10,MUTED,wraplength=490,justify='left').pack(anchor='w',padx=24,pady=(0,12))
  self.label(pop,'Original audio is never overwritten. Processing can take a while for long recordings.',9,MUTED,wraplength=490,justify='left').pack(anchor='w',padx=24,pady=(0,12))
  status=self.label(pop,'Enhanced copy is ready.' if output and output.is_file() else 'Ready to process the current shiur.',10,INK,wraplength=490,justify='left');status.pack(anchor='w',padx=24,pady=(0,8))
  progress=ttk.Progressbar(pop,maximum=100,mode='determinate');progress.pack(fill='x',padx=24,pady=(0,14))
  row=tk.Frame(pop,bg=BG);row.pack(fill='x',padx=24,pady=(0,18))
  cancel_button=self.button(row,'Close',pop.destroy);cancel_button.pack(side='right',padx=(8,0))
  self.button(row,'Use original audio',lambda:self.safe(lambda:(self.command('speech_enhancement_enabled',value=False),status.configure(text='Original audio is active.')))).pack(side='right',padx=(8,0))
  start_button=self.button(row,'Use enhanced copy' if output and output.is_file() else 'Enhance current shiur',lambda:None,True);start_button.pack(side='left')
  job={'track_id':ident,'source':pathlib.Path(source),'output':output,'popup':pop,'status':status,'progress':progress,'start_button':start_button,'cancel_button':cancel_button,'busy':False,'cancel':None,'start':None}
  def use_enhanced():
   self.safe(lambda:self.command('speech_enhancement_enabled',value=True))
   if pop.winfo_exists():status.configure(text='Enhanced audio is enabled when a processed copy is available.')
  def cancel_or_close():
   current=self.speech_job
   if current is job and job['busy']:
    job['cancel'].set();status.configure(text='Cancelling…');cancel_button.configure(state='disabled')
   else:
    pop.destroy()
  def start():
   if job['busy']:return
   if job['output'] and job['output'].is_file():
    use_enhanced();return
   job['busy']=True;job['cancel']=threading.Event();self.speech_job=job
   start_button.configure(state='disabled',text='Enhancing…')
   cancel_button.configure(text='Cancel',command=cancel_or_close,state='normal')
   progress['value']=0;status.configure(text='Preparing audio locally…')
   def work():
    try:
     speech_enhancement.enhance_file(job['source'],job['output'],pathlib.Path(__file__).resolve().parent,job['cancel'],lambda value:self.requests.put(('speech_progress',value)))
     self.requests.put(('speech_done',(job['track_id'],str(job['output']))))
    except speech_enhancement.EnhancementCancelled:
     self.requests.put(('speech_cancelled',None))
    except Exception as error:
     self.requests.put(('speech_error',str(error)))
   threading.Thread(target=work,daemon=True).start()
  job['start']=start;start_button.configure(command=start);cancel_button.configure(command=cancel_or_close)
  pop.protocol('WM_DELETE_WINDOW',cancel_or_close)
  if self.speech_job is None:self.speech_job=job
 def edit_shortcuts(self):
  path=self.player.data_dir/'hotkeys.json'
  draft=hotkeys.load_config(path)
  pop=tk.Toplevel(self.root);pop.title('Keyboard shortcuts');pop.geometry('720x700');pop.minsize(660,650);pop.configure(bg=BG);pop.transient(self.root)
  self.label(pop,'Keyboard shortcuts',20).pack(anchor='w',padx=20,pady=(16,3))
  self.label(pop,'Choose what you want to do, then change its key combination. Your changes take effect when you save.',10,MUTED,wraplength=670,justify='left').pack(anchor='w',padx=20,pady=(0,10))
  enabled=tk.BooleanVar(pop,value=self.player.saved.get('globalShortcuts',False))
  SoftToggle(pop,text='Enable global shortcuts (they work while Shiur Player is in the background)',variable=enabled,command=lambda:None).pack(anchor='w',padx=20,pady=(0,6))
  self.label(pop,'1. SELECT AN ACTION',9,MUTED).pack(anchor='w',padx=20,pady=(8,4))
  frame=tk.Frame(pop,bg=BG);frame.pack(fill='both',expand=True,padx=20,pady=(0,8))
  tree=ttk.Treeview(frame,columns=('action','shortcut'),show='headings',selectmode='browse',height=7)
  tree.heading('action',text='When you press it');tree.heading('shortcut',text='Current key combination')
  tree.column('action',width=280);tree.column('shortcut',width=280)
  scrollbar=SlimScrollbar(frame,tree.yview);tree.configure(yscrollcommand=scrollbar.set);scrollbar.pack(side='right',fill='y');tree.pack(fill='both',expand=True)
  labels={'toggle':'Play or pause','back':'Skip backward','forward':'Skip forward','slower':'Decrease playback speed','faster':'Increase playback speed','previous':'Previous recording','next':'Next recording','skip10':'Set skip length to 10 seconds','skip15':'Set skip length to 15 seconds','skip60':'Set skip length to 60 seconds','stop':'Stop playback','floating':'Show or hide mini player','media_toggle':'Headphones: play / pause','media_back':'Headphones: skip backward','media_forward':'Headphones: skip forward'}
  selected=[None];variables={name:tk.BooleanVar(pop) for name in hotkeys.MODS};key=tk.StringVar(pop);disabled=tk.BooleanVar(pop)
  self.label(pop,'2. SET THE KEY COMBINATION',9,MUTED).pack(anchor='w',padx=20,pady=(2,4))
  self.label(pop,'Select the modifier keys to hold, then choose the main key. Regular keys need Ctrl, Alt, or Win. Media keys work on their own.',10,MUTED,wraplength=670,justify='left').pack(anchor='w',padx=20,pady=(0,6))
  row=tk.Frame(pop,bg=BG);row.pack(fill='x',padx=20,pady=4)
  for name,var in variables.items():tk.Checkbutton(row,text=name.title(),variable=var,bg=BG,activebackground=BG).pack(side='left',padx=(0,10))
  self.label(row,'Main key',9,MUTED).pack(side='left',padx=(8,4))
  combo=ttk.Combobox(row,textvariable=key,values=sorted(hotkeys.KEYS),state='readonly',width=12);combo.pack(side='left',padx=4)
  tk.Checkbutton(row,text='Turn this shortcut off',variable=disabled,bg=BG,activebackground=BG).pack(side='left',padx=(12,0))
  error=self.label(pop,'',10,ERROR,wraplength=670,justify='left');error.pack(fill='x',padx=20,pady=(4,2))
  def populate():
   for name in hotkeys.DEFAULTS:
    value=draft[name];label='Off' if value is None else ' + '.join(value['modifiers']+[value['key']])
    if tree.exists(name):tree.item(name,values=(labels[name],label))
    else:tree.insert('', 'end',iid=name,values=(labels[name],label))
  def show(event=None):
   if not tree.selection():return
   selected[0]=tree.selection()[0];value=draft[selected[0]];disabled.set(value is None)
   for name,var in variables.items():var.set(bool(value and name in value['modifiers']))
   key.set(value['key'] if value else hotkeys.DEFAULTS[selected[0]]['key'])
   error.configure(text='Selected: '+labels[selected[0]]+'. Change the settings below, then click Apply to action.')
  def assign():
   name=selected[0]
   if not name:
    error.configure(text='First select an action in the list above.');return False
   value=None if disabled.get() else {'modifiers':[name for name,var in variables.items() if var.get()],'key':key.get()}
   candidate={**draft,name:value}
   try:hotkeys.bindings(candidate)
   except ValueError as issue:error.configure(text=str(issue));return False
   draft.update(candidate);populate();error.configure(text='Shortcut updated in this window. Click Save changes to keep it.')
   return True
  def reset():
   draft.clear();draft.update(hotkeys.default_config());populate()
   if selected[0] and tree.exists(selected[0]):tree.selection_set(selected[0]);show()
   else:tree.selection_set('toggle');show()
   error.configure(text='Default shortcuts restored in this window. Click Save changes to keep them.')
  def save():
   if not assign():return
   try:
    hotkeys.save_config(path,draft);self.shortcuts(enabled.get())
    conflicts=[status.get('label',status['name'])+': '+status['error'] for status in self.player.hotkey_status if not status['registered']]
    if enabled.get() and conflicts:
     error.configure(text='Settings saved, but some global shortcuts could not start: '+'; '.join(conflicts));return
    pop.destroy()
   except (OSError,ValueError) as issue:error.configure(text=str(issue))
  row=tk.Frame(pop,bg=BG);row.pack(fill='x',padx=20,pady=(6,16))
  self.button(row,'Apply to action',assign,True).pack(side='left')
  self.button(row,'Restore defaults',reset).pack(side='left',padx=8)
  self.button(row,'Cancel',pop.destroy).pack(side='right')
  self.button(row,'Save changes',save,True).pack(side='right',padx=8)
  tree.bind('<<TreeviewSelect>>',show);populate();tree.selection_set('toggle');show()
  self.shortcut_controls={'popup':pop,'tree':tree,'key':key,'modifiers':variables,'disabled':disabled,'enabled':enabled,'assign':assign,'save':save,'reset':reset}
 def timer(self):
  minutes=self.ask_value('Sleep timer','Minutes until pause (0 turns it off):',minvalue=0,maxvalue=180)
  if minutes is not None:self.command('sleep_timer',minutes=minutes)
 def favorite_selected(self):
  self.library.favorite(self.selected_ids());self.update_rows()
 def favorite_current(self):
  ident=self.player.saved['currentId']
  if ident:self.library.favorite([ident]);self.update_rows()
 def add_queue(self,next_up=False):
  self.library.queue_add(self.selected_ids(),next_up=next_up);self.show_queue()
 def mute(self):
  volume=self.player.saved['volume']
  if volume:self.last_volume=volume
  self.command('volume',value=0 if volume else self.last_volume);self.volume.set(self.player.saved['volume'])
 def jump_to(self):
  if not self.player.saved['currentId']:raise ValueError('Choose a recording first.')
  value=self.ask_value('Jump to time','Enter minutes:seconds or hours:minutes:seconds:',initialvalue=clock(self.player.snapshot()['position']))
  if value is None:return
  pieces=value.strip().split(':')
  if not 1<=len(pieces)<=3 or any(not p.isdigit() for p in pieces) or any(int(p)>=60 for p in pieces[1:]):raise ValueError('Use a time such as 12:30 or 1:02:30.')
  seconds=sum(int(part)*60**index for index,part in enumerate(reversed(pieces)))
  self.command('seek',value=seconds)
 def listening_tools(self):
  if self.tools_window is not None and self.tools_window.winfo_exists():self.tools_window.lift();return
  pop=tk.Toplevel(self.root);self.tools_window=pop;pop.title('Listening tools');pop.geometry('560x610');pop.minsize(520,590);pop.configure(bg=BG);pop.transient(self.root)
  self.label(pop,'Listening tools',22).pack(anchor='w',padx=24,pady=(24,12))
  self.label(pop,'REPEAT A SECTION',9,MUTED).pack(anchor='w',padx=24,pady=(12,4))
  self.loop_label=self.label(pop,'Set A where the section starts, then B where it ends.',10,wraplength=490,justify='left');self.loop_label.pack(anchor='w',fill='x',padx=24,pady=8)
  row=tk.Frame(pop,bg=BG);row.pack(fill='x',padx=24)
  for text,op in [('Set A','loop_a'),('Set B','loop_b'),('Clear repeat','loop_clear')]:self.button(row,text,lambda o=op:self.command(o),op=='loop_b').pack(side='left',padx=(0,8))
  self.label(pop,'SLEEP TIMER',9,MUTED).pack(anchor='w',padx=24,pady=(24,4))
  self.sleep_label=self.label(pop,'Off',10);self.sleep_label.pack(anchor='w',fill='x',padx=24,pady=8)
  row=tk.Frame(pop,bg=BG);row.pack(fill='x',padx=24)
  for minutes in [15,30,45,60]:self.button(row,f'{minutes} min',lambda n=minutes:self.command('sleep_timer',minutes=n)).pack(side='left',padx=(0,4))
  row=tk.Frame(pop,bg=BG);row.pack(fill='x',padx=24,pady=(4,0))
  self.button(row,'End of recording',lambda:self.command('sleep_timer',mode='end')).pack(side='left')
  self.button(row,'Custom',self.timer).pack(side='left');self.button(row,'Turn off',lambda:self.command('sleep_timer',minutes=0)).pack(side='left')
  self.label(pop,'NAVIGATION',9,MUTED).pack(anchor='w',padx=24,pady=(24,8))
  row=tk.Frame(pop,bg=BG);row.pack(fill='x',padx=24)
  self.button(row,'Jump to time…',self.jump_to).pack(side='left')
  self.label(row,'Skip seconds',10,MUTED).pack(side='left',padx=(20,8))
  self.interval=ttk.Combobox(row,values=['10','15','60'],state='readonly',width=4);self.interval.set(str(self.player.saved['skipSeconds']));self.interval.pack(side='left');self.interval.bind('<<ComboboxSelected>>',lambda _:self.safe(lambda:self.command('skip_interval',value=int(self.interval.get()))))
  row=tk.Frame(pop,bg=BG);row.pack(fill='x',padx=24,pady=(18,0))
  self.button(row,'Add bookmark',self.bookmark).pack(side='left');self.button(row,'View bookmarks',self.bookmarks).pack(side='left',padx=8)
  self.refresh_tools(self.player.snapshot())
 def refresh_tools(self,state):
  if self.tools_window is None or not self.tools_window.winfo_exists():return
  a,b=state.get('loopA'),state.get('loopB')
  text=f'Repeating {clock(a)} to {clock(b)}' if b is not None else f'Start: {clock(a)} · Set B at the end of the section.' if a is not None else 'Set A where the section starts, then B where it ends.'
  self.set_options(self.loop_label,text=text)
  text=f"Pauses in {clock(state['sleepRemaining'])}" if state['sleepRemaining'] else 'Pauses at the end of this recording' if state.get('sleepAtEnd') else 'Off'
  self.set_options(self.sleep_label,text=text)
 def show_queue(self):
  if self.queue_window is not None and self.queue_window.winfo_exists():self.queue_window.lift();self.refresh_queue();return
  pop=tk.Toplevel(self.root);self.queue_window=pop;pop.title('Play queue');pop.geometry('700x500');pop.minsize(600,430);pop.configure(bg=BG);pop.transient(self.root)
  self.label(pop,'Play queue',24).pack(anchor='w',padx=22,pady=(22,8))
  auto=tk.BooleanVar(value=self.player.saved['autoNext']);self.queue_auto=auto
  SoftToggle(pop,text='Automatically continue to the next recording',variable=auto,command=lambda:self.safe(lambda:self.command('autonext',value=auto.get()))).pack(anchor='w',fill='x',padx=22,pady=(0,12))
  queue_card=RoundedCard(pop,inset=12,stretch=True,height=160);queue_card.pack(fill='both',expand=True,padx=22)
  frame=queue_card.body
  self.queue_tree=ttk.Treeview(frame,columns=('title','position'),show='headings',selectmode='browse',height=4)
  self.queue_tree.heading('title',text='RECORDING');self.queue_tree.heading('position',text='RESUME AT')
  self.queue_tree.column('title',width=420);self.queue_tree.column('position',width=100,stretch=False,anchor='center')
  self.queue_tree.tag_configure('current',foreground=GREEN,font=(FONT,11,'bold'))
  scroll=SlimScrollbar(frame,self.queue_tree.yview);self.queue_tree.configure(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y');self.queue_tree.pack(fill='both',expand=True)
  self.queue_tree.bind('<Double-1>',lambda _:self.safe(lambda:self.queue_action('play')));self.queue_tree.bind('<Return>',lambda _:self.safe(lambda:self.queue_action('play')))
  self.queue_tree.bind('<ButtonPress-1>',lambda e:'break' if self.queue_tree.identify_region(e.x,e.y)=='separator' else None)
  row=tk.Frame(pop,bg=BG);row.pack(fill='x',padx=22,pady=14)
  for text,action in [('Play','play'),('Move up','up'),('Move down','down'),('Remove','remove')]:self.button(row,text,lambda a=action:self.queue_action(a),action=='play').pack(side='left',padx=(0,6))
  self.queue_hint=self.label(pop,'',9,MUTED);self.queue_hint.pack(anchor='w',fill='x',padx=22,pady=(0,12))
  self.refresh_queue()
 def refresh_queue(self):
  if self.queue_window is None or not self.queue_window.winfo_exists():return
  with self.player.lock:ids=list(self.player.saved['queue']);tracks={t['id']:t for t in self.player.library()};current=self.player.saved['currentId'];auto=self.player.saved['autoNext']
  ids=[i for i in ids if i in tracks];old=list(self.queue_tree.get_children())
  for ident in old:
   if ident not in ids:self.queue_tree.delete(ident)
  for index,ident in enumerate(ids):
   track=tracks[ident];values=(('Playing · ' if ident==current else f'{index+1:02}  ')+track['name'],clock(track.get('position',0)))
   if not self.queue_tree.exists(ident):self.queue_tree.insert('',index,iid=ident,values=values)
   elif tuple(self.queue_tree.item(ident,'values'))!=values:self.queue_tree.item(ident,values=values)
   if old!=ids:self.queue_tree.move(ident,'',index)
   tags=('current',) if ident==current else ()
   if tuple(self.root.tk.splitlist(self.queue_tree.item(ident,'tags')))!=tags:self.queue_tree.item(ident,tags=tags)
  if self.queue_auto.get()!=auto:self.queue_auto.set(auto)
  self.set_options(self.queue_hint,text=f"{len(ids)} recordings · Select one to play or reorder." if ids else 'Select recordings in the library, then choose More → Add to queue.')
 def queue_action(self,action):
  ids=self.queue_tree.selection()
  if not ids:return
  ident=ids[0]
  if action=='play':
   if ident!=self.player.saved['currentId']:self.command('load',id=ident,queue=list(self.player.saved['queue']))
   self.command('play')
  elif action=='remove':self.library.queue_remove([ident])
  else:self.library.queue_move(ident,-1 if action=='up' else 1)
  self.refresh_queue()
 def export_backup(self):
  path=filedialog.asksaveasfilename(title='Back up listening library',defaultextension='.json',initialfile='Shiur Player backup.json',filetypes=[('Listening backup','*.json')],parent=self.root)
  if path:profile_backup.export_profile(self.player,path);messagebox.showinfo('Backup saved','Your listening positions, collections and bookmarks are backed up. Audio files stay in their original folder.',parent=self.root)
 def restore_backup(self):
  path=filedialog.askopenfilename(title='Restore listening backup',filetypes=[('Listening backup','*.json')],parent=self.root)
  if not path:return
  if not messagebox.askyesno('Restore backup','Replace saved positions, collections and bookmarks with this backup? A safety copy of your current library will be kept. Playback will pause.',parent=self.root):return
  safety=profile_backup.import_profile(self.player,path)
  self.library.selected=self.player.saved['currentId'];self.library.view='all';self.library.sort=self.player.saved.get('librarySort','name');self.library.descending=self.player.saved.get('librarySortDescending',False)
  self.library.explicit_sort=False;self.nav_signature=None;self.update_rows();self.volume.set(self.player.saved['volume'])
  messagebox.showinfo('Backup restored',f'Your listening library has been restored.\n\nSafety copy: {safety}',parent=self.root)
 def update_rows(self):
  with self.player.lock:tracks=self.library.tracks()
  ids=[t['id'] for t in tracks];previous=list(self.tree.get_children());reorder=previous!=ids
  for ident in self.tree.get_children():
   if ident not in ids:self.tree.delete(ident);self.rows.pop(ident,None)
  for index,track in enumerate(tracks):
   position=track.get('position',0);resume='Finished' if track.get('completed') else clock(position) if position else 'New'
   values=(track['name'].rsplit('.',1)[0],resume,clock(track['duration']) if track.get('duration') else '-')
   if not self.tree.exists(track['id']):self.tree.insert('',index,iid=track['id'],values=values)
   elif self.rows.get(track['id'])!=values:self.tree.item(track['id'],values=values)
   if reorder:self.tree.move(track['id'],'',index)
   tags=(('current',) if track['id']==self.player.saved['currentId'] else ())+(('alternate',) if index%2 else ())
   if tuple(self.root.tk.splitlist(self.tree.item(track['id'],'tags')))!=tags:self.tree.item(track['id'],tags=tags)
   self.rows[track['id']]=values
  if self.library.selected in ids and not self.tree.selection():self.tree.selection_set(self.library.selected)
  self.select()
  for column,title in [('name','Recording'),('resume','Saved place'),('duration','Length')]:
   active=column==self.library.sort and (self.library.view!='continue' or self.library.explicit_sort)
   text=title+(' v' if self.library.descending else ' ^') if active else title
   if self.tree.heading(column,'text')!=text:self.tree.heading(column,text=text)
  if not tracks:
   message='No matching recordings' if self.query.get() else 'Choose an audio folder to get started' if not self.player.root else 'No recordings in this view'
   self.set_options(self.empty,text=message);self.empty.place(relx=.5,rely=.55,anchor='center')
  else:self.empty.place_forget()
  folders=self.player.saved['folders'];name=next((f['name'] for f in folders if f['id']==self.library.view),VIEWS.get(self.library.view,'All shiurim'))
  self.set_options(self.heading,text=single_line(name));self.set_options(self.subtitle,text=f"{len(tracks)} recording{'s' if len(tracks)!=1 else ''}")
  signature=(self.library.view,tuple((f['id'],f['name']) for f in folders))
  if signature!=self.nav_signature:
   self.nav_signature=signature
   for widget in self.nav.winfo_children():widget.destroy()
   for ident,title in VIEWS.items():
    b=self.button(self.nav,title,lambda i=ident:self.navigate(i),anchor='w');b.configure(bg=TINT if ident==self.library.view else SIDEBAR);b.pack(fill='x',pady=2)
   self.label(self.nav,'Collections',10,MUTED,anchor='w').pack(fill='x',padx=12,pady=(24,10))
   for folder in folders:
    b=self.button(self.nav,folder['name'],lambda i=folder['id']:self.navigate(i),anchor='w');b.configure(bg=TINT if folder['id']==self.library.view else SIDEBAR);b.pack(fill='x',pady=2)
   self.button(self.nav,'+ New collection',self.new_collection,anchor='w').pack(fill='x',pady=(4,12))
   for widget in self.nav.winfo_children():widget.bind('<MouseWheel>',lambda e:self.nav_canvas.yview_scroll(-int(e.delta/120),'units'))
 def refresh(self):
  if self.closed:return
  try:
   self.check_window_state()
   while not self.requests.empty():
    action=self.requests.get_nowait()
    if isinstance(action,tuple):
     self.update_event(action)
     if self.closed:return
     continue
    if action=='show':self.root.deiconify();self.root.lift();self.root.focus_force()
    elif action=='hide':self.root.iconify()
    elif action=='folder':self.safe(self.choose_folder)
   with self.player.lock:state=self.player.snapshot();current=next((t for t in self.player.tracks if t['id']==state['currentId']),None)
   self.update_rows()
   if self.speed.get()!=f"{state['speed']:g}":self.speed.set(f"{state['speed']:g}")
   if self.interval is not None and self.interval.winfo_exists() and self.interval.get()!=str(state['skipSeconds']):self.interval.set(str(state['skipSeconds']))
   if not self.volume.winfo_containing(self.root.winfo_pointerx(),self.root.winfo_pointery()) is self.volume:self.volume.set(state['volume'])
   self.set_options(self.mute_button,text='Muted' if not state['volume'] else 'Volume')
   self.set_options(self.folder_label,text=self.player.root.name if self.player.root else 'No folder selected')
   self.set_options(self.track_title,text=single_line(current['name'].rsplit('.',1)[0]) if current else 'No recording selected');self.set_options(self.source,text=single_line(current['source']) if current and current['source']!=current['name'] else '' if current else 'Choose a recording to begin.')
   playing=state['status']=='playing' or bool(self.player.pending and self.player.pending['autoplay']);self.set_options(self.play_button,text='Pause' if playing else 'Play');self.set_options(self.compact_play,text='Pause' if playing else 'Play');self.set_options(self.compact_speed,text=f"{state['speed']:g}×")
   # A wrapped filename can grow the dock until the library has no space.
   self.set_options(self.track_title,wraplength=0)
   self.set_options(self.state_label,text='Loading…' if state['status']=='loading' else 'Playing' if playing else 'Paused' if current else '')
   if not self.dragging:self.seek.configure(to=max(1,state['duration']));self.seek.set(state['position'])
   self.set_options(self.time,text=f"{clock(state['position'])} / {clock(state['duration'])}");self.set_options(self.back,text=f"-{state['skipSeconds']}s");self.set_options(self.forward,text=f"+{state['skipSeconds']}s")
   self.set_options(self.remaining,text=f"{clock(max(0,state['duration']-state['position'])/state['speed'])} left at {state['speed']:g}×" if state['duration'] else '')
   self.set_options(self.queue_button,text=f"Queue · {len(state['queue'])}")
   sleep=f"Pauses in {clock(state['sleepRemaining'])}" if state['sleepRemaining'] else 'Pauses after this recording' if state.get('sleepAtEnd') else ''
   loop=f"Repeat {clock(state['loopA'])}–{clock(state['loopB'])}" if state.get('loopB') is not None else ''
   self.set_options(self.status,text=state['error'] or '   ·   '.join(t for t in (sleep,loop) if t),fg=ERROR if state['error'] else MUTED)
   if self.status.cget('text') and not self.status.winfo_manager():self.status.pack(fill='x',pady=(6,0))
   elif not self.status.cget('text') and self.status.winfo_manager():self.status.pack_forget()
   self.refresh_tools(state);self.refresh_queue()
  except Exception as error:
   self.set_options(self.status,text=str(error),fg=ERROR)
   if not self.status.winfo_manager():self.status.pack(fill='x',pady=(6,0))
  self.root.after(500,self.refresh)
 def close(self):
  try:
   with self.player.lock:
    self.player.capture()
    if self.root.state()=='normal':self.player.saved['windowSize']=[self.root.winfo_width(),self.root.winfo_height()]
    self.player.persist()
  except Exception as error:messagebox.showerror('Could not save your place',str(error),parent=self.root);return False
  self.closed=True
  for callback in self.root.tk.call('after','info'):self.root.tk.call('after','cancel',callback)
  self.root.destroy();return True
 def run(self):self.root.mainloop()

