"""Read-only exhaustive slot audit against an independent occupancy oracle."""
import json,sys,time
from pathlib import Path
from hashlib import sha256
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.constraints import booking_errors,enriched,placement_errors
from backend.solver import domain_issues
from backend.bookings import venue_availability
from audit_hard_constraints import audit

def intersects(a,b):
    return b.get('week') in (None,7) and a['day']==b['day'] and bool(set(range(a['start_period'],a['start_period']+a['duration']))&set(range(b['start_period'],b['start_period']+b['duration'])))

def expected(data,room,q,occupied):
    periods=set(range(q['start_period'],q['start_period']+q['duration']))
    return (periods<=set(range(1,14)) and not {5,6}<=periods and room['capacity']>=q['size']
        and (not q.get('accessible') or room['accessible']) and (not q.get('room_type') or room['type']==q['room_type'])
        and not any(intersects(q,w) for w in room.get('unavailable',[]))
        and not any(intersects(q,a) and (a['room']==room['id'] or set(q.get('groups',[]))&set(a.get('groups',[]))) for a in occupied))

def run(path):
    started=time.monotonic();raw=path.read_bytes();snapshot=json.loads(raw);data=snapshot['data'];schedule=snapshot['schedule']
    rows=enriched(data,schedule['sessions']);approved=[b for b in schedule['bookings'] if b['status']=='approved'];occupied=rows+approved
    checked=0;failures=[]
    for day in range(5):
        for start in range(1,14):
            for duration in range(1,15-start):
                for room in data['rooms']:
                    for size in (room['capacity'],room['capacity']+1):
                        q=dict(week=7,day=day,start_period=start,duration=duration,room=room['id'],size=size,category='club',groups=[])
                        actual=not booking_errors(data,q,rows,approved)
                        if actual!=expected(data,room,q,occupied):failures.append(dict(query=q,actual=actual))
                        checked+=1
    discoveries=0
    for day in range(5):
        for start in range(1,14):
            for duration in (1,2,3):
                if start+duration>14:continue
                q=dict(week=7,day=day,start_period=start,duration=duration,size=70,accessible=True,room_type='classroom',groups=[data['groups'][0]['id']])
                actual=venue_availability(data,q,rows,approved)
                want={r['id'] for r in data['rooms'] if expected(data,r,q,occupied)}
                if {r['room'] for r in actual['available_rooms']}!=want:failures.append(dict(discovery=q,expected=sorted(want)))
                for offer in actual['other_times']:
                    room=next(r for r in data['rooms'] if r['id']==offer['room'])
                    if not expected(data,room,{**q,**offer},occupied):failures.append(dict(invalid_offer=offer))
                discoveries+=1
    representatives={}
    for section in ('sessions','exams'):
        for s in data[section]:representatives.setdefault((section,s['kind'],s['duration'],s['room_type'],s.get('accessible',False),bool(s.get('fixed'))),s)
    domains=0
    for key,s in representatives.items():
        for day in range(5):
            for start in range(1,10):
                for room in data['rooms']:
                    a=dict(day=day,start_period=start,room=room['id'])
                    if bool(domain_issues(data,s,a,key[0]=='exams'))!=bool(placement_errors(data,s,a,key[0]=='exams')):failures.append(dict(domain_mismatch=s['id'],placement=a))
                    domains+=1
    unchanged=sha256(path.read_bytes()).digest()==sha256(raw).digest()
    hard=audit(snapshot)
    return dict(revision=snapshot['revision'],booking_windows_checked=checked,room_discovery_queries=discoveries,solver_validator_domains_compared=domains,failures=failures,state_unchanged=unchanged,hard_constraint_audit=hard,elapsed_seconds=round(time.monotonic()-started,2))

if __name__=='__main__':
    result=run(ROOT/'runtime'/'state.json');print(json.dumps(result,indent=2))
    sys.exit(bool(result['failures']) or not result['state_unchanged'] or not result['hard_constraint_audit']['passed'])
