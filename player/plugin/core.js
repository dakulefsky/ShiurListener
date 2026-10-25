/* Shared data helpers: no filesystem paths or expiring playback URLs are persisted. */
(function (root) {
  'use strict';
  const extensions = ['mp3','wav'];
  const fresh = () => ({version:1,tracks:[],playlists:[],currentId:null,speed:1,volume:1,autoNext:false,skipSeconds:15});
  function normalize(value) {
    const state = fresh();
    if (!value || value.version !== 1) return state;
    state.tracks = Array.isArray(value.tracks) ? value.tracks.filter(t => t && typeof t.id==='string' && typeof t.name==='string').map(t => ({...t,position:Math.max(0,Number(t.position)||0),duration:Math.max(0,Number(t.duration)||0),completed:t.completed===true||(t.completed==null&&Number(t.duration)>0&&Number(t.position)>=Number(t.duration)),lastListenedAt:Number.isFinite(t.lastListenedAt)?t.lastListenedAt:0,bookmarks:Array.isArray(t.bookmarks)?t.bookmarks:[]})) : [];
    const ids = new Set(state.tracks.map(t=>t.id));
    state.playlists = Array.isArray(value.playlists) ? value.playlists.filter(p=>p && typeof p.name==='string' && typeof p.id==='string').map(p=>({...p,trackIds:[...new Set((Array.isArray(p.trackIds)?p.trackIds:[]).filter(id=>ids.has(id)))]})) : [];
    state.currentId = ids.has(value.currentId) ? value.currentId : null;
    state.speed = [0.75,1,1.25,1.5,1.75,2].includes(value.speed)?value.speed:1;
    state.volume = Number.isFinite(value.volume)?Math.max(0,Math.min(1,value.volume)):1;
    state.autoNext = value.autoNext === true;
    state.skipSeconds = [10,15,60].includes(value.skipSeconds)?value.skipSeconds:15;
    return state;
  }
  function viewTracks(state,view) {
    if(view==='all') return state.tracks;
    if(view==='continue') return state.tracks.filter(t=>t.position>0&&!t.completed).sort((a,b)=>(b.lastListenedAt||0)-(a.lastListenedAt||0));
    const p=state.playlists.find(p=>p.id===view);
    return p?p.trackIds.map(id=>state.tracks.find(t=>t.id===id)).filter(Boolean):[];
  }
  function progressLabel(track){return track.completed?'ההאזנה הושלמה':track.position>0?`המשך מ־${format(track.position)}${track.duration?' / '+format(track.duration):''}`:'טרם הושמע';}
  function removeTrack(state,id) {
    state.tracks=state.tracks.filter(t=>t.id!==id);
    state.playlists.forEach(p=>p.trackIds=p.trackIds.filter(x=>x!==id));
    if(state.currentId===id) state.currentId=null;
  }
  function format(seconds) {
    seconds=Math.max(0,Math.floor(Number(seconds)||0));
    const h=Math.floor(seconds/3600),m=Math.floor(seconds%3600/60),s=seconds%60;
    return h?`${h}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`:`${m}:${String(s).padStart(2,'0')}`;
  }
  function uuid(){return root.crypto?.randomUUID?.()||'local-'+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2);}
  const api={extensions,fresh,normalize,viewTracks,removeTrack,format,progressLabel,uuid};
  root.ShiurCore=api;
  if(typeof module!=='undefined') module.exports=api;
})(globalThis);
