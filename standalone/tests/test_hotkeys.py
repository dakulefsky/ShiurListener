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
