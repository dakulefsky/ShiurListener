(function(root){
'use strict';
const prefix='shiur-audio-v1:';
const keys={state:prefix+'state',progress:prefix+'progress',queue:prefix+'queue'};
async function rpc(method,args={}){
 const result=await Otzaria.call(method,args);
 if(!result?.success)throw Error(result?.error?.message||'הפעולה נכשלה');
 return result.data;
}
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
function source(value){
 if(!value||typeof value.id!=='string'||!value.id||value.id.length>4096||typeof value.title!=='string'||value.title.length>300)throw Error('מקור שמע לא תקין');
 const token=/^[a-zA-Z0-9_-]{1,128}$/;
 if(typeof value.token==='string'&&token.test(value.token)&&!value.folderToken&&!value.path)return {id:value.id,title:value.title,token:value.token};
 if(typeof value.folderToken==='string'&&token.test(value.folderToken)&&!value.token&&typeof value.path==='string'&&value.path.length>0&&value.path.length<4096&&!/^[\/\\]|^[a-z]+:|(^|[\/\\])\.\.([\/\\]|$)/i.test(value.path))return {id:value.id,title:value.title,folderToken:value.folderToken,path:value.path};
 throw Error('נדרש קובץ מאושר או נתיב יחסי בתיקייה מאושרת');
}
function position(value){if(typeof value!=='number'||!Number.isFinite(value)||value<0||value>604800000)throw Error('מיקום לא תקין');return Math.round(value);}
function positions(value){
 const result=Object.create(null);
 if(!value||typeof value!=='object'||Array.isArray(value))return result;
 for(const [id,item] of Object.entries(value)){
  if(!item||typeof item!=='object'||!Number.isFinite(item.positionMs)||item.positionMs<0||item.positionMs>604800000)continue;
  const durationMs=Number.isFinite(item.durationMs)&&item.durationMs>=0?Math.round(item.durationMs):0;
  result[id]={positionMs:Math.round(item.positionMs),durationMs,completed:item.completed===true||(item.completed==null&&durationMs>0&&item.positionMs>=durationMs),lastListenedAt:Number.isFinite(item.lastListenedAt)?Math.max(0,item.lastListenedAt):0};
 }
 return result;
}
const rates=[.75,1,1.25,1.5,1.75,2];
function control(id){
 return {'shiur-toggle':{op:'toggle'},'shiur-back':{op:'skip',direction:-1},'shiur-forward':{op:'skip',direction:1},'shiur-previous':{op:'previous'},'shiur-next':{op:'next'},'shiur-slower':{op:'speed_step',direction:-1},'shiur-faster':{op:'speed_step',direction:1},'shiur-stop':{op:'stop'}}[id];
}
root.ShiurProtocol={keys,rpc,sleep,source,position,positions,rates,control};
})(globalThis);
