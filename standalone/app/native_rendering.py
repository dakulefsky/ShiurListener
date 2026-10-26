"""GDI+ compositing for antialiased mini-player PNG assets; GDI remains the fallback."""
import ctypes,struct,zlib
from collections import OrderedDict
class SmoothDrawing:
 def __init__(self):
  self.ready=False;self.images=OrderedDict();self.token=ctypes.c_size_t()
  try:
   self.dll=ctypes.WinDLL('gdiplus',use_last_error=True)
   class Startup(ctypes.Structure):
    _fields_=[('version',ctypes.c_uint32),('debug',ctypes.c_void_p),('background',ctypes.c_int),('codecs',ctypes.c_int)]
   self.start=self.bind('GdiplusStartup',ctypes.c_int,[ctypes.POINTER(ctypes.c_size_t),ctypes.POINTER(Startup),ctypes.c_void_p])
   self.shutdown=self.bind('GdiplusShutdown',None,[ctypes.c_size_t])
   self.create=self.bind('GdipCreateBitmapFromScan0',ctypes.c_int,[ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_void_p,ctypes.POINTER(ctypes.c_void_p)])
   self.dispose=self.bind('GdipDisposeImage',ctypes.c_int,[ctypes.c_void_p])
   self.graphics=self.bind('GdipCreateFromHDC',ctypes.c_int,[ctypes.c_void_p,ctypes.POINTER(ctypes.c_void_p)])
   self.delete=self.bind('GdipDeleteGraphics',ctypes.c_int,[ctypes.c_void_p])
   self.draw_image=self.bind('GdipDrawImageRectI',ctypes.c_int,[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int])
   self.ready=self.start(ctypes.byref(self.token),ctypes.byref(Startup(1,None,0,0)),None)==0
  except (OSError,AttributeError,KeyError):pass
 def bind(self,name,result,args):
  fn=getattr(self.dll,name);fn.restype=result;fn.argtypes=args;return fn
 def draw(self,dc,x,y,width,height,data):
  if not self.ready:return False
  image=self.images.get(data)
  if image is None:
   position=8;compressed=b''
   while position<len(data):
    size=struct.unpack_from('!I',data,position)[0];kind=data[position+4:position+8];payload=data[position+8:position+8+size]
    if kind==b'IHDR':w,h=struct.unpack_from('!2I',payload)
    elif kind==b'IDAT':compressed+=payload
    position+=size+12
   raw=zlib.decompress(compressed);pixels=bytearray()
   for row in range(h):
    offset=row*(w*4+1);assert raw[offset]==0
    for start in range(offset+1,offset+1+w*4,4):
     r,g,b,a=raw[start:start+4];pixels.extend((b,g,r,a))
   buffer=ctypes.create_string_buffer(bytes(pixels));bitmap=ctypes.c_void_p()
   if self.create(w,h,w*4,0x26200A,buffer,ctypes.byref(bitmap))!=0:return False
   image=(bitmap,buffer);self.images[data]=image
   if len(self.images)>64:
    _,old=self.images.popitem(last=False);self.dispose(old[0])
  else:self.images.move_to_end(data)
  graphics=ctypes.c_void_p()
  if self.graphics(dc,ctypes.byref(graphics))!=0:return False
  try:return self.draw_image(graphics,image[0],x,y,width,height)==0
  finally:self.delete(graphics)
 def close(self):
  if self.ready:
   for image,_ in self.images.values():self.dispose(image)
   self.images.clear();self.shutdown(self.token);self.ready=False

