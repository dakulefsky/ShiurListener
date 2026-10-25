/* Development source: two local checks; no new plugin archive published. */
(function(root){
'use strict';
let active=null;
function message(text){const node=document.getElementById('analysis-status');if(node)node.textContent=text;}
async function analyze(url,options={}){
 if(!root.BrowserTwoCheck||!root.tf||!root.tflite)throw Error('רכיבי הבדיקה המקומית חסרים. התקינו מחדש את התוסף.');
 active?.abort();const controller=new AbortController();active=controller;const abort=()=>controller.abort();options.signal?.addEventListener('abort',abort,{once:true});if(options.signal?.aborted)abort();
 const started=performance.now();
 try{
  message('בדיקה מהירה מקומית: שתי דגימות בלבד…');
  const result=await BrowserTwoCheck.scan(url,{assetBase:new URL('./',document.baseURI).href,duration:options.duration,budgetMs:5000,signal:controller.signal});
  if(controller.signal.aborted)throw Error('בדיקת השמע בוטלה');
  result.version='two-interior-checks-v2-speech-priority';
  if(result.decision==='provisional_speech'){message('בדיקה מקומית: זוהה דיבור בשתי הדגימות או באחת מהן. זו בדיקה חלקית.');return result;}
  if(result.decision==='music_detected_in_samples'){message('זוהתה מוזיקה או שירה בשתי הדגימות.');throw Error('זוהתה מוזיקה או שירה בשתי הדגימות. הניגון נחסם.');}
  message('שתי הדגימות אינן מספיקות לזיהוי דיבור.');throw Error('בדיקת השמע אינה ודאית. הניגון נחסם.');
 }catch(error){
  if(controller.signal.aborted||performance.now()-started>=5000)throw Error('הבדיקה הופסקה או חרגה מחמש שניות. אפשר לנסות שוב.');
  if(/No supported MPEG|Unsupported WAV|Unsupported extensible|Unsupported file prefix/.test(error.message))throw Error('הבדיקה המהירה תומכת כעת בקובצי MP3 ו־WAV PCM או Float בלבד. ייתכן שקובץ זה פגום או שאינו נתמך.');
  throw error;
 }finally{options.signal?.removeEventListener('abort',abort);if(active===controller)active=null;}
}
root.OfflineSpeechAnalysis={analyze,decide:rows=>root.BrowserTwoCheck.decide(rows),cancel(){active?.abort();}};
})(globalThis);
