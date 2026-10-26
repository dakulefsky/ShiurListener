"""Antialiased UI assets generated at their display size; no extra runtime dependency."""
import functools,math,struct,zlib
def png(width,height,rows):
 def chunk(kind,data):return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
 return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',width,height,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(b'\0'+row for row in rows)))+chunk(b'IEND',b'')
def rgb(color):return tuple(int(color[i:i+2],16) for i in (1,3,5))
@functools.lru_cache(maxsize=96)
def rounded_png(width,height,radius,fill,border=''):
 width=max(1,int(width));height=max(1,int(height));radius=min(radius,width/2,height/2)
 foreground=rgb(fill);edge=rgb(border or fill);rows=[]
 def coverage(x,y,inset=0):
  r=max(0,radius-inset);left=top=inset;right=width-inset;bottom=height-inset
  if right<=left or bottom<=top:return 0.
  dx=max(left+r-x,0,x-(right-r));dy=max(top+r-y,0,y-(bottom-r))
  return max(0.,min(1.,r+.5-math.hypot(dx,dy)))
 for y in range(height):
  if radius<=y+.5<=height-radius:
   row=bytes((*foreground,255))*width
   if border:
    row=bytes((*edge,255))+row[4:-4]+bytes((*edge,255)) if width>1 else bytes((*edge,255))
   rows.append(row);continue
  def pixel(x):
   a=coverage(x+.5,y+.5);inside=coverage(x+.5,y+.5,1) if border else a
   mix=min(1.,inside/a) if a else 0.
   color=tuple(round(edge[i]*(1-mix)+foreground[i]*mix) for i in range(3))
   return bytes((*color,round(a*255)))
  corners=min(math.ceil(radius),width//2)
  left=b''.join(pixel(x) for x in range(corners))
  middle=pixel(width//2)*(width-2*corners)
  right=b''.join(pixel(x) for x in range(width-corners,width))
  rows.append(left+middle+right)
 return png(width,height,rows)
@functools.lru_cache(maxsize=64)
def icon_png(name,color,size=22):
 ink=rgb(color);rows=[]
 def inside(x,y):
  x=(x-size/2)*22/size;y=(y-size/2)*22/size
  if name=='Close':return abs(x-y)<1.2 and abs(x)<=6 and abs(y)<=6 or abs(x+y)<1.2 and abs(x)<=6 and abs(y)<=6
  if name=='Collapse':return abs(y)<1.1 and abs(x)<=6
  if name=='Expand':return (abs(x+y)<1.1 and abs(x)<=6 and abs(y)<=6) or (abs(y+6)<1.1 and -3<=x<=6) or (abs(x-6)<1.1 and -6<=y<=3)
  if name=='Pause':return -7<=y<=7 and (-5.5<=x<=-2.5 or 2.5<=x<=5.5)
  if name=='Prev':x=-x
  triangle=-5<=x<=7 and abs(y)<=(7-x)*2/3
  return triangle or (name in ('Prev','Next') and 8<=x<=10 and -8<=y<=8)
 for y in range(size):
  row=bytearray()
  for x in range(size):
   count=sum(inside(x+(sx+.5)/4,y+(sy+.5)/4) for sx in range(4) for sy in range(4))
   row.extend((*ink,round(count*255/16)))
  rows.append(bytes(row))
 return png(size,size,rows)

