"""Untrusted interpretation layer. Never imports or invokes the solver."""
import os, json, re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
import httpx

PROMPT=Path(__file__).resolve().parents[1]/'prompts'/'parse.txt'

def guard_interpretation(result,message):
    """Discard provider authority claims and malformed fields before UI rendering."""
    from .models import BookingDraft, Disruption
    if not isinstance(result,dict) or result.get('intent') not in ('booking','schedule_change'):
        return dict(source='unavailable',draft={},missing=['Interpretation unavailable. Use the independent manual form.'])
    missing=result.get('missing',[])
    missing=[m[:300] for m in missing if isinstance(m,str)] if isinstance(missing,list) else ['Review missing details manually.']
    raw=result.get('draft',{}); model=BookingDraft if result['intent']=='booking' else Disruption
    if not isinstance(raw,dict):raw={};missing.append('Malformed draft; enter the details manually.')
    draft={k:v for k,v in raw.items() if k in model.model_fields}
    if set(raw)-set(draft):missing.append('Unsupported model fields were discarded; review the draft.')
    try:draft=model.model_validate(draft,strict=True).model_dump(exclude_none=True,exclude_unset=True)
    except ValueError:draft={};missing.append('Invalid draft fields; enter the details manually.')
    # Preserve the user's claimed exam category even if a provider silently relabels it.
    if result['intent']=='booking' and re.search(r'\b(exam|midsem)\b',message,re.I):draft['category']='exam'
    return dict(source=result.get('source','untrusted-parser'),intent=result['intent'],draft=draft,missing=missing)

def parse_request(message,data,outage=False,actor=None):
    if outage: return dict(source='unavailable',draft={},missing=['AI outage simulated. Use the independent manual form.'])
    if os.getenv('AI_API_KEY') and os.getenv('AI_MODEL'):
        try:
            context=dict(today=datetime.now(ZoneInfo('Asia/Kolkata')).strftime('%A %Y-%m-%d'),actor=actor,rooms=[{k:r[k] for k in ['id','name','type']} for r in data['rooms']],sessions=[s['id'] for s in data['sessions']])
            response=httpx.post(os.getenv('AI_BASE_URL','https://api.openai.com/v1').rstrip('/')+'/chat/completions',headers={'Authorization':'Bearer '+os.environ['AI_API_KEY']},json={'model':os.environ['AI_MODEL'],'messages':[{'role':'system','content':PROMPT.read_text(encoding='utf-8')+'\nContext: '+json.dumps(context)},{'role':'user','content':message}],'response_format':{'type':'json_object'}},timeout=15)
            response.raise_for_status(); result=json.loads(response.json()['choices'][0]['message']['content'])
            if not isinstance(result,dict) or result.get('intent') not in ['booking','schedule_change'] or not isinstance(result.get('draft'),dict) or not isinstance(result.get('missing'),list):raise ValueError('Malformed interpretation')
            result['source']='llm-untrusted'; return result
        except Exception:
            return dict(source='unavailable',draft={},missing=['AI service unavailable. Use the manual form; no schedule was changed.'])
    return parse_local(message,data,actor)

def parse_local(message,data,actor=None):
    # Honest no-key fallback, deliberately conservative and labelled as a parser.
    low=message.lower(); draft={'title':message[:180],'category':'club','duration':1,'accessible':bool(re.search(r'accessible|wheelchair',low)),'groups':[]}
    for category, pattern in [('exam',r'exam|midsem'),('institute',r'institute|spectra|convocation'),('guest',r'guest'),('department',r'department'),('exam',r'exam|midsem')]:
        if re.search(pattern,low): draft['category']=category; break
    names=['monday','tuesday','wednesday','thursday','friday']
    for day,name in enumerate(names):
        if re.search(r'\b'+name+r'\b',low): draft['day']=day; break
    relative_day=bool(re.search(r'\b(kal|tomorrow)\b',low))
    match=re.search(r'\bp(1[0-3]|[1-9])\b',low)
    if match:draft['start_period']=int(match[1])
    else:
        match=re.search(r'\b(\d{1,2})(?::00)?\s*(am|pm|baje)\b',low)
        if match:
            hour=int(match[1]); marker=match[2]
            if marker=='pm' and hour<12:hour+=12
            if marker=='baje' and ('shaam' in low or 'evening' in low) and hour<12:hour+=12
            if marker!='baje' or hour>=13 or 'subah' in low:
                if 8<=hour<=12:draft['start_period']=hour-7
                elif 14<=hour<=21:draft['start_period']=hour-8
    for r in sorted(data['rooms'],key=lambda r:-len(r['name'])):
        if r['name'].lower() in low or re.search(r'(?<![\w-])'+re.escape(r['id'].lower())+r'(?![\w-])',low):draft['room']=r['id'];draft['room_type']=r['type'];break
    match=re.search(r'(\d+)\s*(students|people|attendees|log|bacche)',low)
    if match:draft['size']=int(match[1])
    match=re.search(r'(\d+)\s*(hours?|hrs?|ghant)',low)
    if match:draft['duration']=int(match[1])
    if re.search(r'\b(move|shift|reschedule|leave|unavailable|chhutti)\b',low) or re.search(r'\b(change|modify|edit)\b.*\b(timetable|session|class|s\d{3})\b',low):
        sid=re.search(r'\bs\d{3}\b',low);fid=re.search(r'\bf\d{2}\b',low)
        missing=[];change={}
        if re.search(r'\b(leave|unavailable|chhutti)\b',low):
            faculty=fid[0].upper() if fid else (actor or {}).get('faculty')
            if not faculty:missing.append('faculty identity')
            if 'day' not in draft:missing.append('day')
            if not re.search(r'full.day|whole.day|poora din',low) and 'start_period' not in draft:missing.append('leave time or explicit full-day leave')
            change={'faculty_leave':[dict(faculty=faculty,day=draft.get('day'),start_period=draft.get('start_period',1),duration=draft.get('duration',9) if 'start_period' in draft else 9)]}
        else:
            if not sid:missing.append('session ID')
            missing += [k for k in ['day','start_period'] if k not in draft]
            move=dict(session=sid[0].upper() if sid else None,day=draft.get('day'),start_period=draft.get('start_period'))
            if 'room' in draft:move['room']=draft['room']
            change={'moves':[move]}
        if relative_day:missing.append('Confirm the intended weekday and week; relative dates are ambiguous.')
        return dict(source='local-rule-parser (no model configured)',intent='schedule_change',draft=change,missing=missing)
    missing=[k for k in ['day','start_period','room','size'] if k not in draft]
    if not match:missing.append('duration')
    if relative_day:missing.append('Confirm the intended weekday and week; relative dates are ambiguous.')
    if re.search(r'\b(if|unless|agar|maybe|around|approximately)\b',low):missing.append('Confirm the condition or approximate timing explicitly in the form.')
    return dict(source='local-rule-parser (no model configured)',intent='booking',draft=draft,missing=missing)
