"""Shortcut configuration and native registration/dispatch lifecycle, with Win32 mocked."""
import ctypes
import pathlib
import sys
import unittest
from unittest.mock import Mock,patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'app'))
import hotkeys
import test_player

class Tests(unittest.TestCase):
 def test_defaults_are_unique_and_conflicting_config_is_rejected(self):
  items=hotkeys.bindings({});self.assertEqual(len(items),len(hotkeys.DEFAULTS))
  self.assertEqual(len({(mods,key) for name,mods,key,label,action in items}),len(items))
  with self.assertRaises(ValueError):hotkeys.bindings({'toggle':{'modifiers':['CTRL','ALT','SHIFT'],'key':'LEFT'}})
  self.assertEqual(len(hotkeys.bindings({'toggle':None})),len(items)-1)

 def test_bluetooth_media_keys_are_valid_and_map_to_play_pause_and_skip(self):
  items=hotkeys.bindings(hotkeys.default_config())
  by_name={name:(mods,key,label,action) for name,mods,key,label,action in items}
  self.assertEqual(by_name['media_toggle'][0],0)
  self.assertEqual(by_name['media_toggle'][1],0xB3)
  self.assertEqual(by_name['media_toggle'][3],{'op':'toggle'})
  self.assertEqual(by_name['media_back'][3],{'op':'skip','direction':-1})
  self.assertEqual(by_name['media_forward'][3],{'op':'skip','direction':1})
  with self.assertRaisesRegex(ValueError,'Ctrl, Alt or Win'):
   hotkeys.bindings({'toggle':{'modifiers':[],'key':'P'}})
  with self.assertRaisesRegex(ValueError,'Duplicate'):
   hotkeys.bindings({'media_toggle':{'modifiers':[],'key':'MEDIA_PLAY_PAUSE'},'media_back':{'modifiers':[],'key':'MEDIA_PLAY_PAUSE'}})

 def test_custom_shortcuts_save_reload_and_invalid_changes_preserve_file(self):
  fixture=test_player.Tests();fixture.setUp()
  try:
   path=fixture.player.data_dir/'hotkeys.json'
   config=hotkeys.default_config();config['toggle']={'modifiers':['CTRL'],'key':'F8'};config['stop']=None
   hotkeys.save_config(path,config)
   self.assertEqual(hotkeys.load_config(path),config)
   before=path.read_bytes();config['forward']=config['toggle']
   with self.assertRaisesRegex(ValueError,'Duplicate'):hotkeys.save_config(path,config)
   self.assertEqual(path.read_bytes(),before)
   with self.assertRaises(ValueError):hotkeys.bindings({'toggle':{'modifiers':[{}],'key':'P'}})
  finally:fixture.tearDown()

 def test_registration_conflict_and_dispatch_without_console(self):
  fixture=test_player.Tests();fixture.setUp()
  try:
   user=Mock();kernel=Mock();kernel.GetCurrentThreadId.return_value=77
   user.RegisterHotKey.side_effect=lambda hwnd,index,mods,key:index!=2
   messages=[1,0]
   def get_message(pointer,*args):
    pointer._obj.message=0x0312;pointer._obj.wParam=1;return messages.pop(0)
   user.GetMessageW.side_effect=get_message
   keys=hotkeys.GlobalHotkeys(fixture.player)
   with patch.object(ctypes,'WinDLL',side_effect=lambda name,**kw:user if name=='user32' else kernel,create=True),patch.object(ctypes,'get_last_error',return_value=1409,create=True),patch.object(sys,'stdout',None):keys.run()
   self.assertTrue(keys.ready.is_set())
   self.assertEqual(len(fixture.player.hotkey_status),len(hotkeys.DEFAULTS))
   self.assertFalse(fixture.player.hotkey_status[1]['registered'])
   self.assertEqual(user.UnregisterHotKey.call_count,len(hotkeys.DEFAULTS)-1)
   self.assertTrue(fixture.player.pending['autoplay'])
  finally:fixture.tearDown()

