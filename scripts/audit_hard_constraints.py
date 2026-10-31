"""Read-only checklist audit of a saved ChronoGrid state; never changes the schedule."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.constraints import validate

RULES=[
    'Exactly one day, start period and room per session',
    'No simultaneous faculty assignments',
    'No group clashes; all combined groups count; same-basket exception',
    'No simultaneous room assignments',
    'Room capacity; floor(capacity / 2) for examinations',
    'Required room type matches',
    'Faculty unavailability respected',
    'Room unavailability respected',
    'No lunch crossing; three-hour labs only P2–P4 or P6–P8',
    'Accessible sessions receive accessible rooms',
    'Same-basket sessions share day and start period',
    'Faculty daily teaching hours stay within their limit',
    'Approved bookings protect rooms and mandatory groups',
    'Original fixed slots are preserved',
]


def audit(snapshot):
    data=snapshot['data'];schedule=snapshot['schedule']
    if not schedule:raise ValueError('No active schedule to audit')
    findings={f'H{i:02}':[] for i in range(1,15)}
    def fail(rule,message):findings[f'H{rule:02}'].append(message)
    rooms={r['id']:r for r in data['rooms']};faculty={f['id']:f for f in data['faculty']}
    joined=[]
    # Separate implementation from solver and validator for the saved-state spot check.
    def conflicts(a,b):
        return (b.get('week') is None or a['week']==b['week']) and a['day']==b['day'] and bool(set(range(a['start_period'],a['start_period']+a['duration']))&set(range(b['start_period'],b['start_period']+b['duration'])))
    def unavailable(item,row):
        return any((window.get('week') is None or window['week']==row['week']) and conflicts(row,window) for window in item.get('unavailable',[]))
    for section,week in [('sessions',7),('exams',8)]:
        source={s['id']:s for s in data[section]};counts=Counter(a.get('id') for a in schedule[section])
        for sid in source:
            if counts[sid]!=1:fail(1,f'{sid}: {counts[sid]} assignments')
        for assignment in schedule[section]:
            sid=assignment.get('id')
            if sid not in source or set(assignment)!={'id','day','start_period','room'}:
                fail(1,f'{sid}: unknown ID or non-canonical assignment');continue
            row={**source[sid],**assignment,'week':week};joined.append(row)
            day=row['day'];start=row['start_period'];duration=row['duration']
            if type(day) is not int or day not in range(5) or type(start) is not int or not set(range(start,start+duration))<=set(range(1,10)):
                fail(1,f'{sid}: invalid academic day or period');continue
            room=rooms.get(row['room'])
            if not room:fail(1,f'{sid}: unknown room');continue
            if row['size']>room['capacity']//(2 if week==8 else 1):fail(5,sid)
            if row['room_type']!=room['type']:fail(6,sid)
            if any(fid not in faculty or unavailable(faculty[fid],row) for fid in row['faculty']):fail(7,sid)
            if unavailable(room,row):fail(8,sid)
            occupied=set(range(start,start+duration))
            if {5,6}<=occupied or (row['kind']=='lab' and duration==3 and start not in [2,6]):fail(9,sid)
            if row.get('accessible') and not room['accessible']:fail(10,sid)
            if any(row.get(key)!=value for key,value in (source[sid].get('fixed') or {}).items()):fail(14,sid)
    for a,b in combinations(joined,2):
        if not conflicts(a,b):continue
        if set(a['faculty'])&set(b['faculty']):fail(2,f'{a["id"]} / {b["id"]}')
        if set(a['groups'])&set(b['groups']) and not (a.get('basket') and a.get('basket')==b.get('basket')):fail(3,f'{a["id"]} / {b["id"]}')
        if a['room']==b['room']:fail(4,f'{a["id"]} / {b["id"]}')
    baskets=defaultdict(set);loads=Counter()
    for row in joined:
        if row.get('basket'):baskets[row['week'],row['basket']].add((row['day'],row['start_period']))
        for fid in row['faculty']:loads[row['week'],row['day'],fid]+=row['duration']
    for key,slots in baskets.items():
        if len(slots)!=1:fail(11,str(key))
    for (week,day,fid),hours in loads.items():
        if hours>faculty[fid]['daily_limit']:fail(12,f'{fid}: {hours}h in week {week}, day {day}')
    bookings=[{**b,'week':7} for b in schedule['bookings'] if b['status']=='approved']
    for booking in bookings:
        for other in joined+[b for b in bookings if b['id']!=booking['id']]:
            if conflicts(booking,other) and (booking['room']==other['room'] or set(booking.get('groups',[]))&set(other.get('groups',[]))):fail(13,f'{booking["id"]} / {other["id"]}')
    validator=validate(data,schedule)
    digest=sha256(json.dumps(dict(data=data,schedule=schedule),sort_keys=True).encode()).hexdigest()
    return dict(checked_at=datetime.now(timezone.utc).isoformat(),revision=snapshot['revision'],snapshot_sha256=digest,synthetic=data.get('meta',{}).get('synthetic',False),teaching_sessions=len(schedule['sessions']),teaching_hours=sum(row['duration'] for row in joined if row['week']==7),exams=len(schedule['exams']),approved_bookings=len(bookings),maximum_faculty_daily_hours=max(loads.values(),default=0),rules=[dict(id=f'H{i:02}',rule=label,passed=not findings[f'H{i:02}'],findings=findings[f'H{i:02}']) for i,label in enumerate(RULES,1)],passed=not any(findings.values()) and validator['valid'],independent_validator=dict(valid=validator['valid'],hard_violations=validator['hard_violations'],errors=validator['errors']),limitation='Local synthetic dataset and local validator; official starter pack/validator not supplied.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state',type=Path,default=ROOT/'runtime'/'state.json')
    parser.add_argument('--output',type=Path,default=ROOT/'evidence'/'hard-constraints-audit.json')
    args=parser.parse_args();result=audit(json.loads(args.state.read_text(encoding='utf-8')))
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['revision','teaching_sessions','teaching_hours','exams','approved_bookings','maximum_faculty_daily_hours','passed','independent_validator']},indent=2))
    raise SystemExit(0 if result['passed'] else 1)
