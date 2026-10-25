"""Win32 hotkey registration/message dispatch mocked on Linux; not a real Windows desktop test."""
import importlib.util,pathlib,tempfile,threading,unittest,unittest.mock,ctypes
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('hotkeys',ROOT/'companion/hotkeys.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class Function:
 def __init__(self,fn):self.fn=fn
 def __call__(self,*args):return self.fn(*args)
class TestHotkeys(unittest.TestCase):
 def test_bindings(self):
  defaults=module.bindings({});self.assertEqual(len(defaults),12);self.assertEqual(defaults[0][3],'CTRL+ALT+SHIFT+P')
  self.assertEqual(len(module.bindings({'toggle':None})),11)
  with self.assertRaises(ValueError):module.bindings({'toggle':{'modifiers':[],'key':'P'}})
  with self.assertRaises(ValueError):module.bindings({'back':{'modifiers':['CTRL','ALT','SHIFT'],'key':'P'}})
 def test_windows_message_loop(self):
  from ctypes import wintypes
  with tempfile.TemporaryDirectory() as tmp:
   class Player:
    data_dir=pathlib.Path(tmp);lock=threading.RLock();hotkey_status=[];error=''
    def __init__(self):self.commands=[]
    def command(self,action):self.commands.append(action)
   player=Player();registered=[];released=[];count=0
   def register(window,ident,mods,key):registered.append((ident,mods,key));return key!=ord('P')
   def message(pointer,*args):
    nonlocal count
    count+=1
    if count==1:
     value=ctypes.cast(pointer,ctypes.POINTER(wintypes.MSG)).contents;value.message=0x312;value.wParam=3;return 1
    return 0
   user=type('User',(),{})();user.RegisterHotKey=Function(register);user.UnregisterHotKey=Function(lambda _,ident:released.append(ident) or 1);user.GetMessageW=Function(message);user.PeekMessageW=Function(lambda *args:0)
   kernel=type('Kernel',(),{})();kernel.GetCurrentThreadId=Function(lambda:123)
   with unittest.mock.patch.object(module.ctypes,'WinDLL',side_effect=lambda name,**kwargs:user if name=='user32' else kernel,create=True),unittest.mock.patch.object(module.ctypes,'get_last_error',return_value=1409,create=True):
    hotkeys=module.GlobalHotkeys(player);hotkeys.run()
   self.assertEqual(len(registered),12);self.assertEqual(len(released),11);self.assertTrue(all(mods&0x4000 for _,mods,_ in registered));self.assertFalse(player.hotkey_status[0]['registered']);self.assertIn('1409',player.hotkey_status[0]['error']);self.assertEqual(player.commands,[{'op':'skip','direction':1}]);self.assertTrue((pathlib.Path(tmp)/'hotkeys.json').exists())
if __name__=='__main__':unittest.main(verbosity=2)
