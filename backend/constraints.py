"""Independent deterministic checks. No model/API calls are permitted here."""
from collections import Counter, defaultdict

def overlap(a,b):
    return (a.get('week') is None or b.get('week') is None or a['week']==b['week']) and a['day']==b['day'] and max(a['start_period'],b['start_period']) < min(a['start_period']+a['duration'],b['start_period']+b['duration'])

def windows(item, placement):
    return any(overlap(placement,w) for w in item.get('unavailable',[]))

def placement_errors(data, session, a, exam=False):
    errors=[]
    rooms={r['id']:r for r in data['rooms']}; faculty={f['id']:f for f in data['faculty']}
    d=session['duration']; p=a.get('start_period'); day=a.get('day'); room=rooms.get(a.get('room'))
    if type(day) is not int or day not in range(5) or type(p) is not int or p not in range(1,10) or p+d-1>9:
        errors.append('Academic session must be within Monday–Friday, P1–P9'); return errors
    if p<=5<p+d-1: errors.append('Session crosses lunch')
    if session.get('kind')=='lab' and d==3 and p not in [2,6]: errors.append('Three-hour lab must start at P2 or P6')
    if not room: errors.append('Unknown room'); return errors
    a={**a,'duration':d,'week':8 if exam else 7}
    if room['capacity']//(2 if exam else 1)<session['size']: errors.append('Insufficient room capacity'+(' at half exam capacity' if exam else ''))
    if room['type']!=session['room_type']: errors.append('Room type mismatch')
    if session.get('accessible') and not room['accessible']: errors.append('Accessible room required')
    if windows(room,a): errors.append('Room unavailable')
    for fid in session['faculty']:
        if fid not in faculty: errors.append('Unknown faculty')
        elif windows(faculty[fid],a): errors.append(f'Faculty {fid} unavailable')
    if any(a.get(k)!=v for k,v in (session.get('fixed') or {}).items()): errors.append('Fixed slot changed')
    return errors

def validate(data, schedule):
    errors=[]; soft=Counter(); valid_rows=[]
    for section, source, exam in [('sessions','sessions',False),('exams','exams',True)]:
        rows=schedule.get(section,[]); expected={s['id']:s for s in data[source]}; counts=Counter(a.get('id') for a in rows)
        for sid in expected:
            if counts[sid]!=1: errors.append(f'{sid}: expected exactly one assignment, found {counts[sid]}')
        joined=[]
        for a in rows:
            if set(a)!={'id','day','start_period','room'}:
                errors.append(f'{a.get("id")}: assignment has missing or untrusted extra fields');continue
            s=expected.get(a.get('id'))
            if not s: errors.append(f'Unknown assignment {a.get("id")}'); continue
            issues=placement_errors(data,s,a,exam)
            errors.extend(f'{s["id"]}: {e}' for e in issues)
            if not issues: joined.append({**s,**a,'duration':s['duration'],'week':8 if exam else 7})
        for i,a in enumerate(joined):
            for b in joined[i+1:]:
                if not overlap(a,b): continue
                if a['room']==b['room']: errors.append(f'Room clash: {a["id"]}, {b["id"]}')
                if set(a['faculty']) & set(b['faculty']): errors.append(f'Faculty clash: {a["id"]}, {b["id"]}')
                elective=a.get('basket') and a.get('basket')==b.get('basket')
                if set(a['groups']) & set(b['groups']) and not elective: errors.append(f'Group clash: {a["id"]}, {b["id"]}')
        baskets=defaultdict(list); daily=Counter()
        for a in joined:
            if a.get('basket'): baskets[a['basket']].append((a['day'],a['start_period']))
            for f in a['faculty']: daily[f,a['day']]+=a['duration']
        for key,slots in baskets.items():
            if len(set(slots))>1: errors.append(f'Elective basket {key} not synchronised')
        for f in data['faculty']:
            for day in range(5):
                if daily[f['id'],day]>f['daily_limit']: errors.append(f'{f["id"]}: daily limit exceeded on day {day}')
        if not exam: valid_rows=joined
    rooms={r['id']:r for r in data['rooms']}; faculty={f['id']:f for f in data['faculty']}
    for a in valid_rows:
        soft['p9']+=int(a['start_period']<=9<a['start_period']+a['duration'])
        soft['underused_room']+=int(a['size']<0.4*rooms[a['room']]['capacity'])
        soft['faculty_avoid']+=sum(any(overlap(a,w) for w in faculty[f].get('avoid',[])) for f in a['faculty'])
    for g in data['groups']:
        for day in range(5):
            rows=[a for a in valid_rows if g['id'] in a['groups'] and a['day']==day]
            occupied={p for a in rows for p in range(a['start_period'],a['start_period']+a['duration'])}
            soft['group_gaps']+=sum(p not in occupied for p in range(min(occupied),max(occupied)+1)) if occupied else 0
            soft['group_overload']+=max(0,len(occupied)-6)
            courses=Counter(a['course'] for a in rows if a['kind']=='lecture')
            soft['repeated_lecture']+=sum(max(0,n-1) for n in courses.values())
    active=[]; request_ids=set()
    decisions=schedule.get('bookings',[])
    for request in data['bookings']:
        matches=[b for b in decisions if b.get('id')==request['id']]
        if len(matches)!=1:errors.append(f'{request["id"]}: expected exactly one booking decision')
        if request.get('cancelled') and any(b.get('status')!='cancelled' for b in matches):errors.append(f'{request["id"]}: cancelled request must not reserve a venue')
    for b in decisions:
        if b.get('id') in request_ids: errors.append(f'Duplicate booking decision {b.get("id")}')
        request_ids.add(b.get('id'))
        if b.get('status') not in ['approved','alternative','rejected','cancelled','pending']:errors.append(f'{b.get("id")}: unknown booking status')
        if not b.get('reason'):errors.append(f'{b.get("id")}: booking decision requires a reason')
        if b.get('status')=='approved':
            issues=booking_errors(data,b,valid_rows,active,check_category=False)
            errors.extend(f'{b["id"]}: {e}' for e in issues); active.append(b)
    utilisation=utilisation_report(data,valid_rows)
    components=['faculty_avoid','group_gaps','group_overload','repeated_lecture','underused_room','p9']
    return dict(valid=not errors,hard_violations=len(errors),errors=errors,soft_penalty=sum(soft.values()),soft_breakdown={k:soft[k] for k in components},soft_weights={k:1 for k in components},scoring='provisional unit weights; official validator unavailable',room_utilisation=utilisation['percent'],utilisation=utilisation)

def utilisation_report(data,rows,week=7):
    """Academic room-hours, eligible teaching room types, less closure union."""
    eligible={s['room_type'] for s in data['sessions']}
    rooms=[]
    for room in data['rooms']:
        available=sum(not windows(room,dict(week=week,day=d,start_period=p,duration=1)) for d in range(5) for p in range(1,10)) if room['type'] in eligible else 0
        used=sum(a['duration'] for a in rows if a['room']==room['id'])
        rooms.append(dict(id=room['id'],available_hours=available,used_hours=used,percent=round(100*used/available,2) if available else 0))
    available=sum(r['available_hours'] for r in rooms); used=sum(r['used_hours'] for r in rooms)
    return dict(week=week,periods='P1-P9',denominator='Available room-hours of teaching-compatible room types, excluding maintenance and closures',available_hours=available,used_hours=used,percent=round(100*used/available,2) if available else 0,rooms=rooms)

def booking_errors(data,b,sessions,bookings,check_category=True):
    b={**b,'week':7}
    errors=[]; rooms={r['id']:r for r in data['rooms']}; room=rooms.get(b.get('room'))
    p=b.get('start_period'); duration=b.get('duration'); day=b.get('day'); size=b.get('size')
    if type(day) is not int or day not in range(5) or type(p) is not int or type(duration) is not int or duration<1 or p<1 or p+duration-1>13:
        return ['Valid day, start period and duration required']
    if p<=5<p+duration-1: errors.append('Event crosses lunch')
    if type(size) is not int or size<1: errors.append('Positive attendance required')
    if not room: return errors+['Select a known room']
    if type(size) is int and size>room['capacity']: errors.append('Insufficient room capacity')
    if b.get('room_type') and b['room_type']!=room['type']: errors.append('Room type mismatch')
    if b.get('accessible') and not room['accessible']: errors.append('Accessible room required')
    if windows(room,b): errors.append('Room unavailable')
    if any(g not in {x['id'] for x in data['groups']} for g in b.get('groups',[])): errors.append('Unknown mandatory group')
    if check_category and b.get('category') not in ['institute','guest','department','club']: errors.append('Event category is invalid; exams/classes require academic scheduling')
    for a in sessions+bookings:
        if overlap(a,b):
            if a['room']==b['room']: errors.append(f'Room occupied by {a["id"]}')
            if set(a.get('groups',[])) & set(b.get('groups',[])): errors.append(f'Mandatory group occupied by {a["id"]}')
    return errors

def enriched(data,rows,section='sessions'):
    source={s['id']:s for s in data[section]}
    return [{**source[a['id']],**a,'week':8 if section=='exams' else 7} for a in rows]
