/* Companion protocol v1. All requests go through Otzaria's native HTTP bridge. */
(function(){
'use strict';
let hostReady=false,token='',tracks=[],snapshot=null,polling=false,visible=false,timer=null,marks={},lastError='',folderView='all',folderSignature='',hotkeySignature='';
const $=id=>document.getElementById(id),base='http://127.0.0.1:18473';
const section=document.createElement('section');section.id='companion-panel';section.hidden=true;section.style.cssText='margin:16px 32px 32px';
section.innerHTML=`<div class="section-head"><h2>נגן מלווה · האזנה ברקע</h2><button id="companion-back">חזרה לנגן הרגיל</button></div>
<p class="companion-install-note">התקנה מחנות התוספים מתקינה את הממשק בלבד. ניגון ברקע, קיצורים כלליים והנגן הצף דורשים הפעלה נפרדת של הנגן המלווה במחשב. הנגן הרגיל זמין בלי הנגן המלווה.</p><p>הפעילו את הנגן המלווה במחשב, בחרו תיקיית שיעורים והדביקו את קוד הצימוד מהחלון שלו. יש להשאיר את חלון הנגן המלווה פתוח.</p>
<div class="actions"><label>קוד צימוד <input id="companion-token" type="password" autocomplete="off" spellcheck="false"></label><label class="remember-pairing"><input id="companion-remember" type="checkbox"> זכירת החיבור במכשיר הזה</label><button id="companion-connect">חיבור</button><button id="companion-refresh">רענון</button><button id="companion-stop">עצירה</button><button id="companion-floating">הצגה / הסתרה של הנגן הצף</button></div>
<p id="companion-status" role="status" aria-live="polite"></p>
<div class="companion-grid"><section class="library"><label class="search">חיפוש שיעורים<input id="companion-search" type="search"></label><div class="folder-toolbar"><label>תיקייה<select id="companion-folder"><option value="all">כל השיעורים</option></select></label><button id="companion-new-folder">＋ תיקייה חדשה</button><button id="companion-rename-folder" hidden>שינוי שם</button><button id="companion-delete-folder" hidden>מחיקה</button></div><label class="listening-filter">הצגה<select id="companion-filter"><option value="all">כל השיעורים</option><option value="continue">המשך האזנה</option><option value="unplayed">טרם הושמעו</option><option value="done">האזנה שהושלמה</option></select></label><p id="companion-count" class="muted"></p><div id="companion-tracks"></div></section>
<section class="player"><span class="eyebrow">ניגון ברקע דרך VLC</span><h2 id="companion-title">בחרו שיעור</h2><input id="companion-seek" type="range" min="0" max="0" value="0" step="1" aria-label="מיקום בנגן המלווה"><div id="companion-time" dir="ltr"></div><div class="transport" dir="ltr"><button id="companion-previous" aria-label="השיעור הקודם">⏮</button><button id="companion-back15">−15</button><button id="companion-play" class="primary" aria-label="ניגון או השהיה">▶</button><button id="companion-forward15">+15</button><button id="companion-next" aria-label="השיעור הבא">⏭</button></div><div class="player-options"><label>מהירות <select id="companion-speed"><option value="0.75">0.75×</option><option value="1">1×</option><option value="1.25">1.25×</option><option value="1.5">1.5×</option><option value="1.75">1.75×</option><option value="2">2×</option></select></label><label>עוצמה<input id="companion-volume" type="range" min="0" max="1" step="0.05" value="1"></label></div><label class="skip-option">דילוג<select id="companion-skip"><option value="10">10 שניות</option><option value="15">15 שניות</option><option value="60">דקה</option></select></label><label class="autonext"><input id="companion-auto" type="checkbox"> מעבר אוטומטי לשיעור הבא ברקע</label><label class="skip-option">טיימר שינה<select id="companion-sleep"><option value="0">כבוי</option><option value="15">15 דקות</option><option value="30">30 דקות</option><option value="60">שעה</option><option value="90">שעה וחצי</option></select></label><p id="companion-sleep-status" class="muted" role="status"></p><h3>סימניות</h3><div class="actions"><input id="companion-mark-name" placeholder="שם הסימנייה" maxlength="160"><button id="companion-mark">＋ שמירה</button></div><div id="companion-marks"></div></section></div><details class="keyboard-help"><summary>שליטה מכל עמוד ומכל תוכנה</summary><p>הנגן המלווה רושם קיצורים כלליים ב־Windows. אין צורך לחזור ללשונית הנגן. כל הקיצורים הבאים מתחילים ב־Ctrl + Alt + Shift:</p><ul><li>P — הפעלה או השהיה</li><li>חץ שמאלה / ימינה — אחורה / קדימה לפי משך הדילוג שנבחר</li><li>חץ למעלה / למטה — שינוי מהירות</li><li>Page Up / Page Down — השיעור הקודם / הבא</li><li>1 / 2 / 3 — בחירת 10 שניות / 15 שניות / דקה</li><li>S — עצירה ושמירת המיקום</li><li>F — הצגה / הסתרה של הנגן הצף</li></ul><p>לשינוי או לביטול קיצור: ערכו את hotkeys.json בתיקיית הנתונים של הנגן והפעילו אותו מחדש. קיצור שתפוס על ידי תוכנה אחרת לא יירשם.</p><div id="companion-hotkeys"></div></details>`;
document.querySelector('main').after(section);
section.style.cssText='';
const setup=document.createElement('details');setup.id='sidekick-connection';setup.open=true;
setup.innerHTML='<summary>חיבור לנגן המלווה</summary><div class="setup-steps"><p><strong>1</strong> פתחו את Sidekick במחשב ובחרו את תיקיית השיעורים.</p><p><strong>2</strong> העתיקו את קוד החיבור מהחלון שלו והדביקו כאן.</p><p><strong>3</strong> לחצו על חיבור. השאירו את Sidekick פועל בזמן ההאזנה.</p></div>';
setup.append(section.querySelector(':scope > .actions'));
section.querySelectorAll(':scope > p:not([id])').forEach(p=>p.remove());
section.querySelector(':scope > .section-head h2').textContent='השיעורים שלכם, גם בזמן הלימוד';
section.prepend(setup);
const grid=section.querySelector('.companion-grid'),player=grid.querySelector('.player');grid.prepend(player);
player.querySelector('.eyebrow').textContent='כעת בנגן · ההאזנה ממשיכה גם בכרטיסיות אחרות';
player.querySelector('.player-options').append($('companion-skip').closest('label'));
const extras=document.createElement('details');extras.id='sidekick-options';extras.innerHTML='<summary>טיימר, המשך אוטומטי וסימניות</summary>';
let option=player.querySelector('.autonext');while(option){const next=option.nextSibling;extras.append(option);option=next;}player.append(extras);
const tools=document.createElement('div');tools.className='sidekick-tools';for(const id of ['companion-floating','companion-refresh','companion-stop'])tools.append($(id));player.append(tools);
$('companion-title').dir='auto';$('companion-token').placeholder='הדביקו את קוד החיבור';
const tell=(text,error=false)=>{$('companion-status').textContent=text;$('companion-status').classList.toggle('error',error);if(error)setup.open=true;};
const guard=fn=>(...args)=>Promise.resolve().then(()=>fn(...args)).catch(e=>tell(e.message,true));
const format=s=>ShiurCore.format(s);
async function request(path,body){
 if(!hostReady)throw Error('החיבור זמין מתוך אוצריא בלבד.');
 const params={url:base+path,method:body?'POST':'GET',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},timeoutMs:5000};if(body)params.body=JSON.stringify(body);
 let text='',httpStatus=0;
 for await(const chunk of window.Otzaria.call('network.fetchStream',params)){
  if(chunk.success===false||chunk.type==='error')throw Error(chunk.error?.message||chunk.message||'בקשת החיבור נכשלה.');
  if(chunk.type==='response')httpStatus=chunk.status;
  if(chunk.type==='data')text+=chunk.body;
 }
 let data;try{data=JSON.parse(text);}catch{throw Error('לא התקבלה תשובה תקינה מהנגן המלווה. בדקו שהוא פועל.');}
 if(httpStatus!==200)throw Error(data.error||`שגיאת חיבור ${httpStatus}`);return data;
}
async function command(op,extra={}){snapshot=await request('/v1/command',{op,...extra});renderState();}
async function syncFloatingTheme(theme){if(!token||!hostReady||!theme?.colorScheme)return;await command('floating_theme',{theme:{...theme.colorScheme,fontFamily:theme.typography?.uiFontFamily||'Rubik'}});}
document.addEventListener('shiur-theme',event=>{if(token)guard(()=>syncFloatingTheme(event.detail))();});
function renderState(){
 if(!snapshot)return;
 const t=tracks.find(t=>t.id===snapshot.currentId);
 $('companion-title').textContent=t?.name||'בחרו שיעור';ShiurUI.setPlay($('companion-play'),snapshot.status!=='playing');
 if(document.activeElement!==$('companion-seek')){$('companion-seek').max=snapshot.duration;$('companion-seek').value=snapshot.position;}
 $('companion-time').textContent=`${format(snapshot.position)} / ${format(snapshot.duration)}`;
 $('companion-speed').value=String(snapshot.speed);if(document.activeElement!==$('companion-volume'))$('companion-volume').value=snapshot.volume;
 $('companion-auto').checked=snapshot.autoNext;
 $('companion-sleep-status').textContent=snapshot.sleepRemaining?`הניגון יושהה בעוד ${format(snapshot.sleepRemaining)}`:'הניגון לא יושהה אוטומטית';if(document.activeElement!==$('companion-sleep'))$('companion-sleep').value=String(snapshot.sleepMinutes||0);
 $('companion-skip').value=String(snapshot.skipSeconds||15);$('companion-back15').textContent='−'+(snapshot.skipSeconds||15);$('companion-forward15').textContent='+'+(snapshot.skipSeconds||15);
 $('companion-back15').setAttribute('aria-label',`אחורה ${snapshot.skipSeconds||15} שניות`);$('companion-forward15').setAttribute('aria-label',`קדימה ${snapshot.skipSeconds||15} שניות`);
 const folders=JSON.stringify(snapshot.folders||[]);if(folders!==folderSignature){folderSignature=folders;renderFolders();renderTracks();}
 const keys=JSON.stringify(snapshot.hotkeys||[]);if(keys!==hotkeySignature){hotkeySignature=keys;renderHotkeys();}
 if(t){t.position=snapshot.position;t.duration=snapshot.duration;}
 for(const row of $('companion-tracks').children){const track=tracks.find(t=>t.id===row.dataset.id);const progress=row.querySelector('[data-progress]');if(track&&progress)progress.textContent=track.position?`${format(track.position)} / ${format(track.duration)}`:'טרם הושמע';} 
 if(snapshot.error)tell(snapshot.error,true);
 $('companion-floating').disabled=!snapshot.floatingAvailable;$('companion-floating').title=snapshot.floatingStatus||'';
 renderMarks();
 for(const row of $('companion-tracks').children)row.classList.toggle('selected',row.dataset.id===snapshot.currentId);
}
function renderTracks(){
 const container=$('companion-tracks');container.replaceChildren();const q=$('companion-search').value.toLowerCase();
 const folder=(snapshot?.folders||[]).find(f=>f.id===folderView);const viewTracks=folder?folder.trackIds.map(id=>tracks.find(t=>t.id===id)).filter(Boolean):tracks;
 const filter=$('companion-filter').value;const shown=viewTracks.filter(t=>(t.name+' '+t.source).toLowerCase().includes(q)).filter(t=>filter==='all'||(filter==='continue'&&t.position>0&&(!t.duration||t.position<t.duration-.5))||(filter==='unplayed'&&!t.position)||(filter==='done'&&t.duration>0&&t.position>=t.duration-.5));$('companion-count').textContent=`${shown.length} שיעורים`;
 for(const t of shown){
  const row=document.createElement('article');row.className='track';row.dataset.id=t.id;const info=document.createElement('div');const play=document.createElement('button');play.className='track-title';play.textContent=t.name;play.dir='auto';play.onclick=guard(async()=>{await command('load',{id:t.id,queue:viewTracks.map(t=>t.id)});await command('play');});const source=document.createElement('small');source.textContent=t.source;source.dir='auto';const progress=document.createElement('small');progress.dataset.progress='';progress.dir='ltr';progress.textContent=t.position?`${format(t.position)} / ${format(t.duration)}`:'טרם הושמע';info.append(play,source,progress);row.append(info);
  const actions=document.createElement('div');actions.className='actions';const select=document.createElement('select');select.setAttribute('aria-label',`הוספת ${t.name} לתיקייה`);select.add(new Option('＋ לתיקייה',''));for(const f of snapshot?.folders||[])select.add(new Option(f.name,f.id));select.disabled=!(snapshot?.folders||[]).length;select.onchange=guard(async()=>{const id=select.value;if(id)await command('folder_add',{id,trackId:t.id});select.value='';});actions.append(select);
  if(folder){const remove=document.createElement('button');remove.textContent='הסרה מהתיקייה';remove.className='remove';remove.onclick=guard(()=>command('folder_remove',{id:folder.id,trackId:t.id}));actions.append(remove);}row.append(actions);container.append(row);
 }
 if(!container.children.length){const p=document.createElement('p');p.textContent=folder?'התיקייה ריקה. הוסיפו שיעורים מהספרייה באמצעות תפריט ״לתיקייה״.':'אין שיעורים להצגה. לשינוי תיקיית המקור או לסריקה מחדש יש להפעיל מחדש את הנגן המלווה.';container.append(p);}
}
function renderFolders(){
 const folders=snapshot?.folders||[];if(folderView!=='all'&&!folders.some(f=>f.id===folderView))folderView='all';
 const select=$('companion-folder');select.replaceChildren(new Option('כל השיעורים','all'));folders.forEach(f=>select.add(new Option(f.name,f.id)));select.value=folderView;$('companion-rename-folder').hidden=$('companion-delete-folder').hidden=folderView==='all';
}
function askFolder(title,initial=''){return new Promise(resolve=>{const d=$('text-dialog');$('dialog-title').textContent=title;$('dialog-input').value=initial;d.returnValue='cancel';d.addEventListener('close',()=>resolve(d.returnValue==='save'?$('dialog-input').value.trim():null),{once:true});d.showModal();$('dialog-input').focus();});}
function renderHotkeys(){const box=$('companion-hotkeys');box.replaceChildren();for(const item of snapshot?.hotkeys||[]){const line=document.createElement('p');line.dir='auto';line.textContent=(item.label||item.name)+': '+(item.registered?'פעיל':item.error||'לא זמין');if(!item.registered)line.className='error';box.append(line);}}
$('companion-folder').onchange=()=>{folderView=$('companion-folder').value;renderFolders();renderTracks();};
$('companion-new-folder').onclick=guard(async()=>{if(!snapshot)throw Error('יש להתחבר לנגן המלווה תחילה.');const name=await askFolder('תיקייה חדשה');if(name){await command('folder_create',{name});folderView=snapshot.folders[snapshot.folders.length-1].id;renderFolders();renderTracks();}});
$('companion-rename-folder').onclick=guard(async()=>{const folder=snapshot?.folders.find(f=>f.id===folderView);if(folder){const name=await askFolder('שינוי שם התיקייה',folder.name);if(name)await command('folder_rename',{id:folder.id,name});}});
$('companion-delete-folder').onclick=guard(async()=>{if(folderView==='all')return;const d=$('confirm-dialog');$('confirm-title').textContent='למחוק את התיקייה? השיעורים יישארו בספרייה.';d.returnValue='cancel';const yes=await new Promise(resolve=>{d.addEventListener('close',()=>resolve(d.returnValue==='yes'),{once:true});d.showModal();});if(yes)await command('folder_delete',{id:folderView});});
document.addEventListener('keydown',event=>{
 if(!visible||!snapshot||event.ctrlKey||event.altKey||event.metaKey||event.repeat||event.isComposing||document.querySelector('dialog[open]')||event.target.closest('input,select,textarea,button,summary,[contenteditable="true"]'))return;
 const key=/^Key[A-Z]$/.test(event.code)?event.code.slice(3).toLowerCase():event.key.toLowerCase();let task;
 if(event.code==='Space')task=()=>command('toggle');
 else if(key==='arrowleft'||key==='arrowright')task=()=>event.shiftKey?command(key==='arrowleft'?'previous':'next'):command('skip',{direction:key==='arrowleft'?-1:1});
 else if(['1','2','3'].includes(key))task=()=>command('skip_interval',{value:{1:10,2:15,3:60}[key]});
 else if(['+','=','-','_'].includes(key))task=()=>command('speed_step',{direction:['-','_'].includes(key)?-1:1});
 else if(key==='f')task=()=>$('companion-search').focus();else if(key==='n')task=()=>$('companion-new-folder').click();else if(key==='b')task=()=>$('companion-mark-name').focus();
 if(task){event.preventDefault();guard(task)();}
});
function renderMarks(){
 const box=$('companion-marks');box.replaceChildren();if(!snapshot?.currentId)return;
 for(const mark of marks[snapshot.currentId]||[]){const row=document.createElement('div');row.className='bookmark-row';const b=document.createElement('button');b.textContent=`${format(mark.position)} · ${mark.name}`;b.onclick=guard(()=>command('seek',{value:mark.position}));const del=document.createElement('button');del.textContent='×';del.setAttribute('aria-label','מחיקת סימנייה');del.onclick=guard(async()=>{marks[snapshot.currentId]=marks[snapshot.currentId].filter(m=>m.id!==mark.id);await saveMarks();renderMarks();});row.append(b,del);box.append(row);}
}
async function saveMarks(){const r=await window.Otzaria.call('storage.set',{key:'companion-bookmarks-v1',value:marks});if(!r.success)throw Error('שמירת הסימניות נכשלה.');}
async function refresh(){
 if(polling||!token||!visible)return;polling=true;
 try{snapshot=await request('/v1/state');renderState();if(lastError){tell('מחובר. ההאזנה תימשך גם כשהתוסף מוסתר.');lastError='';}}
 catch(e){lastError=e.message;tell('החיבור לנגן המלווה אבד. בדקו שהחלון שלו פתוח. '+e.message,true);}
 finally{polling=false;}
}
$('open-companion').onclick=()=>{visible=true;setup.open=true;document.querySelector('.notice').hidden=true;document.querySelector('main').hidden=true;section.hidden=false;document.querySelector('#audio').pause();if(!timer)timer=setInterval(refresh,1000);};
$('companion-back').onclick=guard(async()=>{try{if(token)await command('pause');}catch(e){$('status').textContent='לא ניתן להשהות את הנגן המלווה. אפשר לעצור אותו בחלון שלו.';$('status').classList.add('error');}finally{visible=false;section.hidden=true;document.querySelector('.notice').hidden=false;document.querySelector('main').hidden=false;}});
async function connect(){
 token=$('companion-token').value.trim();if(!token)throw Error('הדביקו את קוד הצימוד מהנגן המלווה.');
 const library=await request('/v1/library');tracks=library.tracks;renderTracks();snapshot=await request('/v1/state');renderState();await syncFloatingTheme(ShiurUI.currentTheme);const saved=await window.Otzaria.call('storage.set',{key:'companion-connection-v1',value:{token:$('companion-remember').checked?token:null}});if(!saved.success)throw Error('החיבור הצליח, אך לא ניתן לשמור את ההעדפה.');setup.open=false;tell(`מחובר · ${tracks.length} שיעורים. ההאזנה תימשך גם כשהתוסף מוסתר.`);
}
$('companion-connect').onclick=guard(connect);
$('companion-remember').onchange=guard(async()=>{if(!$('companion-remember').checked){const r=await window.Otzaria.call('storage.set',{key:'companion-connection-v1',value:{token:null}});if(!r.success)throw Error('לא ניתן למחוק את החיבור השמור.');}});
$('companion-filter').onchange=renderTracks;
$('companion-sleep').onchange=guard(()=>command('sleep_timer',{minutes:Number($('companion-sleep').value)}));
$('companion-refresh').onclick=guard(async()=>{const lib=await request('/v1/library');tracks=lib.tracks;renderTracks();await refresh();});
$('companion-floating').onclick=guard(()=>command('floating_toggle'));
$('companion-stop').onclick=guard(()=>command('stop'));
$('companion-play').onclick=guard(()=>command(snapshot?.status==='playing'?'pause':'play'));
$('companion-previous').onclick=guard(()=>command('previous'));$('companion-next').onclick=guard(()=>command('next'));
$('companion-back15').onclick=guard(()=>command('skip',{direction:-1}));$('companion-forward15').onclick=guard(()=>command('skip',{direction:1}));
$('companion-skip').onchange=guard(()=>command('skip_interval',{value:Number($('companion-skip').value)}));
$('companion-seek').onchange=guard(()=>command('seek',{value:Number($('companion-seek').value)}));
$('companion-speed').onchange=guard(()=>command('speed',{value:Number($('companion-speed').value)}));$('companion-volume').onchange=guard(()=>command('volume',{value:Number($('companion-volume').value)}));
$('companion-auto').onchange=guard(()=>command('autonext',{value:$('companion-auto').checked}));$('companion-search').oninput=renderTracks;
$('companion-mark').onclick=guard(async()=>{if(!snapshot?.currentId)throw Error('בחרו שיעור תחילה.');snapshot=await request('/v1/state');const name=$('companion-mark-name').value.trim()||'סימנייה';(marks[snapshot.currentId]||=[]).push({id:crypto.randomUUID(),position:snapshot.position,name});await saveMarks();$('companion-mark-name').value='';renderMarks();});
if(window.Otzaria){window.Otzaria.on('plugin.boot',guard(async()=>{hostReady=true;const r=await window.Otzaria.call('storage.get',{key:'companion-bookmarks-v1'});if(!r.success)throw Error('טעינת הסימניות נכשלה.');marks=r.data||{};const connection=await window.Otzaria.call('storage.get',{key:'companion-connection-v1'});if(connection.success&&typeof connection.data?.token==='string'&&connection.data.token){$('companion-token').value=connection.data.token;$('companion-remember').checked=true;try{await connect();}catch(e){tell('החיבור השמור אינו זמין. הפעילו את הנגן או הדביקו קוד צימוד עדכני. '+e.message,true);}}}));window.Otzaria.on('plugin.suspended',()=>{visible=false;});window.Otzaria.on('plugin.resumed',()=>{visible=!section.hidden;refresh();});}
$('open-companion').click();
})();
