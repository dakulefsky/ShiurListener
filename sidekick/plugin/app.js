(function(){
'use strict';
const $=id=>document.getElementById(id), C=ShiurCore;
const engine=new WebAudioPlayback($('audio'));
let state=C.fresh(),view='all',query='',ready=false,host=false,loadedId=null,loadRevision=0,queue=[],lastSaved=0,saveChain=Promise.resolve(),importing=false;
const previewFiles=new Map();
const status=(message,error=false)=>{$('status').textContent=message;$('status').classList.toggle('error',error);};
async function rpc(method,args={}){const r=await window.Otzaria.call(method,args);if(!r || !r.success)throw new Error(r?.error?.message||`הפעולה נכשלה: ${method}`);return r.data;}
function safe(fn){return (...args)=>Promise.resolve().then(()=>fn(...args)).catch(e=>status(e.message||String(e),true));}
function save(){
  const snapshot=JSON.parse(JSON.stringify(state));
  saveChain=saveChain.catch(()=>{}).then(()=>host?rpc('storage.set',{key:'library-v1',value:snapshot}):localStorage.setItem('shiur-player-v1',JSON.stringify(snapshot)));
  saveChain.catch(()=>status('שמירת הנתונים נכשלה. בדקו את הרשאות האחסון של התוסף.',true));
  return saveChain;
}
function current(){return state.tracks.find(t=>t.id===state.currentId);}
function capture(){const t=state.tracks.find(t=>t.id===loadedId);if(t){t.position=engine.position;if(engine.duration)t.duration=engine.duration;}}
const applyTheme=ShiurUI.applyTheme;
function button(text,fn,cls){const b=document.createElement('button');b.textContent=text;b.onclick=safe(fn);if(cls)b.className=cls;return b;}
function ask(title,initial=''){
  return new Promise(resolve=>{const d=$('text-dialog');$('dialog-title').textContent=title;$('dialog-input').value=initial;d.returnValue='cancel';d.addEventListener('close',()=>resolve(d.returnValue==='save'?$('dialog-input').value.trim():null),{once:true});d.showModal();$('dialog-input').focus();});
}
function confirmDelete(title){return new Promise(resolve=>{const d=$('confirm-dialog');$('confirm-title').textContent=title;d.returnValue='cancel';d.addEventListener('close',()=>resolve(d.returnValue==='yes'),{once:true});d.showModal();});}
function changeView(id){view=id;render();}
function render(){renderNavigation();renderTracks();renderPlayer();}
function renderNavigation(){
  const nav=$('navigation');nav.replaceChildren();
  [['all','כל השיעורים'],['continue','המשך האזנה'],...state.playlists.map(p=>[p.id,p.name])].forEach(([id,name])=>{
    const b=button(name,()=>changeView(id),view===id?'active':'');b.setAttribute('aria-current',view===id?'page':'false');b.insertAdjacentHTML('afterbegin',ShiurUI.icon(id==='all'?'library':id==='continue'?'history':'list'));nav.append(b);
  });
  const p=state.playlists.find(p=>p.id===view);
  $('view-title').textContent=p?p.name:view==='continue'?'המשך האזנה':'כל השיעורים';
  $('rename-playlist').hidden=$('delete-playlist').hidden=!p;
}
function filtered(){const q=query.toLocaleLowerCase();return C.viewTracks(state,view).filter(t=>(t.name+' '+(t.source||'')).toLocaleLowerCase().includes(q));}
function renderTracks(){
  const list=$('tracks');list.replaceChildren();const tracks=filtered();$('track-count').textContent=`${tracks.length} שיעורים`;
  if(!tracks.length){const empty=document.createElement('div');empty.className='empty';const title=document.createElement('strong');title.textContent=state.tracks.length?'אין שיעורים בתצוגה הזו':'כל שיעור מתחיל בהקשבה';const text=document.createElement('p');text.textContent=state.tracks.length?'אפשר לשנות את החיפוש או להוסיף שיעורים לרשימה.':'הוסיפו קובץ שמע או תיקייה כדי להתחיל.';empty.append(title,text);list.append(empty);return;}
  for(const t of tracks){
    const row=document.createElement('article');row.className='track'+(state.currentId===t.id?' selected':'');row.dataset.trackId=t.id;
    const info=document.createElement('div');const title=button(t.name,()=>selectTrack(t.id,true,tracks.map(t=>t.id)),'track-title');title.dir='auto';
    const source=document.createElement('small');source.textContent=t.source||'קובץ מקומי';source.dir='auto';
    const progress=document.createElement('small');progress.dir='ltr';progress.textContent=t.position?`${C.format(t.position)}${t.duration?' / '+C.format(t.duration):''}`:'טרם הושמע';
    info.append(title,source,progress);
    if(t.duration){const bar=document.createElement('div');bar.className='progress';const fill=document.createElement('span');fill.style.width=Math.min(100,t.position/t.duration*100)+'%';bar.append(fill);info.append(bar);}
    const actions=document.createElement('div');actions.className='actions';
    const select=document.createElement('select');select.setAttribute('aria-label',`הוספת ${t.name} לתיקייה`);const placeholder=new Option('＋ לתיקייה','');select.add(placeholder);state.playlists.forEach(p=>select.add(new Option(p.name,p.id)));select.disabled=!state.playlists.length;
    select.onchange=safe(async()=>{const p=state.playlists.find(p=>p.id===select.value);if(p&&!p.trackIds.includes(t.id)){p.trackIds.push(t.id);await save();status('השיעור נוסף לתיקייה.');}select.value='';});actions.append(select);
    actions.append(button(view!=='all'&&view!=='continue'?'הסרה מהתיקייה':'הסרה',async()=>{
      if(view!=='all'&&view!=='continue'){const p=state.playlists.find(p=>p.id===view);p.trackIds=p.trackIds.filter(id=>id!==t.id);}
      else {if(!await confirmDelete(`להסיר את „${t.name}” מהספרייה?`))return;
        if(state.currentId===t.id){++loadRevision;loadedId=null;engine.clear();}
        C.removeTrack(state,t.id);queue=queue.filter(id=>id!==t.id);const url=previewFiles.get(t.id);if(url){URL.revokeObjectURL(url);previewFiles.delete(t.id);}
      }
      await save();render();
    },'remove'));
    row.append(info,actions);list.append(row);
  }
}
function renderPlayer(){
  const t=current();$('current-title').textContent=t?t.name:'בחרו שיעור להאזנה';$('current-source').textContent=t?(t.source||'קובץ מקומי'):'השיעורים נשארים במכשיר שלכם';
  $('skip-interval').value=String(state.skipSeconds);$('back').textContent='−'+state.skipSeconds;$('forward').textContent='+'+state.skipSeconds;$('back').setAttribute('aria-label',`אחורה ${state.skipSeconds} שניות`);$('forward').setAttribute('aria-label',`קדימה ${state.skipSeconds} שניות`);$('speed').value=String(state.speed);$('volume').value=state.volume;$('autonext').checked=state.autoNext;
  ['play','previous','next','back','forward','bookmark'].forEach(id=>$(id).disabled=!ready||!t);
  renderTimeline();renderBookmarks();
}
function renderTimeline(){
  const t=current(),active=t&&loadedId===t.id;const position=active?engine.position:t?.position||0,duration=active?engine.duration:t?.duration||0;
  $('position').textContent=C.format(position);$('duration').textContent=C.format(duration);$('seek').max=duration;$('seek').value=position;$('seek').disabled=!active||!duration;
  ShiurUI.setPlay($('play'),engine.paused);
}
function renderBookmarks(){
  const box=$('bookmarks');box.replaceChildren();const t=current();
  if(!t?.bookmarks.length){const p=document.createElement('p');p.className='muted';p.textContent='אפשר לשמור נקודות חשובות תוך כדי האזנה.';box.append(p);return;}
  for(const mark of [...t.bookmarks].sort((a,b)=>a.position-b.position)){
    const row=document.createElement('div');row.className='bookmark-row';row.append(button(`${C.format(mark.position)} · ${mark.label}`,async()=>{if(loadedId!==t.id){await selectTrack(t.id,false);if(loadedId!==t.id)return;}engine.seek(mark.position);capture();await save();renderTimeline();}));
    const del=button('×',async()=>{t.bookmarks=t.bookmarks.filter(b=>b.id!==mark.id);await save();renderBookmarks();});del.setAttribute('aria-label',`מחיקת סימנייה ${mark.label}`);row.append(del);box.append(row);
  }
}
async function resolveTrack(t){
  if(!host){const url=previewFiles.get(t.id);if(!url)throw new Error('בחרו שוב את קובץ השמע כדי לחדש את הגישה אליו בתצוגת הדפדפן.');return url;}
  if(t.folderToken){const file=await rpc('fs.openFolderFile',{folderToken:t.folderToken,path:t.relativePath});return file.url;}
  return (await rpc('fs.resolveFileUrl',{token:t.token})).url;
}
async function selectTrack(id,autoplay=false,newQueue){
  const t=state.tracks.find(t=>t.id===id);if(!t)return false;
  capture();const revision=++loadRevision;engine.cancel();engine.pause();loadedId=null;state.currentId=id;
  if(newQueue)queue=[...newQueue];else if(!queue.includes(id))queue=C.viewTracks(state,view).map(t=>t.id);
  render();status('טוען שיעור…');save();
  try{
    const url=await resolveTrack(t);if(revision!==loadRevision)return false;
    const loaded=await engine.load(url,t.position,state.speed);if(!loaded||revision!==loadRevision)return false;
    loadedId=id;engine.setVolume(state.volume);t.duration=engine.duration;renderPlayer();await save();
    if(revision!==loadRevision)return false;if(autoplay)await engine.play();status('');return true;
  }catch(e){if(revision===loadRevision){loadedId=null;status(e.message,true);renderPlayer();}return false;}
}
async function adjacent(delta){const id=state.currentId;let ids=queue.filter(id=>state.tracks.some(t=>t.id===id));if(!ids.includes(id))ids=C.viewTracks(state,view).map(t=>t.id);const next=ids[ids.indexOf(id)+delta];if(next)await selectTrack(next,true,ids);}
async function addFiles(files){
  let added=0;
  for(const file of files){
    if(!C.extensions.includes(file.name.split('.').pop().toLowerCase()))continue;
    const id=`preview:${file.webkitRelativePath||file.name}:${file.size}:${file.lastModified}`;
    if(previewFiles.has(id))URL.revokeObjectURL(previewFiles.get(id));previewFiles.set(id,URL.createObjectURL(file));
    if(!state.tracks.some(t=>t.id===id)){state.tracks.push({id,name:file.name,source:file.webkitRelativePath||'קובץ מקומי',position:0,duration:0,bookmarks:[]});added++;}
  }
  await save();render();status(added?`נוספו ${added} שיעורים.`:'הגישה לקבצים עודכנה.');
}
function choosePreview(folder){const input=document.createElement('input');input.type='file';input.accept='audio/*,'+C.extensions.map(x=>'.'+x).join(',');input.multiple=true;if(folder)input.webkitdirectory=true;input.onchange=safe(()=>addFiles([...input.files]));input.click();}
async function addFile(){
  if(!host){choosePreview(false);return;}
  const f=await rpc('fs.pickUserFile',{title:'בחירת שיעור',extensions:C.extensions});if(f.cancelled)return;
  const id='file:'+f.token;
  if(!state.tracks.some(t=>t.id===id||t.token===f.token))state.tracks.push({id,token:f.token,name:f.name,source:'קובץ מקומי',position:0,duration:0,bookmarks:[]});
  await save();render();status('השיעור נוסף לספרייה.');
}
async function addFolder(){
  if(!host){choosePreview(true);return;}if(importing)return;
  const folder=await rpc('fs.pickUserFolder',{title:'בחירת תיקיית שיעורים'});if(folder.cancelled)return;
  importing=true;$('add-folder').disabled=true;let count=0,truncated=false;
  try{
    const pending=[''];const seen=new Set();
    while(pending.length){
      const path=pending.shift();if(seen.has(path))continue;seen.add(path);
      const data=await rpc('fs.listUserFolder',{folderToken:folder.folderToken,path,extensions:C.extensions});truncated=truncated||data.truncated;
      for(const entry of data.entries){
        if(entry.type==='dir'){pending.push(entry.path);continue;}
        if(!C.extensions.includes(entry.name.split('.').pop().toLowerCase()))continue;
        const id=`folder:${folder.folderToken}:${entry.path}`;
        if(!state.tracks.some(t=>t.id===id)){state.tracks.push({id,folderToken:folder.folderToken,relativePath:entry.path,name:entry.name,source:folder.name+' / '+entry.path,position:0,duration:0,bookmarks:[]});count++;}
      }
      status(`נוספו ${count} שיעורים…`);
    }
    status(`נוספו ${count} שיעורים.${truncated?' חלק מהתיקיות מכילות יותר מ־2,000 פריטים; הרשימה חלקית.':''}`);
  }finally{importing=false;$('add-folder').disabled=false;await save();render();}
}
function wire(){
  $('add-file').onclick=safe(addFile);$('add-folder').onclick=safe(addFolder);
  $('search').oninput=()=>{query=$('search').value;renderTracks();};
  $('new-playlist').onclick=safe(async()=>{const name=await ask('תיקייה חדשה');if(!name)return;const p={id:crypto.randomUUID(),name,trackIds:[]};state.playlists.push(p);view=p.id;await save();render();});
  $('rename-playlist').onclick=safe(async()=>{const p=state.playlists.find(p=>p.id===view);if(!p)return;const name=await ask('שינוי שם התיקייה',p.name);if(name){p.name=name;await save();render();}});
  $('delete-playlist').onclick=safe(async()=>{const p=state.playlists.find(p=>p.id===view);if(p&&await confirmDelete(`למחוק את התיקייה „${p.name}”?`)){state.playlists=state.playlists.filter(x=>x.id!==p.id);view='all';await save();render();}});
  $('play').onclick=safe(async()=>{const t=current();if(!t)return;if(loadedId!==t.id){await selectTrack(t.id,true);return;}if(engine.paused)await engine.play();else{engine.pause();capture();await save();}});
  $('previous').onclick=safe(()=>adjacent(-1));$('next').onclick=safe(()=>adjacent(1));
  $('back').onclick=safe(async()=>{engine.seek(engine.position-state.skipSeconds);capture();await save();renderTimeline();});$('forward').onclick=safe(async()=>{engine.seek(engine.position+state.skipSeconds);capture();await save();renderTimeline();});
  $('seek').oninput=safe(async()=>{engine.seek(Number($('seek').value));capture();await save();renderTimeline();});
  $('skip-interval').onchange=safe(async()=>{state.skipSeconds=Number($('skip-interval').value);await save();renderPlayer();});
  $('speed').onchange=safe(async()=>{state.speed=Number($('speed').value);engine.setSpeed(state.speed);await save();});
  $('volume').oninput=safe(async()=>{state.volume=Number($('volume').value);engine.setVolume(state.volume);await save();});
  $('autonext').onchange=safe(async()=>{state.autoNext=$('autonext').checked;await save();});
  $('bookmark').onclick=safe(async()=>{capture();const t=current();if(!t)return;const position=t.position;const label=await ask('סימנייה חדשה',`סימנייה ב־${C.format(position)}`);if(!label)return;t.bookmarks.push({id:crypto.randomUUID(),position,label});await save();renderBookmarks();});
  engine.on('timeupdate',()=>{capture();renderTimeline();if(Date.now()-lastSaved>1000){lastSaved=Date.now();save();}});
  engine.on('play',renderTimeline);engine.on('pause',()=>{capture();save();renderTimeline();renderTracks();});
  engine.on('ended',safe(async()=>{capture();await save();renderTracks();if(state.autoNext)await adjacent(1);}));
  engine.on('error',()=>{if(loadedId)status('ניגון השיעור נכשל. בדקו שהקובץ זמין ושהפורמט נתמך במערכת.',true);});
  document.addEventListener('keydown',event=>{
    if(!ready||document.querySelector('main').hidden||event.ctrlKey||event.altKey||event.metaKey||event.isComposing||event.repeat||document.querySelector('dialog[open]'))return;
    if(event.target.closest('input,select,textarea,button,[contenteditable="true"],summary'))return;
    const key=/^Key[A-Z]$/.test(event.code)?event.code.slice(3).toLowerCase():event.key.toLowerCase();let action;
    if(event.code==='Space')action=()=>$('play').click();
    else if(key==='arrowleft')action=()=>event.shiftKey?$('previous').click():$('back').click();
    else if(key==='arrowright')action=()=>event.shiftKey?$('next').click():$('forward').click();
    else if(['1','2','3'].includes(key))action=()=>{$('skip-interval').value={1:'10',2:'15',3:'60'}[key];$('skip-interval').dispatchEvent(new Event('change'));};
    else if(['+','=','-','_'].includes(key))action=()=>{const rates=[.75,1,1.25,1.5,1.75,2];$('speed').value=String(rates[Math.max(0,Math.min(5,rates.indexOf(state.speed)+(['-','_'].includes(key)?-1:1)))]);$('speed').dispatchEvent(new Event('change'));};
    else if(key==='b')action=()=>$('bookmark').click();else if(key==='f')action=()=>$('search').focus();else if(key==='n')action=()=>$('new-playlist').click();
    if(action){event.preventDefault();action();}
  });
  window.addEventListener('pagehide',()=>{capture();save();});
}
async function initialize(payload){
  if(ready)return;host=!!window.Otzaria;applyTheme(payload?.theme);
  try{const saved=host?await rpc('storage.get',{key:'library-v1'}):JSON.parse(localStorage.getItem('shiur-player-v1')||'null');state=C.normalize(saved);}
  catch(e){status('לא ניתן לטעון את הספרייה השמורה: '+e.message,true);return;}
  ready=true;wire();$('preview-note').hidden=host;$('add-folder').disabled=false;$('add-file').disabled=false;$('new-playlist').disabled=false;
  engine.setVolume(state.volume);render();status('');
  // Restore the selection and position, never start sound automatically on boot.
  if(state.currentId)await selectTrack(state.currentId,false);
}
$('add-file').disabled=$('add-folder').disabled=$('new-playlist').disabled=true;
render();
if(window.Otzaria){
  window.Otzaria.on('plugin.boot',safe(initialize));window.Otzaria.on('theme.changed',applyTheme);
  window.Otzaria.on('plugin.suspended',()=>{++loadRevision;engine.cancel();engine.pause();capture();save();status('הניגון הושהה. לחצו על ניגון כדי להמשיך.');});
  window.Otzaria.on('plugin.resumed',renderPlayer);
}else initialize().catch(e=>status(e.message,true));
})();
