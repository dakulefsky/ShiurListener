(function(root){
'use strict';
const dictionary={
'נגן שיעורים':'Shiur Player','עדכנו גם את התוכנה במחשב מה־ZIP החדש.':'Update the desktop app from the new ZIP too.','נגן מלווה · 1.1.0':'Companion player · 1.1.0','הגדרות חיבור':'Connection settings','חיבור לנגן המלווה':'Connect to the companion',
'פתחו את נגן השיעורים במחשב.':'Open Shiur Player on your computer.','העתיקו את קוד החיבור מהחלון שלו והדביקו כאן.':'Copy the connection code from its window and paste it here.','לחצו על חיבור. אין צורך להשאיר את חלון האפליקציה גלוי.':'Click Connect. The app window can stay hidden.',
'השיעורים שלכם, גם בזמן הלימוד':'Your recordings, while you learn','קוד צימוד':'Connection code','זכירת החיבור במכשיר הזה':'Remember this connection on this device','חיבור':'Connect','הדביקו את קוד החיבור':'Paste the connection code',
'כעת בנגן · ההאזנה ממשיכה גם בכרטיסיות אחרות':'Now playing · listening continues in other tabs','בחרו שיעור':'Choose a recording','ניגון':'Play','השהיה':'Pause','ניגון או השהיה':'Play or pause','השיעור הקודם':'Previous recording','השיעור הבא':'Next recording',
'מהירות':'Speed','עוצמה':'Volume','דילוג':'Skip','10 שניות':'10 seconds','15 שניות':'15 seconds','דקה':'1 minute','טיימר, המשך אוטומטי וסימניות':'Sleep timer, auto-next and bookmarks','מעבר אוטומטי לשיעור הבא ברקע':'Automatically play the next recording',
'טיימר שינה':'Sleep timer','כבוי':'Off','15 דקות':'15 minutes','30 דקות':'30 minutes','שעה':'1 hour','שעה וחצי':'90 minutes','הניגון לא יושהה אוטומטית':'Sleep timer is off','סימניות':'Bookmarks','שם הסימנייה':'Bookmark name','＋ שמירה':'＋ Save','מחיקת סימנייה':'Delete bookmark',
'הצגה / הסתרה של הנגן הצף':'Show / hide floating player','סריקה מחדש':'Rescan folder','עצירה':'Stop','חיפוש שיעורים':'Search recordings','תיקייה':'Collection','כל השיעורים':'All recordings','＋ תיקייה חדשה':'＋ New collection','שינוי שם':'Rename','מחיקה':'Delete','הצגה':'Show','המשך האזנה':'Continue listening','טרם הושמעו':'Unplayed','האזנה שהושלמה':'Completed','טרם הושמע':'Not played yet','＋ לתיקייה':'＋ Add to collection','הסרה מהתיקייה':'Remove from collection',
'התיקייה ריקה. הוסיפו שיעורים מהספרייה באמצעות תפריט ״לתיקייה״.':'This collection is empty. Add recordings using the collection menu.',
'אין שיעורים להצגה. בחרו את תיקיית השמע במחשב, או הוסיפו אליה קבצים ולחצו על סריקה מחדש.':'No recordings to show. Choose the recordings folder on your computer, or add audio files to it and click Rescan folder.',
'בחירת תיקיית שיעורים':'Choose recordings folder','חלון הנגן במחשב':'Open desktop app','טרם נבחרה תיקיית שמע':'No recordings folder selected','תיקיית מקור:':'Recordings folder:',
'שליטה מכל עמוד ומכל תוכנה':'Controls across pages and applications','הנגן המלווה רושם קיצורים כלליים ב־Windows. אין צורך לחזור ללשונית הנגן. כל הקיצורים הבאים מתחילים ב־Ctrl + Alt + Shift:':'Windows global shortcuts work without returning to this tab. All shortcuts below start with Ctrl + Alt + Shift:',
'P — הפעלה או השהיה':'P — Play / pause','חץ שמאלה / ימינה — אחורה / קדימה לפי משך הדילוג שנבחר':'Left / Right — Skip backward / forward','חץ למעלה / למטה — שינוי מהירות':'Up / Down — Change speed','Page Up / Page Down — השיעור הקודם / הבא':'Page Up / Page Down — Previous / next recording','1 / 2 / 3 — בחירת 10 שניות / 15 שניות / דקה':'1 / 2 / 3 — Select 10 / 15 / 60 seconds','S — עצירה ושמירת המיקום':'S — Stop and save position','F — הצגה / הסתרה של הנגן הצף':'F — Show / hide floating player',
'לשינוי או לביטול קיצור: ערכו את hotkeys.json בתיקיית הנתונים של הנגן והפעילו אותו מחדש. קיצור שתפוס על ידי תוכנה אחרת לא יירשם.':'To change or disable a shortcut, edit hotkeys.json in the player data folder and restart the app. Shortcuts already used by another app cannot be registered.',
'תיקייה חדשה':'New collection','שינוי שם התיקייה':'Rename collection','למחוק את התיקייה? השיעורים יישארו בספרייה.':'Delete this collection? The recordings stay in the library.','שם':'Name','ביטול':'Cancel','שמירה':'Save','אישור':'Confirm','הקבצים המקוריים במכשיר לא יימחקו.':'Your original audio files will not be deleted.',
'הדביקו את קוד הצימוד מהנגן המלווה.':'Paste the connection code from the desktop app.','יש להתחבר לנגן המלווה תחילה.':'Connect to the desktop app first.','בחרו שיעור תחילה.':'Choose a recording first.','טעינת הסימניות נכשלה.':'Could not load bookmarks.','שמירת הסימניות נכשלה.':'Could not save bookmarks.','החיבור זמין מתוך אוצריא בלבד.':'Connect from inside Otzaria.',
'החיבור הצליח, אך לא ניתן לשמור את ההעדפה.':'Connected, but the connection preference could not be saved.','לא ניתן למחוק את החיבור השמור.':'Could not remove the saved connection.','לא התקבלה תשובה תקינה מהנגן המלווה. בדקו שהוא פועל.':'The companion did not respond correctly. Check that it is running.',
'Choose a recordings folder first.':'Choose a recordings folder first.','No recordings found. Choose a recordings folder, then rescan.':'No recordings found. Choose a recordings folder, then rescan.',
'פתיחת התיקייה נעשית בחלון הנגן במחשב.':'Choose the folder in the desktop app window.','מחובר. ההאזנה תימשך גם כשהתוסף מוסתר.':'Connected. Listening continues when this tab is hidden.'
};
const heErrors={'Choose a recordings folder first.':'בחרו תחילה את תיקיית השיעורים.','No recordings found. Choose a recordings folder, then rescan.':'לא נמצאו שיעורים. בחרו את תיקיית השיעורים וסרקו מחדש.','The recordings folder is missing or disconnected.':'תיקיית השיעורים חסרה או שהכונן מנותק.','Pairing required.':'נדרש קוד חיבור תקין.','Pairing required. Browser-origin requests are not accepted.':'נדרש קוד חיבור תקין.'};
const reverse=Object.fromEntries(Object.entries(dictionary).map(([he,en])=>[en,he]));
let language='he';const originals=new WeakMap();
function translate(text){
 const value=text.trim();let result=value;
 if(language==='he')result=heErrors[value]||reverse[value]||value;
 else{
  result=dictionary[value]||value;
  if(/^\d+ שיעורים$/.test(value))result=value.replace('שיעורים','recordings');
  if(value.startsWith('מחובר · '))result=value.replace('מחובר · ','Connected · ').replace('שיעורים. ההאזנה תימשך גם כשהתוסף מוסתר.','recordings. Listening continues in other tabs.');
  if(value.startsWith('הניגון יושהה בעוד '))result=value.replace('הניגון יושהה בעוד ','Playback pauses in ');
  if(value.startsWith('תיקיית מקור: '))result=value.replace('תיקיית מקור: ','Recordings folder: ');
  if(value.endsWith(': פעיל'))result=value.replace(': פעיל',': active');
  if(value.endsWith(': לא זמין'))result=value.replace(': לא זמין',': unavailable');
  if(value.startsWith('אחורה '))result=value.replace('אחורה ','Back ').replace(' שניות',' seconds');
  if(value.startsWith('קדימה '))result=value.replace('קדימה ','Forward ').replace(' שניות',' seconds');
  if(value.startsWith('הוספת '))result=value.replace('הוספת ','Add ').replace(' לתיקייה',' to collection');
  if(value.startsWith('החיבור לנגן המלווה אבד.'))result='Connection lost. Reopen the desktop app and check its connection code.';
  if(value.startsWith('החיבור השמור אינו זמין.'))result='Saved connection unavailable. Reopen the desktop app or paste its current connection code.';
 }
 return text.replace(value,result);
}
function apply(){
 document.documentElement.lang=language;document.documentElement.dir=language==='en'?'ltr':'rtl';document.title=language==='en'?'Shiur Player':'נגן שיעורים';
 const walk=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
 for(let node;node=walk.nextNode();){
  if(node.parentElement.closest('script,style,[data-user-text]'))continue;
  const old=originals.get(node),original=old&&node.nodeValue===old.rendered?old.original:node.nodeValue;
  const rendered=translate(original);if(node.nodeValue!==rendered)node.nodeValue=rendered;originals.set(node,{original,rendered});
 }
 for(const el of document.querySelectorAll('[placeholder],[aria-label],[title]')){
  if(el.closest('[data-user-text]'))continue;
  let map=originals.get(el)||{};
  for(const key of ['placeholder','aria-label','title'])if(el.hasAttribute(key)){
   const old=map[key],original=old&&el.getAttribute(key)===old.rendered?old.original:el.getAttribute(key);const rendered=translate(original);el.setAttribute(key,rendered);map[key]={original,rendered};
  }
  originals.set(el,map);
 }
 const select=document.getElementById('interface-language');if(select)select.value=language;
}
root.ShiurLocale={get language(){return language;},set(value){language=value==='en'?'en':'he';apply();},apply,text:translate};
})(globalThis);
