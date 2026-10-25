"""Exercise the real desktop toolkit, including persistence across a new window."""
import os,pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'app'))
from window import PlayerWindow
from engine import Player
from controller import LibraryController
import test_player
@unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform=='win32','Needs a desktop display')
class Tests(unittest.TestCase):
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
   fixture.library.selected=fixture.player.tracks[0]['id'];window.assign_collection('My recordings')
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
   window=PlayerWindow(fixture.player,fixture.library,lambda _:None);window.root.geometry('1120x740');window.root.update()
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
   self.assertEqual(restored.saved['windowSize'],[1120,740]);self.assertTrue(library.descending)
   window=PlayerWindow(restored,library,lambda _:None);window.root.update()
   self.assertEqual([window.root.winfo_width(),window.root.winfo_height()],[1120,740])
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
   fixture.player.command({'op':'speed_cycle'});window.refresh();self.assertEqual(window.speed.get(),'1.5')
  finally:
   if window:window.close()
   fixture.tearDown()
if __name__=='__main__':unittest.main(verbosity=2)
