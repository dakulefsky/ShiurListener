import pathlib,struct,sys,unittest,zlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'app'))
from rendering import rounded_png,icon_png
def pixels(data):
 assert data[:8]==b'\x89PNG\r\n\x1a\n'
 offset=8;compressed=b''
 while offset<len(data):
  size=struct.unpack_from('!I',data,offset)[0];kind=data[offset+4:offset+8];payload=data[offset+8:offset+8+size]
  if kind==b'IHDR':width,height=struct.unpack_from('!2I',payload)
  if kind==b'IDAT':compressed+=payload
  offset+=size+12
 raw=zlib.decompress(compressed);stride=width*4+1
 return width,height,[raw[y*stride+1:(y+1)*stride] for y in range(height)]
class Tests(unittest.TestCase):
 def test_rounded_edges_are_partly_transparent_with_solid_interior(self):
  width,height,rows=pixels(rounded_png(120,40,16,'#6558D3'))
  self.assertEqual((width,height),(120,40))
  self.assertEqual(rows[0][3],0)
  self.assertEqual(tuple(rows[20][60*4:60*4+4]),(101,88,211,255))
  self.assertTrue(any(0<a<255 for row in rows for a in row[3::4]))
  self.assertEqual(rows,rows[::-1])
 def test_icons_have_antialiased_edges_and_disabled_color(self):
  for name in ('Play','Pause','Prev','Next'):
   width,height,rows=pixels(icon_png(name,'#A6A1B1',33))
   self.assertEqual((width,height),(33,33))
   self.assertTrue(any(a==255 for row in rows for a in row[3::4]))
   self.assertTrue(any(0<a<255 for row in rows for a in row[3::4]))
   self.assertEqual(tuple(rows[16][:3]),(166,161,177))
 def test_surfaces_handle_tiny_sizes_and_cached_repaints(self):
  for width,height in ((1,1),(2,3),(300,140)):
   data=rounded_png(width,height,18,'#FFFFFF','#6558D3')
   self.assertEqual(pixels(data)[:2],(width,height))
   self.assertIs(data,rounded_png(width,height,18,'#FFFFFF','#6558D3'))
if __name__=='__main__':unittest.main()

