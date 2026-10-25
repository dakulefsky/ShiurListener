"""Native Windows folder chooser; no PowerShell or browser dependency."""
import ctypes

def choose_recordings_folder(language='en'):
 from ctypes import wintypes as w
 shell=ctypes.WinDLL('shell32',use_last_error=True);ole=ctypes.WinDLL('ole32',use_last_error=True)
 class BROWSEINFO(ctypes.Structure):
  _fields_=[('owner',w.HWND),('root',w.LPVOID),('display',w.LPWSTR),('title',w.LPCWSTR),('flags',w.UINT),('callback',w.LPVOID),('parameter',w.LPARAM),('image',ctypes.c_int)]
 ole.CoInitializeEx.argtypes=[w.LPVOID,w.DWORD];ole.CoInitializeEx.restype=ctypes.c_long
 ole.CoTaskMemFree.argtypes=[w.LPVOID];ole.CoTaskMemFree.restype=None
 ole.CoUninitialize.argtypes=[];ole.CoUninitialize.restype=None
 shell.SHBrowseForFolderW.argtypes=[ctypes.POINTER(BROWSEINFO)];shell.SHBrowseForFolderW.restype=w.LPVOID
 shell.SHGetPathFromIDListEx.argtypes=[w.LPVOID,w.LPWSTR,w.DWORD,w.DWORD];shell.SHGetPathFromIDListEx.restype=w.BOOL
 initialized=ole.CoInitializeEx(None,2)
 if initialized not in (0,1):raise RuntimeError('Could not open the Windows folder chooser.')
 pidl=None
 try:
  display=ctypes.create_unicode_buffer(32768);dialog=BROWSEINFO(None,None,ctypes.cast(display,w.LPWSTR),'Choose recordings folder',0x0241,None,0,0)
  pidl=shell.SHBrowseForFolderW(ctypes.byref(dialog))
  if not pidl:return ''
  path=ctypes.create_unicode_buffer(32768)
  if not shell.SHGetPathFromIDListEx(pidl,path,len(path),0):raise RuntimeError('Choose an existing filesystem folder.')
  return path.value
 finally:
  if pidl:ole.CoTaskMemFree(pidl)
  ole.CoUninitialize()
