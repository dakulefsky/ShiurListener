/* Otzaria Material 3 color roles and host-injected fonts. No remote font requests. */
(function(root){
'use strict';
const icons={
 headphones:'<path d="M4 14v-3a8 8 0 0 1 16 0v3"/><rect x="3" y="12" width="5" height="9" rx="2"/><rect x="16" y="12" width="5" height="9" rx="2"/>',
 play:'<path d="m9 5 11 7-11 7Z"/>',pause:'<path d="M9 5v14M16 5v14"/>',
 previous:'<path d="M5 5v14m14-14L8 12l11 7Z"/>',next:'<path d="M19 5v14M5 5l11 7-11 7Z"/>',
 folder:'<path d="M3 7a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>',
 plus:'<path d="M12 5v14M5 12h14"/>',bookmark:'<path d="M6 4h12v17l-6-4-6 4Z"/>',
 library:'<path d="M4 4h4v16H4zm7 0h4v16h-4zm7 0 3 15"/>',
 history:'<path d="M3 10a9 9 0 1 1 1 7M3 4v6h6m3-4v6l4 2"/>',
 list:'<path d="M9 6h12M9 12h12M9 18h12M3 6h1M3 12h1M3 18h1"/>',
};
function icon(name){return `<svg class="ui-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name]||icons.headphones}</svg>`;}
function decorate(id,name){const el=document.getElementById(id);if(!el)return;const text=el.textContent.replace(/^＋\s*/, '');el.replaceChildren();el.insertAdjacentHTML('beforeend',icon(name));const label=document.createElement('span');label.textContent=text;el.append(label);}
function setPlay(el,paused){const label=paused?'ניגון':'השהיה';el.innerHTML=icon(paused?'play':'pause')+'<span>'+label+'</span>';el.setAttribute('aria-label',label);}
function applyTheme(theme){
 if(!theme?.colorScheme)return;
 root.ShiurUI.currentTheme=theme;document.dispatchEvent(new CustomEvent('shiur-theme',{detail:theme}));
 const style=document.documentElement.style;
 const keys=['primary','onPrimary','primaryContainer','onPrimaryContainer','secondary','onSecondary','secondaryContainer','onSecondaryContainer','surface','onSurface','onSurfaceVariant','surfaceContainerLowest','surfaceContainerLow','surfaceContainer','surfaceContainerHigh','surfaceContainerHighest','outline','outlineVariant','error','onError','errorContainer','onErrorContainer','shadow','scrim'];
 for(const key of keys){if(theme.colorScheme[key])style.setProperty('--color-'+key.replace(/[A-Z]/g,c=>'-'+c.toLowerCase()),theme.colorScheme[key]);else style.removeProperty('--color-'+key.replace(/[A-Z]/g,c=>'-'+c.toLowerCase()));}
 style.colorScheme=theme.mode==='dark'?'dark':'light';
 document.body.classList.toggle('dark-mode',theme.mode==='dark');
 const t=theme.typography||{};
 style.setProperty('--font-ui',t.uiFontFamily?`${JSON.stringify(t.uiFontFamily)},'Rubik',system-ui,sans-serif`:"'Rubik',system-ui,sans-serif");
 if(t.fontFamily)style.setProperty('--font-main',`${JSON.stringify(t.fontFamily)},'David',serif`);
 style.setProperty('--font-size-base',(Math.max(15,Math.min(30,Number(t.fontSize)||18)))+'px');
}
function enhance(){
 [['add-file','plus'],['add-folder','folder'],['reader-controls','headphones'],['new-playlist','plus'],['bookmark','bookmark']].forEach(([id,name])=>decorate(id,name));
 [['previous','previous'],['next','next']].forEach(([id,name])=>{const el=document.getElementById(id);if(el)el.innerHTML=icon(name);});
 document.getElementById('add-file').classList.add('primary');
 document.getElementById('reader-controls').classList.add('reader-entry');
 setPlay(document.getElementById('play'),true);
}
root.ShiurUI={icon,setPlay,applyTheme,enhance};
})(globalThis);
