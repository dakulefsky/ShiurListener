"""Transparent experimental decisions; scores are not content guarantees."""
import math
VERSION='2.0-experimental'
def decide(windows,strict=True):
 if not windows:return dict(decision='uncertain',reason='No decoded audio',segments=[],policy=VERSION)
 total=0.;speech=0.;music=0.;segments=[];active=None
 for w in windows:
  if not all(isinstance(w[k],(int,float)) and math.isfinite(w[k]) for k in ['start','seconds','speech','music','singing']):raise ValueError('Non-finite analysis data')
  if w['seconds']<=0 or w['start']<0 or any(not 0<=w[k]<=1 for k in ['speech','music','singing']):raise ValueError('Invalid analysis data')
  total+=w['seconds'];speech+=w['seconds']*(w['speech']>=.5);hit=max(w['music'],w['singing'])>=.5
  if hit:
   music+=w['seconds']
   if active is None:active={'start':w['start'],'end':w['start']+w['seconds'],'peak':max(w['music'],w['singing'])}
   else:active.update(end=w['start']+w['seconds'],peak=max(active['peak'],w['music'],w['singing']))
  elif active is not None:segments.append(active);active=None
 if active is not None:segments.append(active)
 longest=max((s['end']-s['start'] for s in segments),default=0)
 if music/total>=.1 or longest>=2.9:decision,reason='block','Sustained or substantial music/singing detected'
 elif strict and segments:decision,reason='uncertain','Short music/singing candidates need review'
 elif speech/total>=.5:decision,reason='allow','Predominantly speech under this experimental rule'
 else:decision,reason='uncertain','Insufficient evidence of speech'
 return dict(policy=VERSION,profile='conservative' if strict else 'balanced',decision=decision,reason=reason,seconds=total,speech_fraction=speech/total,music_fraction=music/total,segments=segments)
