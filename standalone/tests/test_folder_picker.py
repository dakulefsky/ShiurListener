import ctypes,pathlib,sys,unittest,unittest.mock
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'app'))
from folder_picker import choose_recordings_folder
class Function:
 def __init__(self,fn):self.fn=fn
 def __call__(self,*args):return self.fn(*args)
class Tests(unittest.TestCase):
 def test_selected_and_cancelled_folder_release_com_resources(self):
  for selected in [True,False]:
   calls=[]
   class Library:
    def __getattr__(self,name):
     def run(*args):
      calls.append(name)
      if name=='CoInitializeEx':return 0
      if name=='SHBrowseForFolderW':return 123 if selected else None
      if name=='SHGetPathFromIDListEx':args[1].value='C:\\Recordings';return 1
     value=Function(run);setattr(self,name,value);return value
   with unittest.mock.patch.object(ctypes,'WinDLL',return_value=Library(),create=True):result=choose_recordings_folder()
   self.assertEqual(result,'C:\\Recordings' if selected else '')
   self.assertEqual(calls[-1],'CoUninitialize');self.assertEqual('CoTaskMemFree' in calls,selected)
if __name__=='__main__':unittest.main(verbosity=2)
