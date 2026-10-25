"""Paired baseline/candidate checks on reused sources and synthetic volume/DC variants.
Requires the baseline Git commit and external research fixtures; no audio is redistributed.
"""
import sys,pathlib,tempfile,threading,functools,http.server,subprocess,json,argparse
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from test_browser import Server,ROOT
from playwright.sync_api import sync_playwright
parser=argparse.ArgumentParser();parser.add_argument('--assets',type=pathlib.Path,required=True);parser.add_argument('--output',type=pathlib.Path,required=True);parser.add_argument('--baseline-ref',default='3ac22b7');parser.add_argument('--levels',default='1,0.01');args=parser.parse_args();assets=args.assets
levels=[float(v) for v in args.levels.split(',')];assert levels and all(0<v<=1 for v in levels)
variants=[(v,dc) for v in levels for dc in ([0] if v==1 else [0,.05])]
items=[(f,label) for label in ('speech','music') for f in sorted((assets/'data'/f'{label}_wav').glob('*.wav'))]
with tempfile.TemporaryDirectory() as tmp:
 Server.fixtures=pathlib.Path(tmp);server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Server,directory=str(ROOT)));threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
 try:
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True);page=browser.new_page();outside=[]
   def local_only(route):
    if route.request.url.startswith(base+'/'):route.continue_()
    else:outside.append(route.request.url);route.abort()
   page.route('**/*',local_only);page.goto(base+'/test.html')
   previous=subprocess.check_output(['git','show',args.baseline_ref+':player/plugin/analysis-two-check.js'],text=True,cwd=ROOT)
   page.evaluate('(code)=>{window.newScan=BrowserTwoCheck.scan;eval(code);window.oldScan=BrowserTwoCheck.scan;}',previous)
   results=[]
   for source,label in items:
    for volume,offset in variants:
     target=pathlib.Path(tmp)/'recording.wav';subprocess.run(['ffmpeg','-nostdin','-v','error','-stream_loop','-1','-i',str(source),'-t','300','-ac','1','-ar','16000','-af',f'volume={volume},dcshift=shift={offset}','-c:a','pcm_s16le','-y',str(target)],check=True)
     row={'file':source.name,'label':label,'volume':volume,'offset':offset}
     for mode in [False,True]:
      page.evaluate('(v)=>window.normalized=v',mode)
      row['normalized' if mode else 'baseline']=page.evaluate('''async base=>{try{return await (window.normalized?window.newScan:window.oldScan)(base+'/audio/recording.wav',{assetBase:base+'/player/plugin/',duration:300});}catch(e){return {error:e.message}}}''',base)
     for mode in ['baseline','normalized']:
      assert len(row[mode]['checks'])==2 and row[mode]['fullFileApproved'] is False,row
     assert [c['startSeconds'] for c in row['baseline']['checks']]==[c['startSeconds'] for c in row['normalized']['checks']]
     assert row['baseline']['sourceBytesRead']==row['normalized']['sourceBytesRead']
     results.append(row)
    print('Tested',source.name,flush=True)
   assert not outside,outside
   browser.close();args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(results,indent=2)+'\n')
   print(json.dumps({label:{mode:{decision:sum(r['label']==label and r[mode].get('decision')==decision for r in results) for decision in ['provisional_speech','music_detected_in_samples','uncertain']} for mode in ['baseline','normalized']} for label in ['speech','music']},indent=2))
 finally:server.shutdown();server.server_close()
