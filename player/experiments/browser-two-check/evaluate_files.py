"""Rescan the same research sources in real Chromium; not an independent dataset."""
import argparse,functools,http.server,json,pathlib,shutil,subprocess,tempfile,threading
from playwright.sync_api import sync_playwright
from test_browser import Server,ROOT

def main():
 p=argparse.ArgumentParser();p.add_argument('--assets',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);args=p.parse_args()
 items=[(f,f.parent.name.replace('_wav','')) for f in sorted((args.assets/'data').rglob('*.wav'))]+[(args.assets/'shiur_freifeld.mp3','shiur')]+[(f,'constructed_music' if 'music' in f.stem else 'non_speech') for f in sorted((args.assets/'stress').glob('*.wav'))]
 with tempfile.TemporaryDirectory(prefix='inside-browser-files-') as tmp:
  Server.fixtures=pathlib.Path(tmp);server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Server,directory=str(ROOT)));threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
  try:
   with sync_playwright() as play:
    browser=play.chromium.launch(headless=True);page=browser.new_page();outside=[];errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    def route(req):
     if req.request.url.startswith(base+'/'):req.continue_()
     else:outside.append(req.request.url);req.abort()
    page.route('**/*',route);page.goto(base+'/test.html');results=[]
    for n,(source,label) in enumerate(items):
     duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(source)]));repeated=duration<300
     target=pathlib.Path(tmp)/('recording.wav' if repeated else 'recording'+source.suffix)
     if repeated:subprocess.run(['ffmpeg','-nostdin','-v','error','-stream_loop','-1','-i',str(source),'-t','300','-ac','1','-ar','16000','-c:a','pcm_s16le','-y',str(target)],timeout=30,check=True);duration=300
     else:shutil.copy2(source,target)
     result=page.evaluate('''async ({url,base,duration})=>{try{return await BrowserTwoCheck.scan(url,{assetBase:base+'/player/plugin/',duration,budgetMs:5000});}catch(e){return {error:e.message};}}''',dict(url=base+'/audio/'+target.name,base=base,duration=duration))
     if 'error' not in result:assert len(result['checks'])==2 and result['fullFileApproved'] is False
     results.append(dict(source=source.name,label=label,repeated_to_five_minutes=repeated,**result));target.unlink()
     if (n+1)%10==0 or n+1==len(items):print(f'Tested {n+1}/{len(items)} browser files',flush=True)
    assert not outside,outside;assert not errors,errors;browser.close()
   summary={label:{d:sum(f['label']==label and f.get('decision','error')==d for f in results) for d in sorted({f.get('decision','error') for f in results})} for label in sorted({f['label'] for f in results})}
   args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(dict(summary=summary,outside_requests=outside,files=results),indent=2)+'\n');print(json.dumps(summary,indent=2))
  finally:server.shutdown();server.server_close()
if __name__=='__main__':main()
