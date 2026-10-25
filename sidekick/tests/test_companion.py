"""Companion service and plugin integration tests. Uses a fake decoder; VLC/OS audio needs desktop testing."""
import importlib.util,json,pathlib,tempfile,threading,time,unittest,urllib.request,urllib.error,functools,http.server,contextlib
from playwright.sync_api import sync_playwright,expect
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('companion',ROOT/'companion/companion.py');companion=importlib.util.module_from_spec(spec);spec.loader.exec_module(companion)
class FakeVLC:
 def __init__(self):self.position=0;self.status='stopped';self.rate=1;self.level=1;self.path=None
 def load(self,path):self.path=path;self.position=0;self.status='stopped'
 def play(self):self.status='playing'
 def pause(self):self.status='paused'
 def stop(self):self.status='stopped'
 def seek(self,value):self.position=value
 def speed(self,value):self.rate=value
 def volume(self,value):self.level=value
 def state(self):return {'position':self.position,'duration':120,'status':self.status}
 def close(self):pass
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.audio=self.root/'audio';self.audio.mkdir();(self.audio/'First.wav').write_bytes(b'fake');(self.audio/'Second.wav').write_bytes(b'fake');(self.audio/'ignore.txt').write_text('ignore');outside=self.root/'outside.wav';outside.write_bytes(b'fake');(self.audio/'escape.wav').symlink_to(outside)
  self.backend=FakeVLC();self.player=companion.Player(self.audio,self.root/'data',self.backend);self.server=companion.Server(('127.0.0.1',0),self.player,'test-pairing-code');threading.Thread(target=self.server.serve_forever,daemon=True).start();self.url=f'http://127.0.0.1:{self.server.server_port}'
 def tearDown(self):self.server.shutdown();self.server.server_close();self.tmp.cleanup()
 def request(self,path,body=None,token='test-pairing-code',origin=None):
  headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'}
  if origin:headers['Origin']=origin
  req=urllib.request.Request(self.url+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)
  try:
   with urllib.request.urlopen(req,timeout=5) as response:return response.status,json.load(response)
  except urllib.error.HTTPError as e:return e.code,json.load(e)
 def test_bundled_vlc_discovery(self):
  import unittest.mock,os
  bundled=self.root/'app/runtime/vlc';bundled.mkdir(parents=True);(bundled/'libvlc.dll').write_bytes(b'fake')
  class Function:
   def __call__(self,*args):return 1
  class Library:
   def __getattr__(self,key):
    value=Function();setattr(self,key,value);return value
  with unittest.mock.patch.object(companion.sys,'platform','win32'),unittest.mock.patch.object(companion,'__file__',str(self.root/'app/companion.py')),unittest.mock.patch.object(companion.os,'add_dll_directory',create=True) as add,unittest.mock.patch.object(companion.ctypes,'CDLL',return_value=Library()) as load,unittest.mock.patch.dict(os.environ,{}):
   backend=companion.VLC();load.assert_called_once_with(str(bundled/'libvlc.dll'));add.assert_called_once_with(str(bundled));self.assertEqual(os.environ['VLC_PLUGIN_PATH'],str(bundled/'plugins'));backend.close()
 def test_service(self):
  self.assertEqual(len(self.player.tracks),2)
  self.assertEqual(self.request('/v1/state',token='wrong')[0],403)
  self.assertEqual(self.request('/v1/state',origin='https://example.org')[0],403)
  self.assertEqual(self.request('/v1/state',origin='null')[0],403)
  ids=[t['id'] for t in self.player.tracks]
  self.assertEqual(self.request('/v1/command',{'op':'load','id':'../../outside.wav','queue':[]})[0],400)
  self.assertEqual(self.request('/v1/command',{'op':'load','id':ids[0],'queue':ids,'position':42})[0],200)
  self.player.tick();self.assertEqual(self.backend.position,42);self.assertEqual(self.backend.status,'paused')
  self.request('/v1/command',{'op':'play'});self.assertEqual(self.backend.status,'playing')
  self.request('/v1/command',{'op':'speed','value':1.5});self.assertEqual(self.backend.rate,1.5)
  self.request('/v1/command',{'op':'volume','value':.4});self.assertEqual(self.backend.level,.4)
  self.assertEqual(self.request('/v1/command',{'op':'volume','value':9})[0],400)
  self.request('/v1/command',{'op':'autonext','value':True});self.player.tick();self.backend.position=120;self.backend.status='ended';self.player.tick();self.player.tick()
  self.assertEqual(self.player.saved['currentId'],ids[1]);self.assertEqual(self.backend.status,'playing')
  self.backend.position=33;self.player.tick();self.player.persist()
  restored=companion.Player(self.audio,self.root/'data',FakeVLC());self.assertEqual(restored.snapshot()['position'],33);self.assertEqual(restored.snapshot()['status'],'paused')
  self.request('/v1/command',{'op':'stop'});self.assertEqual(self.backend.status,'stopped')
  # The HTTP API exposes IDs and relative labels, never full disk paths or file downloads.
  self.assertNotIn(str(self.audio),json.dumps(self.request('/v1/library')[1]))
  self.assertEqual(self.request('/sample.wav')[0],404)
 def test_folders_skip_and_exact_progress(self):
  ids=[t['id'] for t in self.player.tracks];self.assertEqual(self.player.snapshot()['folders'],[])
  result=self.player.command({'op':'folder_create','name':'My shiurim'});folder=result['folders'][0]['id']
  self.player.command({'op':'folder_add','id':folder,'trackId':ids[0]});self.player.command({'op':'folder_add','id':folder,'trackId':ids[0]});self.assertEqual(self.player.saved['folders'][0]['trackIds'],[ids[0]])
  self.player.command({'op':'folder_rename','id':folder,'name':'Renamed'});self.assertEqual(self.player.saved['folders'][0]['name'],'Renamed')
  self.player.command({'op':'load','id':ids[0],'queue':ids});self.player.tick();self.player.command({'op':'toggle'});self.assertEqual(self.backend.status,'playing')
  for interval in [10,15,60]:
   self.backend.position=20;self.player.command({'op':'skip_interval','value':interval});self.player.command({'op':'skip','direction':1});self.assertEqual(self.backend.position,20+interval)
  self.backend.position=65.432;self.player.command({'op':'toggle'});self.assertEqual(self.backend.status,'paused')
  saved=json.loads(self.player.file.read_text());self.assertEqual(saved['tracks'][ids[0]]['position'],65.432)
  self.player.command({'op':'load','id':ids[1],'queue':ids});self.player.tick();self.backend.position=23.789;self.player.command({'op':'pause'})
  self.assertEqual(self.player.saved['tracks'][ids[0]]['position'],65.432);self.assertEqual(self.player.saved['tracks'][ids[1]]['position'],23.789)
  self.player.saved['tracks'][ids[0]]={'position':119.123,'duration':120};self.player.command({'op':'load','id':ids[0],'queue':ids});self.player.tick();self.assertEqual(self.backend.position,119.123)
  self.player.command({'op':'pause'});restored=companion.Player(self.audio,self.root/'data',FakeVLC());self.assertEqual(restored.saved['tracks'][ids[0]]['position'],119.123);self.assertEqual(restored.saved['folders'][0]['name'],'Renamed')
  self.player.command({'op':'folder_delete','id':folder});self.assertTrue(all(path.exists() for path in self.player.paths.values()));self.assertEqual(self.player.saved['folders'],[])
  self.assertEqual(self.request('/v1/command',{'op':'skip_interval','value':999})[0],400)
 def test_sleep_timer_without_ui(self):
  ids=[t['id'] for t in self.player.tracks];self.player.command({'op':'load','id':ids[0],'queue':ids});self.player.tick();self.player.command({'op':'play'});self.backend.position=47.123
  timer=self.player.command({'op':'sleep_timer','minutes':15});self.assertEqual(timer['sleepMinutes'],15);self.assertGreater(timer['sleepRemaining'],890)
  self.player.sleep_deadline=time.monotonic()-1;self.player.tick();self.assertEqual(self.backend.status,'paused');self.assertEqual(self.player.snapshot()['sleepRemaining'],0);self.assertEqual(json.loads(self.player.file.read_text())['tracks'][ids[0]]['position'],47.123)
  self.player.saved['autoNext']=True;self.player.was_playing=True;self.backend.status='ended';self.player.tick();self.assertEqual(self.player.saved['currentId'],ids[0])
  self.player.command({'op':'sleep_timer','minutes':30});self.player.command({'op':'sleep_timer','minutes':0});self.assertIsNone(self.player.sleep_deadline)
  with self.assertRaises(ValueError):self.player.command({'op':'sleep_timer','minutes':999})
 def test_no_url_or_browser_api_and_revalidate_paths(self):
  for op in ['open_url','browse','execute','shell']:
   self.assertEqual(self.request('/v1/command',{'op':op,'url':'https://example.com'})[0],400)
  self.assertEqual(self.request('/v1/command',{'op':'load','id':'https://example.com/shiur.mp3','queue':[]})[0],400)
  ident=self.player.tracks[0]['id'];original=self.player.paths[ident];original.unlink();original.symlink_to(self.root/'outside.wav')
  self.assertEqual(self.request('/v1/command',{'op':'load','id':ident,'queue':[ident]})[0],400)
  self.assertIsNone(self.backend.path)
 def test_plugin(self):
  web=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT/'plugin')));threading.Thread(target=web.serve_forever,daemon=True).start()
  def bridge(_,request):
   target=request['url'].replace('http://127.0.0.1:18473',self.url)
   req=urllib.request.Request(target,data=request.get('body','').encode() if request.get('body') else None,headers=request['headers'],method=request['method'])
   try:
    with urllib.request.urlopen(req,timeout=5) as response:return {'status':response.status,'body':response.read().decode()}
   except urllib.error.HTTPError as e:return {'status':e.code,'body':e.read().decode()}
  mock=r'''(() => {const handlers={};window.testEmit=event=>(handlers[event]||[]).forEach(fn=>fn({}));window.Otzaria={on(event,fn){(handlers[event]||=[]).push(fn);if(event==='plugin.boot')setTimeout(()=>fn({}),0);},call(method,args){if(method==='network.fetchStream')return(async function*(){const r=await window.httpBridge(args);yield{type:'response',status:r.status,ok:r.status===200};const half=Math.floor(r.body.length/2);yield{type:'data',body:r.body.slice(0,half)};yield{type:'data',body:r.body.slice(half)};})();if(method==='storage.get')return Promise.resolve({success:true,data:JSON.parse(localStorage.getItem(args.key)||'null')});if(method==='storage.set'){localStorage.setItem(args.key,JSON.stringify(args.value));return Promise.resolve({success:true,data:true});}throw Error(method);}};})();'''
  running=True
  def tick():
   while running:self.player.tick();time.sleep(.02)
  worker=threading.Thread(target=tick,daemon=True);worker.start()
  try:
   with sync_playwright() as p:
    browser=p.chromium.launch(headless=True);page=browser.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.expose_binding('httpBridge',bridge);page.add_init_script(mock);page.goto(f'http://127.0.0.1:{web.server_port}/')
    expect(page.locator('#add-file')).to_be_enabled();page.locator('#open-companion').click();page.locator('#companion-token').fill('wrong');page.locator('#companion-connect').click();expect(page.locator('#companion-status')).to_contain_text('Pairing required')
    page.locator('#companion-remember').check();page.locator('#companion-token').fill('test-pairing-code');page.locator('#companion-connect').click();expect(page.locator('#companion-tracks .track')).to_have_count(2)
    self.assertEqual(page.evaluate("JSON.parse(localStorage.getItem('companion-connection-v1')).token"),'test-pairing-code')
    page.reload();expect(page.locator('#companion-status')).to_contain_text('מחובר');page.locator('#open-companion').click();expect(page.locator('#companion-tracks .track')).to_have_count(2)
    page.locator('#companion-remember').uncheck();page.wait_for_function("JSON.parse(localStorage.getItem('companion-connection-v1')).token===null")
    page.locator('#sidekick-options summary').click();page.locator('#companion-sleep').select_option('15');expect(page.locator('#companion-sleep-status')).to_contain_text('הניגון יושהה בעוד');self.assertIsNotNone(self.player.sleep_deadline)
    page.locator('#companion-sleep').select_option('0')
    # Folders are empty until the user creates one, and survive through host state.
    self.assertEqual(self.player.saved['folders'],[])
    page.locator('#companion-new-folder').click();page.locator('#dialog-input').fill('My folder');page.locator('#text-dialog button[value=save]').click();expect(page.locator('#companion-tracks .track')).to_have_count(0)
    folder_id=self.player.saved['folders'][0]['id'];page.locator('#companion-folder').select_option('all');page.locator('#companion-tracks select').first.select_option(folder_id)
    page.locator('#companion-folder').select_option(folder_id);expect(page.locator('#companion-tracks .track')).to_have_count(1)
    page.locator('#companion-rename-folder').click();page.locator('#dialog-input').fill('Renamed folder');page.locator('#text-dialog button[value=save]').click();expect(page.locator('#companion-folder option:checked')).to_have_text('Renamed folder')
    page.locator('#companion-folder').select_option('all')
    page.locator('#companion-tracks .track-title').first.click();expect(page.locator('#companion-title')).to_have_text('First.wav')
    page.wait_for_timeout(250);self.assertEqual(self.backend.status,'playing')
    page.locator('#companion-speed').select_option('1.5');page.wait_for_timeout(100);self.assertEqual(self.backend.rate,1.5)
    page.locator('#companion-filter').select_option('unplayed');page.locator('#companion-filter').select_option('all')
    page.locator('#companion-seek').fill('40');page.locator('#companion-seek').dispatch_event('change');page.wait_for_timeout(100);self.assertEqual(self.backend.position,40)
    page.evaluate('document.activeElement.blur()');page.keyboard.press('3');page.wait_for_timeout(100);self.assertEqual(self.player.saved['skipSeconds'],60)
    page.keyboard.press('ArrowRight');page.wait_for_timeout(100);self.assertEqual(self.backend.position,100)
    page.locator('#companion-search').fill('');page.locator('#companion-search').press('Space');self.assertEqual(self.backend.status,'playing');page.locator('#companion-search').fill('')
    page.locator('#companion-mark-name').fill('Review');page.locator('#companion-mark').click();expect(page.locator('#companion-marks .bookmark-row')).to_have_count(1)
    page.locator('#companion-auto').check();page.wait_for_timeout(100)
    # Suspension of the plugin must not stop the companion or prevent queue advancement.
    page.evaluate("testEmit('plugin.suspended')");self.assertEqual(self.backend.status,'playing')
    with self.player.lock:self.player.was_playing=True;self.backend.position=120;self.backend.status='ended'
    page.wait_for_timeout(200);self.assertEqual(self.player.saved['currentId'],self.player.tracks[1]['id']);self.assertEqual(self.backend.status,'playing')
    page.evaluate("testEmit('plugin.resumed')");expect(page.locator('#companion-title')).to_have_text('Second.wav')
    page.locator('#companion-stop').click();page.wait_for_timeout(100);self.assertEqual(self.backend.status,'stopped')
    self.assertFalse(errors,errors);page.evaluate("document.querySelector('#sidekick-connection').open=false;document.querySelector('#sidekick-options').open=false");page.screenshot(path=str(ROOT/'companion-preview.png'),full_page=True);page.set_viewport_size({'width':390,'height':900});page.screenshot(path=str(ROOT/'sidekick-mobile-preview.png'),full_page=True);page.set_viewport_size({'width':1280,'height':950});page.evaluate("ShiurUI.applyTheme({mode:'dark',colorScheme:{primary:'#ddbb8a',onPrimary:'#402d11',surface:'#181713',onSurface:'#e8e2d8',outline:'#938d82',surfaceContainer:'#27251f'}})");page.screenshot(path=str(ROOT/'sidekick-dark-preview.png'),full_page=True);browser.close()
  finally:running=False;worker.join(timeout=2);web.shutdown();web.server_close()
if __name__=='__main__':unittest.main(verbosity=2)
