"""Check actual GDI+ alpha compositing on a Windows memory DC."""
import ctypes,pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'app'))
from native_rendering import SmoothDrawing
from rendering import rounded_png
@unittest.skipUnless(sys.platform=='win32','Needs Windows GDI+')
class Tests(unittest.TestCase):
 def test_soft_edges_are_composited_and_resources_close(self):
  gdi=ctypes.WinDLL('gdi32');user=ctypes.WinDLL('user32')
  user.GetDC.argtypes=[ctypes.c_void_p];user.GetDC.restype=ctypes.c_void_p
  user.ReleaseDC.argtypes=[ctypes.c_void_p,ctypes.c_void_p]
  for name,args,result in [('CreateCompatibleDC',[ctypes.c_void_p],ctypes.c_void_p),('CreateCompatibleBitmap',[ctypes.c_void_p,ctypes.c_int,ctypes.c_int],ctypes.c_void_p),('SelectObject',[ctypes.c_void_p,ctypes.c_void_p],ctypes.c_void_p),('DeleteObject',[ctypes.c_void_p],ctypes.c_int),('DeleteDC',[ctypes.c_void_p],ctypes.c_int),('PatBlt',[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_uint32],ctypes.c_int),('GetPixel',[ctypes.c_void_p,ctypes.c_int,ctypes.c_int],ctypes.c_uint32)]:
   fn=getattr(gdi,name);fn.argtypes=args;fn.restype=result
  screen=user.GetDC(None);dc=gdi.CreateCompatibleDC(screen);bitmap=gdi.CreateCompatibleBitmap(screen,40,40);previous=gdi.SelectObject(dc,bitmap);drawing=SmoothDrawing()
  try:
   self.assertTrue(drawing.ready)
   gdi.PatBlt(dc,0,0,40,40,0x00FF0062);gdi.GdiFlush()
   self.assertTrue(drawing.draw(dc,0,0,40,40,rounded_png(40,40,16,'#000000')))
   self.assertEqual(gdi.GetPixel(dc,20,20),0)
   self.assertEqual(gdi.GetPixel(dc,0,0),0xffffff)
   colors=[gdi.GetPixel(dc,x,y)&255 for y in range(16) for x in range(16)]
   self.assertTrue(any(0<value<255 for value in colors))
  finally:
   drawing.close();self.assertFalse(drawing.ready)
   gdi.SelectObject(dc,previous);gdi.DeleteObject(bitmap);gdi.DeleteDC(dc);user.ReleaseDC(None,screen)

