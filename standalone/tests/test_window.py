"""Exercise the real desktop toolkit, including persistence across a new window."""
import os,pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'app'))
import window as window_module
from window import PlayerWindow
from engine import Player
from controller import LibraryController
import test_player
@unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform=='win32','Needs a desktop display')
class Tests(unittest.TestCase):
 def test_settings_and_audio_enhancement_dialogs_have_scrollable_content(self):
  fixture=test_player.Tests();fixture.setUp();window=None
  try:
   window=PlayerWindow(fixture.player,fixture.library,lambda _:None)
   window.settings();window.root.update()
   settings=next(child for child in window.root.winfo_children() if child.winfo_class()=='Toplevel')
   self.assertTrue(any(child.winfo_class()=='Canvas' for outer in settings.winfo_children() for child in outer.winfo_children()))
   self.assertFalse(any(isinstance(child,window_module.SoftButton) for child in settings.winfo_children()),
                    'Settings actions must live inside the scrollable content, not float outside it')
   settings.destroy()
   window.audio_settings();window.root.update()
   audio=next(child for child in window.root.winfo_children() if child.winfo_class()=='Toplevel')
   canvases=[child for outer in audio.winfo_children() for child in outer.winfo_children() if child.winfo_class()=='Canvas']
   self.assertTrue(canvases)
   self.assertTrue(any(isinstance(child,window_module.SlimScrollbar) for outer in audio.winfo_children() for child in outer.winfo_children()))
   self.assertFalse(any(isinstance(child,window_module.SoftButton) for child in audio.winfo_children()),
                    'Audio actions must live inside the scrollable content, not float outside it')
   def descendants(widget):
    for child in widget.winfo_children():
     yield child
     yield from descendants(child)
   description=next(w for w in descendants(audio) if isinstance(w,window_module.tk.Label) and w.cget('text').startswith('Adjust the sound'))
   preferred=int(description.cget('wraplength'))
   audio.geometry('480x420');window.root.update()
   self.assertLessEqual(int(description.cget('wraplength')),max(180,description.master.master.winfo_width()-48))
   audio.geometry('640x700');window.root.update()
   self.assertGreaterEqual(int(description.cget('wraplength')),min(preferred,description.master.master.winfo_width()-48))
  finally:
   if window:window.close()
   fixture.tearDown()

 def test_speech_enhancement_accepts_selected_recording_without_playing(self):
  fixture=test_player.Tests();fixture.setUp();window=None
  try:
   window=PlayerWindow(fixture.player,fixture.library,lambda _:None)
   ident=fixture.player.tracks[0]['id']
   fixture.player.saved['currentId']=None
   window.tree.selection_set(ident);window.library.selected=ident
   window.speech_enhancement_dialog();window.root.update()
   popups=[child for child in window.root.winfo_children() if child.winfo_class()=='Toplevel']
   self.assertEqual(len(popups),1)
   self.assertEqual(popups[0].title(),'Offline speech enhancement')
   popups[0].destroy()
  finally:
   if window:window.close()
   fixture.tearDown()

 def test_hidden_or_cleared_selection_cannot_reset_recordings(self):
  fixture=test_player.Tests();fixture.setUp();window=None
  try:
   window=PlayerWindow(fixture.player,fixture.library,lambda _:None)
   ident=fixture.player.tracks[0]['id'];fixture.library.selected=ident
   window.tree.selection_set(ident);window.query.set('no matching shiur');window.root.update()
   self.assertEqual(window.selected_ids(),[])
   with self.assertRaisesRegex(ValueError,'Select one'):window.reset_selected()
   with self.assertRaisesRegex(ValueError,'Select one'):window.rename_recording()
  finally:
   if window:window.close()
   fixture.tearDown()

 def test_refresh_error_remains_visible_in_collapsed_panel(self):
  from unittest.mock import patch
  fixture=test_player.Tests();fixture.setUp();window=None
  try:
   window=PlayerWindow(fixture.player,fixture.library,lambda _:None);window.toggle_dock();window.root.update()
   with patch.object(fixture.player,'snapshot',side_effect=RuntimeError('Audio output missing')):
    window.refresh();window.root.update()
   self.assertEqual(window.status.cget('text'),'Audio output missing');self.assertTrue(window.status.winfo_ismapped())
  finally:
   if window:window.close()
   fixture.tearDown()

 def test_main_playback_panel_collapses_without_stopping_and_remembers_choice(self):
  fixture=test_player.Tests();fixture.setUp();window=None
  try:
   fixture.library.play();fixture.player.tick();fixture.backend.position=38
   window=PlayerWindow(fixture.player,fixture.library,lambda _:None);window.root.update()
   expanded_height=window.dock_card.winfo_height();library_height=window.tree.winfo_height()
   window.toggle_dock();window.root.update()
   self.assertLess(window.dock_card.winfo_height(),expanded_height)
   self.assertGreater(window.tree.winfo_height(),library_height)
   self.assertTrue(window.compact_play.winfo_ismapped());self.assertFalse(window.seek.winfo_ismapped())
   self.assertEqual(fixture.backend.status,'playing');self.assertEqual(fixture.backend.position,38)
   window.compact_play.invoke();self.assertEqual(fixture.backend.status,'paused')
   window.compact_speed.invoke();self.assertEqual(fixture.player.saved['speed'],1.5)
   window.close();window=None
   restored=Player(None,fixture.root/'data',test_player.Audio());library=LibraryController(restored)
   window=PlayerWindow(restored,library,lambda _:None);window.root.update()
   self.assertTrue(window.dock_collapsed);self.assertTrue(window.compact_play.winfo_ismapped())
   window.toggle_dock();window.root.update();self.assertTrue(window.seek.winfo_ismapped())
  finally:
   if window:window.close()
   fixture.tearDown()
 def test_long_recording_title_does_not_cover_library_or_hide_collapse(self):
  fixture=test_player.Tests();fixture.setUp();window=None
  try:
   fixture.library.play();fixture.player.tick()
   window=PlayerWindow(fixture.player,fixture.library,lambda _:None)
   window.root.geometry(f'{window.minimum_size[0]}x{window.minimum_size[1]}');window.root.update()
   dock_height=window.dock_card.winfo_height();list_height=window.tree.winfo_height()
   current=next(t for t in fixture.player.tracks if t['id']==fixture.player.saved['currentId'])
   current['name']='A very long shiur title\nwith many words '*60+'.mp3'
   current['source']='A very long source\nfolder '*60
   window.refresh();window.root.update()
   self.assertEqual(window.dock_card.winfo_height(),dock_height)
   self.assertGreaterEqual(window.tree.winfo_height(),list_height)
   self.assertGreater(window.tree.winfo_height(),54)
   self.assertLessEqual(window.tree.winfo_rooty()+window.tree.winfo_height(),window.dock_card.winfo_rooty())
   self.assertTrue(window.dock_toggle.winfo_ismapped())
   self.assertGreater(window.dock_toggle.winfo_width(),1)
   window.dock_toggle.invoke();window.root.update()
   self.assertTrue(window.dock_collapsed)
   self.assertGreater(window.tree.winfo_height(),list_height)
  finally:
   if window:window.close()
   fixture.tearDown()
 def test_long_collection_keeps_mini_player_available_and_hover_shows_name(self):
  fixture=test_player.Tests();fixture.setUp();window=None
  try:
   name='A long collection name '*6
   fixture.library.collection('folder_create',name)
   window=PlayerWindow(fixture.player,fixture.library,lambda _:None)
   window.root.geometry(f'{window.minimum_size[0]}x{window.minimum_size[1]}');window.root.update()
   self.assertTrue(window.mini_button.winfo_ismapped())
   self.assertGreater(window.mini_button.winfo_width(),1)
   self.assertLessEqual(window.mini_button.winfo_rootx()+window.mini_button.winfo_width(),window.root.winfo_rootx()+window.root.winfo_width())
   self.assertLessEqual(window.heading.winfo_rootx()+window.heading.winfo_width(),window.mini_button.winfo_rootx())
   tip=window.heading_tip;tip.show();window.root.update()
   self.assertIsNotNone(tip.popup)
   self.assertEqual(tip.popup.winfo_children()[0].cget('text'),name.strip())
   self.assertLessEqual(tip.popup.winfo_rootx()+tip.popup.winfo_width(),window.root.winfo_screenwidth())
   tip.hide();self.assertIsNone(tip.popup)
   tip.schedule();self.assertIsNotNone(tip.pending)
   tip.hide();self.assertIsNone(tip.pending)
  finally:
   if window:window.close()
   fixture.tearDown()
 def test_expanded_player_leaves_room_for_recordings_at_minimum_size(self):
  fixture=test_player.Tests();fixture.setUp();window=None
  try:
   window=PlayerWindow(fixture.player,fixture.library,lambda _:None)
   window.root.geometry(f'{window.minimum_size[0]}x{window.minimum_size[1]}');window.root.update()
   self.assertFalse(window.dock_collapsed)
   self.assertTrue(window.seek.winfo_ismapped())
   self.assertLessEqual(window.tree.winfo_rooty()-window.root.winfo_rooty(),170)
   self.assertGreaterEqual(window.tree.winfo_height(),190)
   self.assertLessEqual(window.dock_card.winfo_height(),210)
   self.assertLessEqual(window.tree.winfo_rooty()+window.tree.winfo_height(),window.dock_card.winfo_rooty())
   for button in (window.mini_button,window.update_button,window.dock_toggle,window.play_button):
    self.assertTrue(button.winfo_ismapped());self.assertGreater(button.winfo_width(),1)
   self.assertFalse(window.status.winfo_ismapped())
   fixture.player.error='Audio output missing';window.refresh();window.root.update()
   self.assertTrue(window.status.winfo_ismapped())
   fixture.player.error='';window.refresh();window.root.update()
   self.assertFalse(window.status.winfo_ismapped())
  finally:
   if window:window.close()
   fixture.tearDown()
 def test_custom_shortcut_editor_saves_and_reloads_global_keys(self):
  import hotkeys
  fixture=test_player.Tests();fixture.setUp();window=None;calls=[]
  try:
   window=PlayerWindow(fixture.player,fixture.library,calls.append);window.edit_shortcuts();window.root.update()
   ui=window.shortcut_controls;ui['key'].set('F8')
   for name,var in ui['modifiers'].items():var.set(name=='CTRL')
   ui['enabled'].set(True);ui['save']();window.root.update()
   self.assertEqual(calls,[True])
   saved=hotkeys.load_config(fixture.player.data_dir/'hotkeys.json')
   self.assertEqual(saved['toggle'],{'modifiers':['CTRL'],'key':'F8'})
   window.edit_shortcuts();window.root.update()
   self.assertEqual(window.shortcut_controls['key'].get(),'F8')
   window.shortcut_controls['reset']()
   self.assertEqual(hotkeys.load_config(fixture.player.data_dir/'hotkeys.json'),saved)
   window.shortcut_controls['popup'].destroy()
  finally:
   if window:window.close()
   fixture.tearDown()
 def test_queue_actions_fit_at_minimum_window_size(self):
  from window import SoftButton
  fixture=test_player.Tests();fixture.setUp();window=None
  try:
   window=PlayerWindow(fixture.player,fixture.library,lambda _:None);window.show_queue()
   pop=window.queue_window;pop.geometry('600x430');window.root.update()
   buttons=[child for frame in pop.winfo_children() for child in frame.winfo_children() if isinstance(child,SoftButton)]
   self.assertEqual(len(buttons),4)
   for button in buttons:
    self.assertGreater(button.winfo_height(),1)
    self.assertLessEqual(button.winfo_rooty()+button.winfo_height(),pop.winfo_rooty()+pop.winfo_height())
  finally:
   if window:window.close()
   fixture.tearDown()
 def test_modern_switch_keyboard_does_not_pause_playback(self):
  import tkinter as tk
  from window import SoftToggle
  fixture=test_player.Tests();fixture.setUp();window=None
  try:
   fixture.library.play();fixture.player.tick()
   window=PlayerWindow(fixture.player,fixture.library,lambda _:None);window.root.update()
   value=tk.BooleanVar(window.root,value=False);calls=[]
   switch=SoftToggle(window.dock,'Automatic next',value,lambda:calls.append(value.get()));switch.pack(fill='x')
   window.root.update();switch.focus_force();window.root.update()
   switch.event_generate('<KeyPress-space>');switch.event_generate('<KeyRelease-space>');window.root.update()
   self.assertTrue(value.get());self.assertEqual(calls,[True]);self.assertEqual(fixture.backend.status,'playing')
  finally:
   if window:window.close()
   fixture.tearDown()
 def test_modern_input_validates_then_accepts_and_escape_cancels(self):
  import tkinter as tk
  fixture=test_player.Tests();fixture.setUp();window=None
  try:
   window=PlayerWindow(fixture.player,fixture.library,lambda _:None);window.root.update()
   def descendants(widget):
    for child in widget.winfo_children():
     yield child
     yield from descendants(child)
   def submit():
    pop=next(w for w in window.root.winfo_children() if isinstance(w,tk.Toplevel))
    entry=next(w for w in descendants(pop) if isinstance(w,tk.Entry))
    entry.delete(0,'end');entry.insert(0,'181');pop.event_generate('<Return>');window.root.update()
    self.assertTrue(pop.winfo_exists())
    entry.delete(0,'end');entry.insert(0,'30');pop.event_generate('<Return>')
   window.root.after(100,submit)
   self.assertEqual(window.ask_value('Timer','Minutes',minvalue=0,maxvalue=180),30)
   def cancel():
    pop=next(w for w in window.root.winfo_children() if isinstance(w,tk.Toplevel));pop.event_generate('<Escape>')
   window.root.after(100,cancel)
   self.assertIsNone(window.ask_value('Name','Name your collection'))
  finally:
   if window:window.close()
   fixture.tearDown()
 def test_minimize_opens_bar_and_restore_hides_only_automatic_bar(self):
  fixture=test_player.Tests();fixture.setUp();window=None
  class Bar:
   def __init__(self):self.calls=[];self.hwnd=123;self.status='ready'
   def set_visible(self,visible):self.calls.append(visible);fixture.player.saved['floatingVisible']=visible
  try:
   bar=Bar();fixture.player.floating_bar=bar;fixture.player.saved['floatingVisible']=False
   window=PlayerWindow(fixture.player,fixture.library,lambda _:None)
   window.window_state_changed(True);window.window_state_changed(True)
   window.window_state_changed(False);self.assertEqual(bar.calls,[True,False])
   fixture.player.saved['floatingVisible']=True;window.window_state_changed(True);window.window_state_changed(False)
   self.assertEqual(bar.calls,[True,False,True])
   fixture.player.saved['miniOnMinimize']=False;window.window_state_changed(True);self.assertEqual(len(bar.calls),3)
  finally:
   if window:window.close()
   fixture.tearDown()
 def test_new_collection_assignment_is_one_operation(self):
  fixture=test_player.Tests();fixture.setUp();window=None
  try:
   window=PlayerWindow(fixture.player,fixture.library,lambda _:None)
   fixture.library.selected=fixture.player.tracks[0]['id'];window.tree.selection_set(fixture.library.selected);window.assign_collection('My recordings')
   folders=fixture.player.saved['folders'];self.assertEqual(len(folders),1);self.assertEqual(folders[0]['trackIds'],[fixture.library.selected])
   window.assign_collection('my recordings');self.assertEqual(len(folders),1);self.assertEqual(len(folders[0]['trackIds']),1)
  finally:
   if window:window.close()
   fixture.tearDown()
 def test_custom_seek_and_volume_controls(self):
  from types import SimpleNamespace
  fixture=test_player.Tests();fixture.setUp();window=None
  try:
   fixture.library.play();fixture.player.tick()
   window=PlayerWindow(fixture.player,fixture.library,lambda _:None);window.root.update()
   window.seek.pointer(SimpleNamespace(x=window.seek.winfo_width()/2));window.seek_release(None)
   self.assertAlmostEqual(fixture.backend.position,60,delta=1)
   window.seek.step(1);self.assertGreater(fixture.backend.position,60)
   self.assertAlmostEqual(fixture.player.saved['tracks'][fixture.player.active]['position'],fixture.backend.position)
  finally:
   if window:window.close()
   fixture.tearDown()
 def test_batch_collections_sorting_and_saved_window_size(self):
  fixture=test_player.Tests();fixture.setUp();window=None
  try:
   window=PlayerWindow(fixture.player,fixture.library,lambda _:None);wanted=[min(1120,window.root.winfo_screenwidth()-40),min(740,window.root.winfo_screenheight()-80)];window.root.geometry(f'{wanted[0]}x{wanted[1]}');window.root.update()
   ids=list(window.tree.get_children());window.select_all();window.root.update()
   self.assertEqual(window.selection_info.cget('text'),'2 selected')
   window.assign_collection('A series')
   self.assertEqual(fixture.player.saved['folders'][0]['trackIds'],ids)
   window.assign_collection('a SERIES');self.assertEqual(len(fixture.player.saved['folders']),1)
   window.sort_by('name');window.sort_by('name');self.assertEqual(list(window.tree.get_children()),ids[::-1])
   self.assertEqual(set(window.tree.selection()),set(ids))
   view=fixture.player.saved['folders'][0]['id'];window.navigate(view);window.select_all();window.remove_selected()
   self.assertEqual(window.tree.get_children(),());self.assertEqual(len(fixture.player.paths),2)
   window.close();window=None
   restored=Player(None,fixture.root/'data',test_player.Audio());library=LibraryController(restored)
   self.assertEqual(restored.saved['windowSize'],wanted);self.assertTrue(library.descending)
   window=PlayerWindow(restored,library,lambda _:None);window.root.update()
   self.assertEqual([window.root.winfo_width(),window.root.winfo_height()],wanted)
  finally:
   if window:window.close()
   fixture.tearDown()
 def test_soft_button_command_can_be_rebound(self):
  import tkinter as tk
  from window import SoftButton
  fixture=test_player.Tests();fixture.setUp();window=None
  try:
   window=PlayerWindow(fixture.player,fixture.library,lambda _:None)
   calls=[]
   button=SoftButton(window.root,'Original',lambda:calls.append('old'))
   button.pack();window.root.update()
   button.configure(command=lambda:calls.append('new'))
   button.invoke()
   self.assertEqual(calls,['new'])
  finally:
   if window:window.close()
   fixture.tearDown()
 def test_space_on_focused_button_does_not_toggle_twice(self):
  import tkinter as tk
  fixture=test_player.Tests();fixture.setUp();window=None
  try:
   fixture.library.play();fixture.player.tick()
   window=PlayerWindow(fixture.player,fixture.library,lambda _:None);window.root.update()
   window.play_button.focus_force();window.root.update()
   window.play_button.event_generate('<KeyPress-space>');window.root.update()
   window.play_button.event_generate('<KeyRelease-space>');window.root.update()
   done=tk.BooleanVar(window.root);window.root.after(150,lambda:done.set(True));window.root.wait_variable(done)
   self.assertEqual(fixture.backend.status,'paused')
   window.play_button.event_generate('<KeyPress-space>');window.root.update()
   window.play_button.event_generate('<KeyRelease-space>');window.root.update()
   done=tk.BooleanVar(window.root);window.root.after(150,lambda:done.set(True));window.root.wait_variable(done)
   self.assertEqual(fixture.backend.status,'playing')
  finally:
   if window:window.close()
   fixture.tearDown()
 def test_multiple_resume_rows_and_reopen(self):
  fixture=test_player.Tests();fixture.setUp();window=None
  try:
   (fixture.audio/'03.wav').write_bytes(b'fake');fixture.player.scan();ids=[t['id'] for t in fixture.player.tracks]
   for ident,position in zip(ids,[65.432,23.789,119.9]):
    fixture.library.selected=ident;fixture.library.play(force=True);fixture.player.tick();fixture.backend.position=position;fixture.player.command({'op':'pause'})
   window=PlayerWindow(fixture.player,fixture.library,lambda _:None);window.root.update()
   self.assertEqual([window.tree.item(i,'values')[1] for i in ids],['1:05','0:23','1:59'])
   window.navigate('continue');window.root.update();self.assertEqual(list(window.tree.get_children()),ids[::-1])
   window.tree.selection_set(ids[0]);window.root.update();window.resume();fixture.player.tick();self.assertEqual(fixture.backend.position,65.432)
   window.query.set('03');window.root.update();self.assertEqual(list(window.tree.get_children()),[ids[2]])
   window.toggle();self.assertEqual(fixture.backend.status,'paused');window.close();window=None
   backend=test_player.Audio();player=Player(None,fixture.root/'data',backend);library=LibraryController(player);window=PlayerWindow(player,library,lambda _:None);window.root.update()
   for ident,position in zip(ids,[65.432,23.789,119.9]):
    window.tree.selection_set(ident);window.root.update();window.resume();player.tick();self.assertEqual(backend.position,position)
  finally:
   if window:window.close()
   fixture.tearDown()
 def test_update_handoff_saves_positions_and_cancels_if_close_fails(self):
  import json
  from unittest.mock import Mock,patch
  fixture=test_player.Tests();fixture.setUp();window=None
  try:
   fixture.library.play();fixture.player.tick();fixture.backend.position=65.432
   window=PlayerWindow(fixture.player,fixture.library,lambda _:None);window.root.update();helper=Mock()
   def start(_):
    saved=json.loads(fixture.player.file.read_text());self.assertEqual(saved['tracks'][fixture.player.active]['position'],65.432);return helper
   with patch('window.updater.install',side_effect=start),patch.object(window,'close',return_value=False),patch('window.messagebox.showerror'):
    window.update_busy=True;window.update_event(('update_downloaded',fixture.root/'Setup.exe'))
    helper.terminate.assert_called_once();self.assertFalse(window.update_busy);self.assertTrue(window.root.winfo_exists())
  finally:
   if window:window.close()
   fixture.tearDown()
 def test_column_dividers_are_locked_but_headings_still_sort(self):
  fixture=test_player.Tests();fixture.setUp();window=None
  try:
   window=PlayerWindow(fixture.player,fixture.library,lambda _:None);window.root.update()
   y=12;separator=next(x for x in range(window.tree.winfo_width()) if window.tree.identify_region(x,y)=='separator')
   before=[window.tree.column(c,'width') for c in ('name','resume','duration')]
   window.tree.event_generate('<ButtonPress-1>',x=separator,y=y)
   window.tree.event_generate('<B1-Motion>',x=separator+80,y=y)
   window.tree.event_generate('<ButtonRelease-1>',x=separator+80,y=y);window.root.update()
   self.assertEqual([window.tree.column(c,'width') for c in ('name','resume','duration')],before)
   window.sort_by('name');window.sort_by('name');self.assertTrue(fixture.library.descending)
  finally:
   if window:window.close()
   fixture.tearDown()
 def test_idle_refresh_does_not_rebuild_list_or_canvas_items(self):
  from unittest.mock import patch
  fixture=test_player.Tests();fixture.setUp();window=None
  try:
   window=PlayerWindow(fixture.player,fixture.library,lambda _:None);window.root.update();window.refresh();window.root.update()
   items=window.seek.find_all()
   with patch.object(window.tree,'move',wraps=window.tree.move) as move,patch.object(window.tree,'item',wraps=window.tree.item) as item,patch.object(window.seek,'coords',wraps=window.seek.coords) as coords:
    window.refresh();window.refresh()
    self.assertFalse(move.called);self.assertFalse(coords.called)
    self.assertFalse(any(call.kwargs for call in item.call_args_list),item.call_args_list)
   self.assertEqual(window.seek.find_all(),items)
   window.speed_button.invoke();window.refresh();self.assertEqual(window.speed.get(),'1.5')
   fixture.player.command({'op':'speed_cycle'});window.refresh();self.assertEqual(window.speed.get(),'2')
   window.speed_button.invoke();window.refresh();self.assertEqual(window.speed.get(),'0.5')
  finally:
   if window:window.close()
   fixture.tearDown()
 def test_favorites_queue_and_listening_tools_keep_current_place(self):
  fixture=test_player.Tests();fixture.setUp();window=None
  try:
   fixture.library.play();fixture.player.tick();fixture.backend.position=42.875
   window=PlayerWindow(fixture.player,fixture.library,lambda _:None);window.root.update()
   ident=fixture.player.active;window.favorite_current();window.navigate('favorites');window.root.update()
   self.assertEqual(list(window.tree.get_children()),[ident])
   window.show_queue();window.queue_tree.selection_set(ident);window.queue_action('play')
   self.assertEqual(fixture.backend.position,42.875)
   window.listening_tools();window.root.update();fixture.player.command({'op':'loop_a'})
   fixture.backend.position=55;fixture.player.command({'op':'loop_b'});window.refresh()
   self.assertIn('0:42',window.loop_label.cget('text'))
   fixture.player.command({'op':'sleep_timer','mode':'end'});window.refresh()
   self.assertIn('end of this recording',window.sleep_label.cget('text'))
   self.assertIsNone(fixture.player.snapshot()['loopB']);self.assertEqual(fixture.backend.position,55)
  finally:
   if window:window.close()
   fixture.tearDown()
 def test_settings_audio_enhancement_buttons_open_and_respond(self):
  fixture=test_player.Tests();fixture.setUp();window=None
  try:
   window=PlayerWindow(fixture.player,fixture.library,lambda _:None)
   ident=fixture.player.tracks[0]['id']
   window.tree.selection_set(ident);window.tree.focus(ident);window.select();window.root.update()
   def descendants(widget):
    for child in widget.winfo_children():
     yield child
     yield from descendants(child)
   window.settings();window.root.update()
   settings=next(child for child in window.root.winfo_children() if child.winfo_class()=='Toplevel')
   audio_entry=next(w for w in descendants(settings) if isinstance(w,window_module.SoftButton) and w.cget('text')=='Audio enhancements…')
   audio_entry.invoke();window.root.update()
   audio=next(child for child in window.root.winfo_children() if child.winfo_class()=='Toplevel')
   self.assertEqual(audio.title(),'Audio enhancements')
   preset=next(w for w in descendants(audio) if isinstance(w,window_module.SoftButton) and w.cget('text')=='Strong speech')
   preset.invoke();window.root.update()
   self.assertEqual({name:var.get() for name,var in window.audio_controls['values'].items()},{'bass':-3.0,'body':-1.0,'clarity':5.0,'treble':2.0})
   entry=next(w for w in descendants(audio) if isinstance(w,window_module.SoftButton) and w.cget('text')=='Enhance current shiur…')
   entry.invoke();window.root.update()
   speech=next(child for child in window.root.winfo_children() if child.winfo_class()=='Toplevel' and child.title()=='Offline speech enhancement')
   original=next(w for w in descendants(speech) if isinstance(w,window_module.SoftButton) and w.cget('text')=='Use original audio')
   original.invoke();window.root.update()
   self.assertEqual(fixture.player.saved['speechEnhancementEnabled'],False)
   self.assertEqual(next(w for w in descendants(speech) if isinstance(w,window_module.tk.Label) and w.cget('text')=='Original audio is active.').cget('text'),'Original audio is active.')
  finally:
   if window:window.close()
   fixture.tearDown()
if __name__=='__main__':unittest.main(verbosity=2)
