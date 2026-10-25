"""Stock Otzaria JS bridge, file:// UI, CSP and separate loopback media origin.
This exercises Chromium rather than a Windows WebView2 installation.
"""
import functools,http.server,json,os,pathlib,re,shutil,tempfile,threading,wave,urllib.parse
from playwright.sync_api import sync_playwright,expect
from test_direct_player import MOCK,Quiet
ROOT=pathlib.Path(__file__).resolve().parents[1]
HOST=pathlib.Path(os.environ.get('OTZARIA_SOURCE_ROOT',str(ROOT.parent/'otzaria-native')))/'lib/plugins/view/plugin_sdk_scripts.dart'
class Media(Quiet):
 def do_GET(self):
  if self.path.startswith('/f/org.shiurplayer.local/'):
   self.path='/sample.wav'
  return super().do_GET()
 def end_headers(self):
  self.send_header('Access-Control-Allow-Origin','null')
  super().end_headers()
def main():
 host=HOST.read_text()
 stub=re.search(r"const String _sdkStubCore = r'''(.*?)''';",host,re.S).group(1)
 start=host.index('  var _ls = {};');end=host.index("\n})();\n''';",start)
 boot='(function(){'+host[start:end].replace('$nonceJson',json.dumps('test-nonce')).replace('$payloadJson',json.dumps({'theme':{'mode':'light','colorScheme':{'primary':'#73552e','onPrimary':'#ffffff','surface':'#faf8f3','onSurface':'#29271f'}}}))+'})();'
 with tempfile.TemporaryDirectory() as tmp:
  root=pathlib.Path(tmp);plugin=root/'plugin';shutil.copytree(ROOT/'plugin',plugin)
  with wave.open(str(root/'sample.wav'),'wb') as f:
   f.setnchannels(1);f.setsampwidth(2);f.setframerate(8000);f.writeframes((ROOT/'plugin/sound-check.wav').read_bytes()[44:]*60)
  server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Media,directory=tmp));threading.Thread(target=server.serve_forever,daemon=True).start()
  media=os.environ.get('INSIDE_REAL_MEDIA_URL',f'http://127.0.0.1:{server.server_port}/f/org.shiurplayer.local/test-token')
  media_port=urllib.parse.urlparse(media).port
  csp=f"default-src 'self' file: data: blob: http://127.0.0.1:{media_port}/f/org.shiurplayer.local/ 'unsafe-inline' 'unsafe-eval' 'wasm-unsafe-eval'; base-uri 'self'; form-action 'self'"
  p=plugin/'index.html';p.write_text(p.read_text().replace('<head>','<head><meta http-equiv="Content-Security-Policy" content="'+csp+'">'))
  native='''const nativeCall=window.Otzaria.call;window.flutter_inappwebview={callHandler:async(name,request)=>{
 if(name!=='otzaria_rpc')throw Error('Unknown handler');
 if(request.nonce!=='test-nonce')throw Error('Invalid nonce');
 if(request.method==='storage.get'&&request.payload.key==='library-v1'&&window.failLibraryRead)return {success:false,error:{message:'Library read failed'}};
 if(['fs.resolveFileUrl','fs.openFolderFile'].includes(request.method)){
  if(window.fileMissing||window.fileRevoked)return {success:false,error:{message:'File unavailable'}};
  return {success:true,data:{url:MEDIA_URL}};
 }
 return nativeCall(request.method,request.payload);
 }};Object.defineProperty(crypto,'randomUUID',{value:undefined,configurable:true});'''.replace('MEDIA_URL',json.dumps(media))
  try:
   with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True,args=['--autoplay-policy=document-user-activation-required','--disable-features=PreloadMediaEngagementData,MediaEngagementBypassAutoplayPolicies'])
    context=browser.new_context();context.add_init_script(MOCK+'\n'+native+'\n(function(){'+stub+'})();')
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(p.as_uri());page.evaluate('''localStorage.setItem('library-v1',JSON.stringify({version:1,tracks:[{id:'saved',token:'saved-token',name:'Preserved.wav',position:74.123,bookmarks:[]}]}));window.fileRevoked=true;window.failLibraryRead=true''');page.evaluate(boot)
    expect(page.locator('#status')).to_contain_text('Library read failed')
    page.evaluate("localStorage.setItem('shiur-audio-v1:state',JSON.stringify({marker:'preserve'}))")
    page.evaluate("async()=>{window.dispatchEvent(new Event('pagehide'));window.dispatchEvent(new CustomEvent('plugin.resumed',{detail:{}}));await new Promise(r=>setTimeout(r,50));}")
    assert page.evaluate("JSON.parse(localStorage.getItem('shiur-audio-v1:state')).marker")=='preserve'
    assert page.evaluate("JSON.parse(localStorage.getItem('library-v1')).tracks[0].name")=='Preserved.wav'
    page.evaluate('window.failLibraryRead=false');page.locator('#retry-setup').click()
    expect(page.locator('#recovery')).to_be_visible();expect(page.locator('#add-file')).to_be_disabled()
    page.locator('#reader-controls').click();page.locator('#sound-check').click();page.wait_for_function('!document.querySelector("#sound-check-audio").paused')
    page.evaluate('document.querySelector("#sound-check-audio").pause();window.fileRevoked=false')
    page.locator('#retry-setup').click();expect(page.locator('#add-file')).to_be_enabled()
    page.locator('#add-file').click();expect(page.locator('#status')).to_contain_text('השיעור מוכן')
    page.locator('#play').click();page.wait_for_function('document.querySelector("#audio").currentTime>.1')
    assert page.evaluate('playAudit.at(-1).active') is True
    assert page.locator('#audio').evaluate('(a)=>a.src').startswith(media)
    page.locator('#play').click();page.locator('#seek').fill('23.456')
    page.wait_for_function("JSON.parse(localStorage.getItem('shiur-audio-v1:progress')).positions['file:single'].positionMs===23456")
    page.reload();page.evaluate(boot);expect(page.locator('#play')).to_be_enabled();expect(page.locator('#position')).to_have_text('0:23')
    assert page.locator('#audio').evaluate('(a)=>a.paused')
    # Exercise the previously broken path: failed last recording, then Play reloads it.
    page.reload();page.evaluate('window.fileMissing=true');page.evaluate(boot)
    expect(page.locator('#recovery')).to_be_visible();expect(page.locator('#add-file')).to_be_enabled()
    page.evaluate('window.fileMissing=false');page.locator('#play').click();expect(page.locator('#status')).to_contain_text('השיעור מוכן')
    page.locator('#play').click();page.wait_for_function('!document.querySelector("#audio").paused')
    # Suspension uses actual SDK DOM events, not the simpler test event map.
    page.evaluate("window.dispatchEvent(new CustomEvent('plugin.suspended',{detail:{}}))")
    assert page.locator('#audio').evaluate('(a)=>a.paused')
    assert not errors,errors
    browser.close()
   print('PASS: actual Otzaria JS stub/boot/RPC events; file-origin UI with CSP; cross-origin loopback WAV; strict click activation; permission retry; old WebView UUID fallback; saved millisecond position; missing-file retry; suspension. Windows native host remains unverified.')
  finally:server.shutdown();server.server_close()
if __name__=='__main__':main()
