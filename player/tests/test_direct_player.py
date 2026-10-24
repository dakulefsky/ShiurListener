"""Real visible-page audio under Chromium's strict user-click policy."""
import contextlib,functools,http.server,json,math,pathlib,shutil,struct,tempfile,threading,wave
from playwright.sync_api import sync_playwright,expect
ROOT=pathlib.Path(__file__).resolve().parents[1]
MOCK=r'''(() => {
const handlers={};window.bridge={calls:[],emit:(topic,payload={})=>Promise.all((handlers[topic]||[]).map(fn=>fn(payload)))};
window.playAudit=[];const originalPlay=HTMLMediaElement.prototype.play;
HTMLMediaElement.prototype.play=function(){playAudit.push({active:navigator.userActivation?.isActive,src:this.src});return originalPlay.call(this);};
window.Otzaria={on(topic,fn){(handlers[topic]||=[]).push(fn);if(topic==='plugin.boot')setTimeout(()=>fn({app:{runMode:'foreground'},theme:{mode:'light',colorScheme:{primary:'#23604d',onPrimary:'#ffffff',surface:'#fafafa',onSurface:'#222222',outline:'#888888'}}}),0);},async call(method,args={}){
 bridge.calls.push({method,args});let data;
 if(method==='app.getGrantedPermissions')data={permissions:window.fileRevoked?[]:['fs.user_files.read']};
 else if(method==='storage.get')data=JSON.parse(localStorage.getItem(args.key)||'null');
 else if(method==='storage.set'){localStorage.setItem(args.key,JSON.stringify(args.value));data=true;}
 else if(method==='storage.remove'){localStorage.removeItem(args.key);data=true;}
 else if(method==='fs.pickUserFile')data={cancelled:false,token:'single',name:'Single.wav'};
 else if(method==='fs.pickUserFolder')data={cancelled:false,folderToken:'series',name:'Series'};
 else if(method==='fs.listUserFolder')data={entries:[{type:'file',name:'First.wav',path:'First.wav'},{type:'file',name:'Second.wav',path:'Second.wav'}]};
 else if(method==='fs.resolveFileUrl'||method==='fs.openFolderFile'){
  if(window.fileRevoked||window.fileMissing)return {success:false,error:{message:'File unavailable'}};
  data={url:location.origin+'/sample.wav'};
 }else return {success:false,error:{message:'Unexpected method: '+method}};
 return {success:true,data};
}};
})();'''
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*_):pass
 def do_GET(self):
  if self.path.split('?')[0]!='/sample.wav':return super().do_GET()
  data=(pathlib.Path(self.directory)/'sample.wav').read_bytes();start,end=0,len(data)-1;ranged=self.headers.get('Range')
  if ranged:
   bounds=ranged.removeprefix('bytes=').split('-');start=int(bounds[0] or 0)
   if bounds[1]:end=min(end,int(bounds[1]))
  self.send_response(206 if ranged else 200);self.send_header('Content-Type','audio/wav');self.send_header('Accept-Ranges','bytes');self.send_header('Content-Length',str(end-start+1))
  if ranged:self.send_header('Content-Range',f'bytes {start}-{end}/{len(data)}')
  self.end_headers()
  with contextlib.suppress(BrokenPipeError,ConnectionResetError):self.wfile.write(data[start:end+1])
def main():
 with tempfile.TemporaryDirectory() as directory:
  for file in (ROOT/'plugin').iterdir():shutil.copy(file,directory)
  with wave.open(str(pathlib.Path(directory)/'sample.wav'),'wb') as wav:
   wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(8000)
   tone=b''.join(struct.pack('<h',int(2000*math.sin(2*math.pi*220*n/8000))) for n in range(8000));wav.writeframes(tone*120)
  server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=directory));threading.Thread(target=server.serve_forever,daemon=True).start()
  url=f'http://127.0.0.1:{server.server_port}/'
  try:
   with sync_playwright() as p:
    # No autoplay exemption: this reproduces the policy that blocked the old build.
    browser=p.chromium.launch(headless=True,args=['--autoplay-policy=document-user-activation-required','--disable-features=PreloadMediaEngagementData,MediaEngagementBypassAutoplayPolicies'])
    context=browser.new_context(viewport={'width':1440,'height':1000});context.add_init_script(MOCK)
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto(url)
    expect(page.locator('#add-folder')).to_be_enabled()
    expect(page.locator('#welcome')).to_be_visible();assert page.locator('#audio').get_attribute('controls') is not None
    assert 'nodownload' in page.locator('#audio').get_attribute('controlslist')
    page.locator('#add-folder').click();expect(page.locator('.track')).to_have_count(2)
    page.locator('.track-title',has_text='First.wav').click();expect(page.locator('#status')).to_contain_text('השיעור מוכן')
    page.screenshot(path=str(ROOT/'player-preview.png'),full_page=True)
    # The first audio.play() comes from a real click in the same visible page.
    page.locator('#play').click();expect(page.locator('#play')).to_have_attribute('aria-label','השהיה')
    audit=page.evaluate('playAudit');assert audit and audit[0]['active'] is True,audit
    page.wait_for_function('document.querySelector("#audio").currentTime>0.2')
    page.locator('#play').click();page.wait_for_function('document.querySelector("#audio").paused')
    page.locator('#seek').fill('65');expect(page.locator('#position')).to_have_text('1:05')
    page.wait_for_function("JSON.parse(localStorage.getItem('shiur-audio-v1:progress')).positions['folder:series:First.wav'].positionMs===65000")
    page.locator('.track-title',has_text='Second.wav').click();expect(page.locator('#status')).to_contain_text('השיעור מוכן')
    page.locator('#play').click();page.wait_for_function('!document.querySelector("#audio").paused')
    page.locator('#play').click();page.wait_for_function('document.querySelector("#audio").paused')
    page.locator('#seek').fill('23');expect(page.locator('#position')).to_have_text('0:23')
    page.locator('.track-title',has_text='First.wav').click();expect(page.locator('#position')).to_have_text('1:05')
    page.reload();expect(page.locator('#play')).to_be_enabled();expect(page.locator('#position')).to_have_text('1:05')
    assert page.locator('#audio').evaluate('(a)=>a.paused');assert page.evaluate('playAudit.length')==0
    page.locator('#play').click();page.wait_for_function('!document.querySelector("#audio").paused')
    # Moving focus to the book inside a visible split pane should not pause the player.
    page.locator('#compact-player').click();expect(page.locator('body')).to_have_class('compact-mode')
    page.set_viewport_size({'width':380,'height':850});assert page.locator('#play').is_visible()
    before=page.locator('#audio').evaluate('(a)=>a.currentTime');page.wait_for_function('(n)=>document.querySelector("#audio").currentTime>n+.5',arg=before)
    page.screenshot(path=str(ROOT/'compact-player-preview.png'),full_page=True)
    # A true Otzaria suspension pauses immediately; resuming never starts sound.
    page.evaluate("bridge.emit('plugin.suspended')");assert page.locator('#audio').evaluate('(a)=>a.paused')
    saved=page.locator('#audio').evaluate('(a)=>a.currentTime');page.evaluate("bridge.emit('plugin.resumed')")
    assert page.locator('#audio').evaluate('(a)=>a.paused')
    page.locator('#play').click();page.wait_for_function('!document.querySelector("#audio").paused')
    page.locator('#play').click();page.wait_for_function('document.querySelector("#audio").paused')
    assert page.locator('#audio').evaluate('(a)=>a.currentTime')>=saved
    page.locator('#skip-interval').select_option('10');page.locator('#forward').click()
    page.wait_for_function('(n)=>document.querySelector("#audio").currentTime>n+9',arg=saved)
    page.locator('#speed').select_option('1.5');page.wait_for_function('document.querySelector("#audio").playbackRate===1.5')
    # Native audio controls, keyboard controls, and saved progress use the same element.
    page.locator('#compact-player').click();page.set_viewport_size({'width':1440,'height':1000})
    page.evaluate('document.activeElement.blur()');page.keyboard.press('Space');page.wait_for_function('!document.querySelector("#audio").paused')
    page.keyboard.press('Space');page.wait_for_function('document.querySelector("#audio").paused')
    page.locator('#search').fill('');page.locator('#search').press('Space');assert page.locator('#audio').evaluate('(a)=>a.paused')
    page.locator('#search').fill('')
    first=page.locator('.track',has=page.locator('.track-title',has_text='First.wav'))
    first.locator('summary').click()
    first.locator('.reset-progress').click();page.locator('#confirm-dialog button[value=yes]').click();expect(page.locator('#position')).to_have_text('0:00')
    positions=page.evaluate("JSON.parse(localStorage.getItem('shiur-audio-v1:progress')).positions")
    assert positions['folder:series:Second.wav']['positionMs']==23000
    page.locator('#more-options summary').click();page.locator('#autonext').check()
    page.locator('#audio').evaluate('(a)=>{a.currentTime=119.9}')
    page.locator('#play').click();expect(page.locator('#current-title')).to_have_text('Second.wav')
    page.wait_for_function('!document.querySelector("#audio").paused')
    page.locator('#play').click();page.wait_for_function('document.querySelector("#audio").paused')
    page.locator('#sleep-timer').select_option('15')
    expect(page.locator('#sleep-countdown')).not_to_have_text('')
    page.locator('#sleep-timer').select_option('0')
    page.locator('#new-playlist').click();page.locator('#dialog-input').fill('My series');page.locator('#text-dialog button[value=save]').click();expect(page.locator('#view-title')).to_have_text('My series')
    # A missing last-used file must not prevent adding/replacing files in the library.
    context.add_init_script('window.fileMissing=true');page.reload();expect(page.locator('#add-file')).to_be_enabled();expect(page.locator('#status')).to_contain_text('השיעור האחרון אינו זמין')
    page.evaluate('window.fileMissing=false');page.locator('#retry-setup').click();expect(page.locator('#status')).to_contain_text('השיעור מוכן')
    page.locator('#play').click();page.wait_for_function('!document.querySelector("#audio").paused')
    page.locator('#reader-controls').click();page.locator('#sound-check').click()
    page.wait_for_function('!document.querySelector("#sound-check-audio").paused')
    assert page.locator('#audio').evaluate('(a)=>a.paused')
    page.evaluate("bridge.emit('plugin.suspended')");assert page.locator('#sound-check-audio').evaluate('(a)=>a.paused')
    assert not errors,errors
    manifest=json.loads((ROOT/'plugin/manifest.json').read_text())
    assert 'background' not in manifest['contributes']
    assert not any(x in manifest['permissions'] for x in ['app.run_on_startup','app.background_keep_alive','network.access','app.open_url'])
    assert page.locator('iframe,a[href]').count()==0
    browser.close()
   print('PASS: visible-page audio starts from a real click under strict autoplay; no hidden player; per-track resume/reload; compact mode; suspend/pause; speeds/skips; keyboard; reset; folder management; missing-file recovery. Actual Otzaria still requires a local check.')
  finally:server.shutdown();server.server_close()
if __name__=='__main__':main()
