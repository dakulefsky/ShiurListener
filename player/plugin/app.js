(function(){
'use strict';
const $=id=>document.getElementById(id), C=ShiurCore;
const engine=new VisiblePlayback(document.getElementById('audio'));
let state=C.fresh(),view='all',query='',ready=false,loadedId=null,loadRevision=0,queue=[],saveChain=Promise.resolve(),importing=false,loading=false,initializing=false;
const status=(message,error=false)=>{$('status').textContent=message;$('status').classList.toggle('error',error);$('recovery').hidden=!error;if(error){$('error-detail').textContent='נגן שיעורים 1.4.3\n'+message;$('player-state').textContent='נדרשת בדיקה';}};
async function rpc(method,args={}){const r=await window.Otzaria.call(method,args);if(!r || !r.success)throw new Error(r?.error?.message||`הפעולה נכשלה: ${method}`);return r.data;}
function safe(fn){return (...args)=>Promise.resolve().then(()=>fn(...args)).catch(e=>status(e.message||String(e),true));}
function save(){
  const snapshot=JSON.parse(JSON.stringify(state));
  saveChain=saveChain.catch(()=>{}).then(()=>rpc('storage.set',{key:'library-v1',value:snapshot}));
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
    const info=document.createElement('div');const title=button(t.name,()=>selectTrack(t.id,false,tracks.map(t=>t.id)),'track-title');title.dir='auto';
    const source=document.createElement('small');source.textContent=t.source||'קובץ מקומי';source.dir='auto';
    const progress=document.createElement('small');progress.className='track-progress';progress.textContent=C.progressLabel(t);
    info.append(title,source,progress);
    if(t.duration){const bar=document.createElement('div');bar.className='progress';const fill=document.createElement('span');fill.style.width=Math.min(100,t.position/t.duration*100)+'%';bar.append(fill);info.append(bar);}
    const actions=document.createElement('details');actions.className='actions track-actions';const menu=document.createElement('summary');menu.textContent='אפשרויות';actions.append(menu);
    const select=document.createElement('select');select.setAttribute('aria-label',`הוספת ${t.name} לתיקייה`);const placeholder=new Option('＋ לתיקייה','');select.add(placeholder);state.playlists.forEach(p=>select.add(new Option(p.name,p.id)));select.disabled=!state.playlists.length;
    select.onchange=safe(async()=>{const p=state.playlists.find(p=>p.id===select.value);if(p&&!p.trackIds.includes(t.id)){p.trackIds.push(t.id);await save();status('השיעור נוסף לתיקייה.');}select.value='';});actions.append(select);
    {
      const reset=button('מההתחלה',async()=>{
        if(!await confirmDelete(`לאפס את מיקום ההאזנה של „${t.name}”?`))return;
        await engine.send('reset_progress',{id:t.id});mergeHostProgress();capture();await save();render();
      },'reset-progress');reset.hidden=!(t.position>0||t.completed);reset.setAttribute('aria-label',`איפוס מיקום ההאזנה של ${t.name}`);actions.append(reset);
    }
    actions.append(button(view!=='all'&&view!=='continue'?'הסרה מהתיקייה':'הסרה',async()=>{
      if(view!=='all'&&view!=='continue'){const p=state.playlists.find(p=>p.id===view);p.trackIds=p.trackIds.filter(id=>id!==t.id);}
      else {if(!await confirmDelete(`להסיר את „${t.name}” מהספרייה?`))return;
        if(state.currentId===t.id){++loadRevision;loadedId=null;await engine.clear();}
        C.removeTrack(state,t.id);queue=queue.filter(id=>id!==t.id);
      }
      await save();render();
    },'remove'));
    row.append(info,actions);list.append(row);
  }
}
function syncTrackProgress(){
  const rows=[...$('tracks').querySelectorAll('.track')],tracks=filtered();
  if(rows.length!==tracks.length||rows.some((row,index)=>row.dataset.trackId!==tracks[index].id)){renderTracks();return;}
  rows.forEach((row,index)=>{
    const track=tracks[index];row.querySelector('.track-progress').textContent=C.progressLabel(track);
    const fill=row.querySelector('.progress span');if(fill&&track.duration)fill.style.width=Math.min(100,track.position/track.duration*100)+'%';
    row.querySelector('.reset-progress').hidden=!(track.position>0||track.completed);
  });
}
function renderPlayer(){
  const t=current();$('current-title').textContent=t?t.name:'בחרו שיעור להאזנה';$('current-source').textContent=t?(t.source||'קובץ מקומי'):'השיעורים נשארים במכשיר שלכם';
  $('skip-interval').value=String(state.skipSeconds);$('back').textContent='−'+state.skipSeconds;$('forward').textContent='+'+state.skipSeconds;$('back').setAttribute('aria-label',`אחורה ${state.skipSeconds} שניות`);$('forward').setAttribute('aria-label',`קדימה ${state.skipSeconds} שניות`);$('speed').value=String(state.speed);$('volume').value=state.volume;$('autonext').checked=state.autoNext;
  ['play','previous','next','back','forward','bookmark'].forEach(id=>$(id).disabled=!ready||!t||loading);
  $('player-state').textContent=loading?'טוען את השיעור…':!ready?'מתחבר לאוצריא':!t?'מוכנים להתחיל':loadedId!==t.id?'לחצו על ניגון לטעינה מחדש':engine.paused?'מוכן לניגון':'מתנגן עכשיו';
  $('welcome').hidden=state.tracks.length>0;
  renderTimeline();renderBookmarks();
}
function renderTimeline(){
  const t=current(),active=t&&loadedId===t.id;const position=active?engine.position:t?.position||0,duration=active?engine.duration:t?.duration||0;
  if(!loading&&ready&&active&&!$('status').classList.contains('error'))$('player-state').textContent=engine.paused?'מוכן לניגון':'מתנגן עכשיו';
  if(!engine.state.sleepRemaining)$('sleep-timer').value='0';
  $('sleep-countdown').textContent=engine.state.sleepRemaining?`הניגון יושהה בעוד ${C.format(engine.state.sleepRemaining)}`:'';
  const saved=engine.state.currentId===t?.id?engine.state.savedPositionMs:null;
  $('resume-info').textContent=!t?'':saved!=null&&engine.state.savedAt?`המיקום נשמר: ${C.format(saved/1000)}`:t.position>0?`המשך מהמיקום השמור: ${C.format(t.position)}`:'המיקום יישמר בזמן ההאזנה';
  $('position').textContent=C.format(position);$('duration').textContent=C.format(duration);$('seek').max=duration;$('seek').value=position;$('seek').disabled=!active||!duration;
  ShiurUI.setPlay($('play'),engine.paused);
}
function renderBookmarks(){
  const box=$('bookmarks');box.replaceChildren();const t=current();
  if(!t?.bookmarks.length){const p=document.createElement('p');p.className='muted';p.textContent='אפשר לשמור נקודות חשובות תוך כדי האזנה.';box.append(p);return;}
  for(const mark of [...t.bookmarks].sort((a,b)=>a.position-b.position)){
    const row=document.createElement('div');row.className='bookmark-row';row.append(button(`${C.format(mark.position)} · ${mark.label}`,async()=>{if(loadedId!==t.id){await selectTrack(t.id,false);if(loadedId!==t.id)return;}await engine.seek(mark.position);capture();await save();renderTimeline();}));
    const del=button('×',async()=>{t.bookmarks=t.bookmarks.filter(b=>b.id!==mark.id);await save();renderBookmarks();});del.setAttribute('aria-label',`מחיקת סימנייה ${mark.label}`);row.append(del);box.append(row);
  }
}
function source(t){return {id:t.id,title:t.name,...(t.folderToken?{folderToken:t.folderToken,path:t.relativePath}:{token:t.token})};}
async function resolveTrack(t){return source(t);}
function mergeHostProgress(){for(const t of state.tracks){const progress=engine.state.positions?.[t.id];if(progress){t.position=(progress.positionMs||0)/1000;t.duration=(progress.durationMs||0)/1000;t.completed=progress.completed===true;t.lastListenedAt=progress.lastListenedAt||0;}}}

async function selectTrack(id,autoplay=false,newQueue){
  const t=state.tracks.find(t=>t.id===id);if(!t)return false;
  capture();const revision=++loadRevision;engine.cancel();await engine.pause();loadedId=null;state.currentId=id;loading=true;
  if(newQueue)queue=[...newQueue];else if(!queue.includes(id))queue=C.viewTracks(state,view).map(t=>t.id);
  render();status('טוען שיעור…');save();
  try{
    engine.queue=queue.map(id=>state.tracks.find(t=>t.id===id)).filter(Boolean).map(source);
    const url=await resolveTrack(t);if(revision!==loadRevision)return false;
    const loaded=await engine.load(url,t.position,state.speed);if(!loaded||revision!==loadRevision)return false;
    loadedId=id;loading=false;await engine.setVolume(state.volume);t.duration=engine.duration;renderPlayer();await save();
    if(revision!==loadRevision)return false;if(autoplay)await engine.play();status(autoplay?'':'השיעור מוכן. לחצו על ניגון.');return true;
  }catch(e){if(revision===loadRevision){loadedId=null;loading=false;renderPlayer();status(e.message,true);}return false;}
}
async function adjacent(delta){const id=state.currentId;let ids=queue.filter(id=>state.tracks.some(t=>t.id===id));if(!ids.includes(id))ids=C.viewTracks(state,view).map(t=>t.id);const next=ids[ids.indexOf(id)+delta];if(next)await selectTrack(next,false,ids);}
async function addFile(){
  const f=await rpc('fs.pickUserFile',{title:'בחירת שיעור',extensions:C.extensions});if(f.cancelled)return;
  const id='file:'+f.token;
  if(!state.tracks.some(t=>t.id===id||t.token===f.token))state.tracks.push({id,token:f.token,name:f.name,source:'קובץ מקומי',position:0,duration:0,bookmarks:[]});
  await save();view='all';query='';$('search').value='';render();await selectTrack(id,false);$('play').focus();
}
async function addFolder(){
  if(importing)return;
  const folder=await rpc('fs.pickUserFolder',{title:'בחירת תיקיית שיעורים'});if(folder.cancelled)return;
  importing=true;$('add-folder').disabled=true;let count=0,truncated=false,firstAdded=null;
  try{
    const pending=[''];const seen=new Set();
    while(pending.length){
      const path=pending.shift();if(seen.has(path))continue;seen.add(path);
      const data=await rpc('fs.listUserFolder',{folderToken:folder.folderToken,path,extensions:C.extensions});truncated=truncated||data.truncated;
      for(const entry of data.entries){
        if(entry.type==='dir'){pending.push(entry.path);continue;}
        if(!C.extensions.includes(entry.name.split('.').pop().toLowerCase()))continue;
        const id=`folder:${folder.folderToken}:${entry.path}`;
        if(!state.tracks.some(t=>t.id===id)){state.tracks.push({id,folderToken:folder.folderToken,relativePath:entry.path,name:entry.name,source:folder.name+' / '+entry.path,position:0,duration:0,bookmarks:[]});count++;firstAdded??=id;}
      }
      status(`נוספו ${count} שיעורים…`);
    }
    status(`נוספו ${count} שיעורים.${truncated?' חלק מהתיקיות מכילות יותר מ־2,000 פריטים; הרשימה חלקית.':''}`);
  }finally{importing=false;$('add-folder').disabled=false;await save();render();}
  if(firstAdded&&!loadedId){view='all';render();await selectTrack(firstAdded,false);$('play').focus();}
}
function wire(){
  $('retry-setup').onclick=safe(async()=>{if(!ready)await initialize();else if(current())await selectTrack(current().id,false);});
  $('sound-check').onclick=()=>{if(!engine.paused)engine.pause().catch(error=>status(error.message,true));const tone=$('sound-check-audio');tone.currentTime=0;const action=tone.play();action.then(()=>{$('sound-check-result').textContent='צליל הבדיקה מופעל. אם לא שומעים, בדקו את עוצמת השמע ואת התקן הפלט של אוצריא.';}).catch(error=>{$('sound-check-result').textContent='אוצריא לא הצליחה להפעיל גם את צליל הבדיקה: '+error.message;});};
  $('welcome-add').onclick=()=>$('add-file').click();
  $('compact-player').onclick=()=>{const compact=document.body.classList.toggle('compact-mode');$('compact-player').textContent=compact?'ספריית השיעורים':'נגן קטן';$('compact-player').setAttribute('aria-pressed',String(compact));};
  $('reader-controls').onclick=()=>{const help=document.querySelector('.keyboard-help');help.open=true;help.scrollIntoView({behavior:'smooth',block:'nearest'});};
  $('sleep-timer').onchange=safe(()=>engine.sleep(Number($('sleep-timer').value)));
  $('add-file').onclick=safe(addFile);$('add-folder').onclick=safe(addFolder);
  $('search').oninput=()=>{query=$('search').value;renderTracks();};
  $('new-playlist').onclick=safe(async()=>{const name=await ask('תיקייה חדשה');if(!name)return;const p={id:C.uuid(),name,trackIds:[]};state.playlists.push(p);view=p.id;await save();render();});
  $('rename-playlist').onclick=safe(async()=>{const p=state.playlists.find(p=>p.id===view);if(!p)return;const name=await ask('שינוי שם התיקייה',p.name);if(name){p.name=name;await save();render();}});
  $('delete-playlist').onclick=safe(async()=>{const p=state.playlists.find(p=>p.id===view);if(p&&await confirmDelete(`למחוק את התיקייה „${p.name}”?`)){state.playlists=state.playlists.filter(x=>x.id!==p.id);view='all';await save();render();}});
  $('play').onclick=()=>{
    const t=current();if(!t)return;
    $('sound-check-audio').pause();
    if(loadedId!==t.id){safe(()=>selectTrack(t.id,false))();return;}
    const action=engine.paused?engine.play():engine.pause();
    action.then(()=>{status('');capture();renderTimeline();return save();}).catch(error=>status(error.message,true));
  };
  $('previous').onclick=safe(()=>adjacent(-1));$('next').onclick=safe(()=>adjacent(1));
  const skip=async direction=>{const t=current();if(!t)return;if(loadedId!==t.id&&!await selectTrack(t.id,false))return;await engine.seek(engine.position+direction*state.skipSeconds);capture();await save();renderTimeline();};
  $('back').onclick=safe(()=>skip(-1));$('forward').onclick=safe(()=>skip(1));
  $('seek').oninput=safe(async()=>{await engine.seek(Number($('seek').value));capture();await save();renderTimeline();});
  $('skip-interval').onchange=safe(async()=>{state.skipSeconds=Number($('skip-interval').value);await engine.setSkip(state.skipSeconds);await save();renderPlayer();});
  $('speed').onchange=safe(async()=>{state.speed=Number($('speed').value);await engine.setSpeed(state.speed);await save();});
  $('volume').oninput=safe(async()=>{state.volume=Number($('volume').value);await engine.setVolume(state.volume);await save();});
  $('autonext').onchange=safe(async()=>{state.autoNext=$('autonext').checked;await engine.setAutoNext(state.autoNext);await save();});
  $('bookmark').onclick=safe(async()=>{capture();const t=current();if(!t)return;const position=t.position;const label=await ask('סימנייה חדשה',`סימנייה ב־${C.format(position)}`);if(!label)return;t.bookmarks.push({id:C.uuid(),position,label});await save();renderBookmarks();});
  engine.on('statechange',()=>{const s=engine.state;state.speed=s.speed;state.volume=s.volume;state.skipSeconds=s.skipSeconds;state.autoNext=s.autoNext;renderPlayer();});
  engine.on('trackchange',()=>{mergeHostProgress();const t=state.tracks.find(t=>t.id===engine.state.currentId);if(t){state.currentId=t.id;loadedId=engine.local.loaded?t.id:null;render();}});
  engine.on('timeupdate',()=>{mergeHostProgress();capture();renderTimeline();syncTrackProgress();});
  engine.on('play',renderTimeline);engine.on('pause',()=>{capture();save();renderTimeline();renderTracks();});
  engine.on('ended',safe(async()=>{capture();await save();renderTracks();if(state.autoNext&&!engine.handlesQueue)await adjacent(1);}));
  engine.on('error',()=>{status(engine.error||'פעולת הנגן נכשלה.',true);});
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
  window.addEventListener('pagehide',()=>{if(ready){capture();save();}});
}
async function initialize(payload){
  if(ready||initializing)return;initializing=true;applyTheme(payload?.theme);status('פותח את הספרייה…');
  try{
  try{const saved=await rpc('storage.get',{key:'library-v1'});state=C.normalize(saved);}
  catch(e){throw Error('לא ניתן לטעון את הספרייה השמורה: '+e.message);}
  const hostState=await engine.init();mergeHostProgress();state.speed=hostState.speed||state.speed;state.volume=hostState.volume??state.volume;state.skipSeconds=hostState.skipSeconds||state.skipSeconds;state.autoNext=hostState.autoNext===true;if(state.tracks.some(t=>t.id===hostState.currentId))state.currentId=hostState.currentId;
  ready=true;$('add-folder').disabled=false;$('add-file').disabled=false;$('new-playlist').disabled=false;$('welcome-add').disabled=false;
  // Restore the selection and position, never start sound automatically on boot.
  if(engine.local.loaded&&engine.state.currentId&&state.tracks.some(t=>t.id===engine.state.currentId))loadedId=engine.state.currentId;
  render();status(hostState.error||engine.local.restoreWarning||'',!!hostState.error);
  }catch(error){render();status(error.message+' אפשר לתקן את ההרשאה בהגדרות התוסף וללחוץ על „ניסיון נוסף”.',true);}
  finally{initializing=false;}
}
wire();
$('add-file').disabled=$('add-folder').disabled=$('new-playlist').disabled=$('welcome-add').disabled=true;
render();
if(window.Otzaria){
  window.Otzaria.on('plugin.boot',safe(initialize));window.Otzaria.on('theme.changed',applyTheme);
  window.Otzaria.on('plugin.suspended',()=>{$('sound-check-audio').pause();if(!ready){engine.local.audio.pause();return;}const pending=engine.suspend();capture();save();return pending;});
  const externalControl=safe(async payload=>{const args=ShiurProtocol.control(payload.command||payload.itemId);if(args)await engine.send(args.op,args);});
  window.Otzaria.on('app.command',externalControl);window.Otzaria.on('reader.toolbar_item_clicked',externalControl);
  window.Otzaria.on('plugin.resumed',safe(async()=>{if(!ready)return;await engine.resume();mergeHostProgress();render();}));
}else status('נגן זה מיועד להפעלה כתוסף בתוך אוצריא.',true);
})();
