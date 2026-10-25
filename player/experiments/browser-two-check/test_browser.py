"""Actual Chromium range-decode and offline model tests; development fixtures only."""
import argparse,functools,http.server,json,pathlib,subprocess,threading,time
from playwright.sync_api import sync_playwright
ROOT=pathlib.Path(__file__).resolve().parents[3]
class Server(http.server.SimpleHTTPRequestHandler):
 fixtures=None
 audio_origin=None
 def end_headers(self):
  self.send_header('Access-Control-Allow-Origin','*');self.send_header('Access-Control-Expose-Headers','Content-Range, Accept-Ranges, Content-Length, ETag')
  self.send_header('Content-Security-Policy',"default-src 'self' "+(self.audio_origin or '')+" data: blob: 'unsafe-inline' 'unsafe-eval' 'wasm-unsafe-eval'; base-uri 'self'")
  super().end_headers()
 def log_message(self,*args):pass
 def do_GET(self):
  path=self.path.split('?')[0]
  if path=='/test.html':
   data=b'''<!doctype html><script src="/player/plugin/tf.min.js"></script><script src="/player/plugin/tflite.min.js"></script><script src="/player/plugin/analysis-range-audio.js"></script><script src="/player/plugin/analysis-two-check.js"></script>'''
   self.send_response(200);self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
  if path.startswith('/audio/'):
   file=self.fixtures/path.removeprefix('/audio/')
   if not file.is_file() or file.parent!=self.fixtures:self.send_error(404);return
   size=file.stat().st_size;header=self.headers.get('Range');assert header,'A full audio fetch was attempted'
   low,high=header.removeprefix('bytes=').split('-');start=int(low);end=min(int(high),size-1)
   if start>=size:self.send_error(416);return
   self.send_response(206);self.send_header('Content-Range',f'bytes {start}-{end}/{size}');self.send_header('Content-Length',str(end-start+1));self.send_header('ETag',f'"{size}-{file.stat().st_mtime_ns}"');self.end_headers()
   with file.open('rb') as stream:stream.seek(start);self.wfile.write(stream.read(end-start+1))
   return
  super().do_GET()
def main():
 p=argparse.ArgumentParser();p.add_argument('--fixtures',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);args=p.parse_args();Server.fixtures=args.fixtures.resolve()
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Server,directory=str(ROOT)));threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
 audio=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Server,directory=str(ROOT)));threading.Thread(target=audio.serve_forever,daemon=True).start();audio_base=f'http://127.0.0.1:{audio.server_port}';Server.audio_origin=audio_base
 try:
  with sync_playwright() as play:
   browser=play.chromium.launch(headless=True);page=browser.new_page();outside=[];errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   def route(req):
    if req.request.url.startswith((base+'/',audio_base+'/')):req.continue_()
    else:outside.append(req.request.url);req.abort()
   page.route('**/*',route);page.goto(base+'/test.html');results=[]
   for file in sorted(args.fixtures.iterdir()):
    if file.suffix.lower() not in ['.mp3','.wav']:continue
    duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(file)]))
    result=page.evaluate('''async ({url,base,duration})=>{try{return await BrowserTwoCheck.scan(url,{assetBase:base+'/player/plugin/',duration,budgetMs:5000});}catch(e){return {error:e.message,name:e.name}}}''',dict(url=audio_base+'/audio/'+file.name,base=base,duration=duration))
    assert 'error' not in result,result
    assert len(result['checks'])==2 and result['fullFileApproved'] is False,result
    assert result['sourceBytesRead']<4*1024*1024,result
    assert result['wallMs']<5000,result
    results.append(dict(file=file.name,**result));print(file.name,json.dumps(result),flush=True)
   assert not outside,outside;assert not errors,errors;browser.close()
  args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(dict(cross_origin_audio=True,local_csp=True,outside_requests=outside,results=results),indent=2)+'\n')
 finally:server.shutdown();server.server_close();audio.shutdown();audio.server_close();Server.audio_origin=None
if __name__=='__main__':main()
